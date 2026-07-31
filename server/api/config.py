"""Resolução de configuração de negócio (SPEC-018, Fase Inicial — T-073).

Este módulo é o **único** lugar do projeto que traduz "quem está pedindo" em "o que ele pode".
Os três princípios da spec valem aqui, linha a linha:

**P1 — a configuração é resolvida na fronteira da API e viaja carimbada no evento.** Os workers
não têm ORM e não vão ganhar (ADR-008), e a SPEC-010 promete que o relatório é derivável por
replay do stream: se o `analysis-worker` consultasse o banco, o mesmo replay em dois momentos
daria relatórios diferentes, em silêncio. Então quem lê configuração é a API, na admissão, e o
valor resolvido entra no `session.started`.

**P2 — todo valor tem default no código; o banco apenas sobrepõe.** Nenhuma leitura daqui pode
falhar uma sessão. Postgres lento, Redis fora, tabela vazia, container novo antes da migration:
o caminho degradado usa a constante que já existia antes desta spec. Por isso `capabilities_for`
**não levanta exceção** — nem a de banco, nem a de cache. Configuração indisponível é um treino
a menos de personalização, nunca um erro na cara de quem ia treinar.

**P3 — o que a bancada calibra não é configuração.** Limiar de FSM e de cena não passa por aqui
nem passará: um valor mudado por formulário não tem fixture, não tem teste de regressão, muda a
contagem de repetição sem aviso e contamina o Parquet da SPEC-010.

## Sobre o cache

Um `GET` no cache por admissão, contra uma consulta a duas tabelas. O snapshot é do **catálogo
de planos inteiro**, não de um plano: são três linhas, a consulta é a mesma, e assim uma conta
que troca de plano não precisa de invalidação própria — o que muda é o ponteiro, que é lido do
`User` a cada requisição. Invalidação por `post_save`/`post_delete` (ver `signals`), e o cache é
compartilhado entre processos, então a edição no painel (processo `api`) alcança quem mais leia.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from django.core.cache import cache
from django.db.models import F

from api.trial import TRIAL_LIMIT, TRIAL_MESSAGE

__all__ = [
    "PLAN_ANON",
    "PLAN_FREE",
    "PLAN_SUBSCRIBER",
    "SNAPSHOT_KEY",
    "SNAPSHOT_TTL_S",
    "Capabilities",
    "capabilities_for",
    "invalidate_snapshot",
]

logger = logging.getLogger("api")

PLAN_ANON = "anon"
PLAN_FREE = "free"
PLAN_SUBSCRIBER = "subscriber"

SNAPSHOT_KEY = "df:config:snapshot"

#: O snapshot também expira sozinho. A invalidação por signal é o caminho normal e rápido; o
#: TTL é a rede de baixo para o caso que o signal não cobre — uma linha alterada por
#: `manage.py shell` com `.update()`, que não dispara `post_save`. Cinco minutos de configuração
#: velha num caso raro é barato; configuração velha para sempre não é.
SNAPSHOT_TTL_S = 300


@dataclass(frozen=True, slots=True)
class Capabilities:
    """O que este solicitante pode, já resolvido. Congelado: ninguém ajusta capacidade no meio
    do caminho — quem quiser outro valor muda o plano, não o objeto."""

    plan_slug: str
    plan_name: str

    daily_sessions: int
    session_min_s: int
    session_max_s: int
    countdown_max_s: int
    allow_cloud: bool
    history_limit: int
    kcal_accumulation: bool
    effects_enabled: bool
    streak_protections_month: int
    min_maturity: str
    daily_workout: bool
    quota_message: str

    default_duration_s: int
    default_countdown_s: int
    cloud_slots: int
    cloud_grace_ms: int
    ticket_ttl_s: int
    series_min: int
    series_max: int
    series_default: int
    reps_min: int
    reps_max: int
    reps_default: int

    config_version: int
    #: `False` quando o valor veio do código porque o banco/cache não respondeu (P2). Existe
    #: para o teste conseguir provar a degradação, e para o log dizer a verdade.
    from_db: bool = True
    flags: dict[str, Any] = field(default_factory=dict)

    @property
    def unlimited_sessions(self) -> bool:
        return self.daily_sessions <= 0

    def duration_s(self, requested: int | None = None) -> int:
        """Duração efetiva desta sessão, dentro da faixa do plano.

        `clamp` e não recusa, pela mesma razão que o countdown: duração é conforto pedido pelo
        cliente, não parâmetro de medição. Derrubar a sessão porque veio um número fora da
        faixa trocaria um treino por uma mensagem de erro.
        """
        alvo = self.default_duration_s if requested is None else requested
        return max(self.session_min_s, min(self.session_max_s, alvo))

    def countdown_s(self, requested: int) -> int:
        return max(0, min(self.countdown_max_s, requested))


#: Piso do código (P2): exatamente o comportamento anterior a esta task, por plano. Se o banco
#: sumir inteiro, o produto continua o de ontem — que é a definição de degradar.
_FLOOR_PLAN: dict[str, dict[str, Any]] = {
    PLAN_ANON: {
        "plan_name": "Visitante",
        # O trial de 3/dia da SPEC-011, agora dito como plano em vez de caminho de código.
        "daily_sessions": TRIAL_LIMIT,
        "quota_message": TRIAL_MESSAGE,
        "streak_protections_month": 0,
        "daily_workout": False,
    },
    PLAN_FREE: {
        "plan_name": "Free",
        # 0 = ilimitado, e é o comportamento de HOJE: quota de conta ainda não existe (a
        # SPEC-016 propõe 10/dia, e quem a liga é a T-063). Migration de dados não muda produto.
        "daily_sessions": 0,
        "quota_message": "",
        "streak_protections_month": 1,
        "daily_workout": False,
    },
    PLAN_SUBSCRIBER: {
        "plan_name": "Assinatura",
        "daily_sessions": 0,
        "quota_message": "",
        "streak_protections_month": 2,
        "daily_workout": True,
    },
}

#: Capacidades iguais para todo plano no estado de hoje. Elas se diferenciam nas T-063/T-064;
#: aqui existem para que "ligar a SPEC-018" não mude comportamento nenhum.
_FLOOR_COMMON: dict[str, Any] = {
    "session_min_s": 30,
    "session_max_s": 30,
    "countdown_max_s": 10,
    "allow_cloud": True,
    "history_limit": 50,
    "kcal_accumulation": False,
    "effects_enabled": False,
    "min_maturity": "validado",
}

#: Piso do `SiteConfig`. Mesmos números das constantes que já existiam
#: (`sessions.DEFAULT_DURATION_S`, `events.DEFAULT_COUNTDOWN_S`, `slots.DEFAULT_CLOUD_SLOTS`,
#: `slots.GRACE_MS`, `tokens.DEFAULT_TTL_S`, `configPrefs.ts`).
_FLOOR_SITE: dict[str, Any] = {
    "default_duration_s": 30,
    "default_countdown_s": 3,
    "cloud_slots": 3,
    "cloud_grace_ms": 15_000,
    "ticket_ttl_s": 45,
    "series_min": 1,
    "series_max": 9,
    "series_default": 1,
    "reps_min": 5,
    "reps_max": 30,
    "reps_default": 15,
    "version": 0,
}

_PLAN_FIELDS = (
    "daily_sessions",
    "session_min_s",
    "session_max_s",
    "countdown_max_s",
    "allow_cloud",
    "history_limit",
    "kcal_accumulation",
    "effects_enabled",
    "streak_protections_month",
    "min_maturity",
    "daily_workout",
    "quota_message",
)


def _floor(slug: str) -> dict[str, Any]:
    """Piso completo de um plano, sem tocar em banco nem em cache."""
    base = _FLOOR_PLAN.get(slug) or _FLOOR_PLAN[PLAN_FREE]
    return {"plan_slug": slug, "flags": {}, **_FLOOR_COMMON, **base}


def _read_snapshot_from_db() -> dict[str, Any]:
    """Snapshot cru do Postgres: todos os planos + o singleton de site."""
    from api.models import Plan, SiteConfig

    planos: dict[str, dict[str, Any]] = {}
    default_slug = PLAN_FREE
    for plano in Plan.objects.all():
        planos[plano.slug] = {
            "plan_slug": plano.slug,
            "plan_name": plano.nome,
            "flags": plano.flags or {},
            **{campo: getattr(plano, campo) for campo in _PLAN_FIELDS},
        }
        if plano.is_default:
            default_slug = plano.slug

    site = SiteConfig.objects.filter(pk=1).values(*_FLOOR_SITE.keys()).first()
    return {
        "plans": planos,
        "default_slug": default_slug,
        "site": dict(site) if site else dict(_FLOOR_SITE),
    }


def _snapshot() -> tuple[dict[str, Any], bool]:
    """Snapshot de configuração e se ele veio mesmo do banco.

    Nada aqui propaga exceção: cache fora → consulta direta; banco fora → piso do código. É o
    P2 escrito como fluxo de controle, e é o motivo de o `except Exception` largo ser
    intencional em vez de descuido — a alternativa (deixar subir) é derrubar um treino.
    """
    try:
        guardado = cache.get(SNAPSHOT_KEY)
    except Exception:  # cache fora do ar não é motivo para não ler o banco
        logger.warning("cache indisponível ao ler configuração; consultando o banco", exc_info=True)
        guardado = None

    if guardado:
        return guardado, True

    try:
        fresco = _read_snapshot_from_db()
    except Exception:
        logger.warning("configuração fora do ar; usando os defaults do código", exc_info=True)
        return {"plans": {}, "default_slug": PLAN_FREE, "site": dict(_FLOOR_SITE)}, False

    with_suppressed_cache_errors(lambda: cache.set(SNAPSHOT_KEY, fresco, SNAPSHOT_TTL_S))
    return fresco, True


def with_suppressed_cache_errors(acao) -> None:
    """Escrita em cache é otimização: falhar nela não pode virar erro de requisição."""
    try:
        acao()
    except Exception:
        logger.warning("falha ao gravar o snapshot de configuração no cache", exc_info=True)


def _plan_slug_for(user, *, now: datetime | None = None, default_slug: str) -> str:
    """Qual plano vale para este solicitante, agora.

    A expiração é resolvida **na leitura** e não por job: um cron que rebaixasse contas seria um
    segundo lugar onde o plano é decidido, e o dia em que ele não rodasse ninguém notaria.
    """
    if user is None:
        return PLAN_ANON
    plano = getattr(user, "plan", None)
    if plano is None:
        return default_slug
    vence_em = getattr(user, "plan_until", None)
    if vence_em is not None and vence_em <= (now or datetime.now(UTC)):
        return default_slug
    return plano.slug


def capabilities_for(user=None, *, now: datetime | None = None) -> Capabilities:
    """O que este solicitante pode. **Nunca levanta exceção** (P2).

    `user=None` é o anônimo, e é o caso normal: a Fase 0 inteira é sem conta.
    """
    dados, _ = _snapshot()
    slug = _plan_slug_for(user, now=now, default_slug=dados.get("default_slug", PLAN_FREE))

    # Plano ausente da tabela não é erro: é o estado antes da migration de dados, e o estado
    # depois de alguém apagar uma linha no painel. Cai no piso do próprio slug — que é o
    # comportamento de ontem, não uma capacidade vazia.
    do_banco = (dados.get("plans") or {}).get(slug)
    plano = {**_floor(slug), **(do_banco or {})}

    site = {**_FLOOR_SITE, **(dados.get("site") or {})}
    return Capabilities(
        plan_name=plano.get("plan_name", slug),
        config_version=int(site.pop("version", 0)),
        from_db=do_banco is not None,
        **{campo: plano[campo] for campo in ("plan_slug", "flags", *_PLAN_FIELDS)},
        **site,
    )


def invalidate_snapshot(**_kwargs) -> None:
    """Derruba o snapshot e incrementa a versão da configuração.

    `queryset.update()` e não `instance.save()` para o incremento: `update` não dispara
    `post_save`, então o bump não se realimenta. É a diferença entre um contador e um laço.
    """
    from api.models import SiteConfig

    try:
        # Sem linha ainda (banco novo antes da migration de dados) não há o que incrementar, e
        # criar uma aqui só para contar seria escrever no caminho de um signal.
        SiteConfig.objects.filter(pk=1).update(version=F("version") + 1)
    except Exception:
        logger.warning("não foi possível incrementar a versão da configuração", exc_info=True)

    with_suppressed_cache_errors(lambda: cache.delete(SNAPSHOT_KEY))
