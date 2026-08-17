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

import hashlib
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any

from django.core.cache import cache
from django.db.models import F

from api.models import MATURITY_RANK, Maturity
from api.quota import FREE_LIMIT, FREE_MESSAGE, TRIAL_LIMIT, TRIAL_MESSAGE

__all__ = [
    "COUNTED_MIN_CEILING_S",
    "PLAN_ANON",
    "PLAN_FREE",
    "PLAN_SUBSCRIBER",
    "SNAPSHOT_KEY",
    "SNAPSHOT_TTL_S",
    "Capabilities",
    "capabilities_for",
    "config_etag",
    "config_payload",
    "exercises_for",
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

#: Teto mínimo de sessão para o modo contado existir naquele plano (SPEC-023 §4, T-136).
#:
#: A spec diz "`session_max_s` generoso" e não dá número, porque o número é uma decisão de
#: produto. Este é ele: **o dobro da janela livre de 30 s**. Um teto menor que isso não é teto de
#: série, é a mesma janela competitiva com outro nome — e o modo contado existe justamente para
#: ser o oposto dela ("um aplicativo que não te apressa"). Com 60 s, uma meta de 15 repetições
#: cabe até uma cadência de 15 rpm, que é lento de verdade.
#:
#: É constante de código e não coluna nem `SiteConfig` de propósito. Coluna nova está proibida
#: pela §4 (a lição do `Plan.history_limit`), e derivar a régua de outro campo editável
#: (`default_duration_s`, `session_min_s`) faria alguém baixar a janela no painel e destravar o
#: modo contado em plano que não o suporta — sem ninguém perceber, que é o pior jeito de uma
#: trava falhar. A régua fica parada; o que o painel move é o teto de cada plano.
COUNTED_MIN_CEILING_S = 60


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

    @property
    def allows_counted(self) -> bool:
        """Este plano suporta o modo contado (SPEC-023 §4)?

        **O gate do modo contado é o teto do plano, e não uma flag própria.** É o que a §4
        decidiu: o teto da série contada é o `session_max_s` que já existe, então um plano cujo
        teto é a janela de 30 s (o Free de hoje) não tem onde a série contada acontecer — ela
        seria cortada no meio, que é exatamente o que o modo existe para não fazer. Recusar na
        admissão é dizer isso na hora certa; deixar entrar seria prometer "sem pressa" e cobrar
        30 s.

        Mora aqui, junto de `duration_s`/`countdown_s`, porque é a mesma pergunta que esta
        classe responde ("o que este solicitante pode") — e porque o `GET /api/config` e a
        admissão precisam da MESMA resposta. Dois lugares calculando isto divergiriam, e a
        divergência apareceria como um montador que oferece a meta e um `POST /sessions` que a
        recusa: o `[A/T-051]` de novo.
        """
        return self.session_max_s >= COUNTED_MIN_CEILING_S

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

    def target_reps(self, requested: int | None = None) -> int:
        """Meta efetiva da série contada, dentro da faixa que o painel publica (SPEC-023 §2).

        A faixa é a MESMA dos steppers (`reps_min`/`reps_max`/`reps_default`): o servidor não
        pode ter uma régua para desenhar o montador e outra para admitir a série — a segunda
        régua é o que transforma um cliente adulterado numa meta de 500 repetições.

        `clamp` e não recusa, como em `duration_s`: a meta é escolha de quem treina, e um número
        fora da faixa vira o número da faixa em vez de virar mensagem de erro. `0` (ou ausente)
        cai no default — modo contado sem meta é contrato malformado, e o worker já degrada esse
        caso para o comportamento de sempre; resolver aqui evita que ele chegue lá.
        """
        alvo = requested or self.reps_default
        return max(self.reps_min, min(self.reps_max, alvo))


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
        # 10/dia desde a T-063 (SPEC-016). O piso é o número REAL do produto, não `0`: se
        # fosse `0` (ilimitado), um Postgres fora do ar entregaria sessões sem limite a todo
        # mundo, em silêncio e sem ninguém perceber até a fatura da VPS. Piso é "o produto de
        # ontem", e o produto de ontem tem limite.
        "daily_sessions": FREE_LIMIT,
        "quota_message": FREE_MESSAGE,
        "streak_protections_month": 1,
        "daily_workout": False,
    },
    PLAN_SUBSCRIBER: {
        "plan_name": "Assinatura",
        "daily_sessions": 0,
        "quota_message": "",
        "streak_protections_month": 2,
        # O Laboratório 🧪 da SPEC-020 §Planos: o assinante enxerga `calibrado`, que é exercício
        # com corpus real medido mas sem a semana de produção do `validado`. É o degrau que a
        # assinatura compra neste eixo — **antecipação**, não exclusividade —, e sem este valor
        # o eixo inteiro da T-090 existiria sem nunca mudar nada para ninguém.
        "min_maturity": Maturity.CALIBRADO.value,
        "daily_workout": True,
        # O teto que torna o modo contado possível (SPEC-023 §4, T-136). Três minutos: 15
        # repetições a 5 rpm, que é mais lento do que qualquer pessoa que ainda está treinando.
        # É o **único** lugar onde o piso do código deixa de ser "o produto de ontem", e é de
        # propósito — ele acompanha a migration `0007` para que um Postgres fora do ar não
        # tire do assinante um modo que ele acabou de pagar. Os outros planos ficam em 30 s
        # (`_FLOOR_COMMON`), que é o cadeado da SPEC-016.
        "session_max_s": 180,
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
    """Snapshot cru do Postgres: planos + catálogo + o singleton de site."""
    from api.models import Exercise, Plan, SiteConfig

    planos: dict[str, dict[str, Any]] = {}
    default_slug = PLAN_FREE
    ordem_do_plano: dict[str, int] = {}
    for plano in Plan.objects.all():
        planos[plano.slug] = {
            "plan_slug": plano.slug,
            "plan_name": plano.nome,
            "flags": plano.flags or {},
            **{campo: getattr(plano, campo) for campo in _PLAN_FIELDS},
        }
        ordem_do_plano[plano.slug] = plano.ordem
        if plano.is_default:
            default_slug = plano.slug

    exercicios: list[dict[str, Any]] = []
    consulta = Exercise.objects.select_related("min_plan").prefetch_related("guide_steps")
    for ex in consulta:
        exercicios.append(
            {
                "slug": ex.slug,
                "display_name": ex.display_name,
                "category": ex.category,
                "muscle_group": ex.muscle_group,
                "default_tip": ex.default_tip,
                "main_angle": ex.main_angle,
                "demo_img": ex.demo_img,
                "scene_tip": ex.scene_tip,
                "dot_color": ex.dot_color,
                "met": float(ex.met),
                "ref_cadence_rpm": ex.ref_cadence_rpm,
                "maturity": ex.maturity,
                "enabled": ex.enabled,
                "min_plan": ex.min_plan.slug if ex.min_plan else None,
                "guide_steps": [
                    {"img": passo.img, "text": passo.texto} for passo in ex.guide_steps.all()
                ],
            }
        )

    site = SiteConfig.objects.filter(pk=1).values(*_FLOOR_SITE.keys()).first()
    return {
        "plans": planos,
        "plan_order": ordem_do_plano,
        "default_slug": default_slug,
        "exercises": exercicios,
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


def exercises_for(user=None, *, now: datetime | None = None) -> dict[str, dict[str, Any]]:
    """Os exercícios que este solicitante pode ver **e abrir**, por slug.

    **Um resolvedor só para as duas perguntas.** O `GET /api/config` é este dicionário
    serializado; a admissão é `slug in exercises_for(...)`. Duas listas construídas por dois
    códigos diferentes divergiriam, e divergiriam do pior jeito possível: um card na tela que o
    `POST /sessions` recusa — que é literalmente o `[A/T-051]` que esta task veio fechar.

    Eixos: `enabled`, `min_plan` (T-074) e **maturidade** (T-090) — o terceiro entrou aqui
    dentro, nesta mesma função e não ao lado dela, como a SPEC-020 pede. Ver
    `_visivel_por_maturidade`.

    Degradação (P2) com uma nuance: sem catálogo no banco, devolve o registro de código
    (`EXERCISES`) — que é o comportamento de ontem, quando a admissão só checava o registro.
    Mas a exclusividade por plano falha **fechada**: se há `min_plan` e a ordem dos planos não
    resolve, o exercício some. Fechar o resto também deixaria a tela Escolha vazia num soluço de
    banco; deixar a exclusividade aberta entregaria conteúdo pago de graça. Os dois lados falham
    para o lado certo de cada um.
    """
    from workers.analysis_worker.exercises import EXERCISES

    dados, _ = _snapshot()
    catalogo = dados.get("exercises") or []
    if not catalogo:
        return {slug: {"slug": slug} for slug in EXERCISES}

    ordens = dados.get("plan_order") or {}
    caps = capabilities_for(user, now=now)
    minha_ordem = ordens.get(caps.plan_slug)
    is_admin = bool(getattr(user, "is_admin", False))

    visiveis: dict[str, dict[str, Any]] = {}
    for ex in catalogo:
        if not ex.get("enabled"):
            continue
        # Slug que saiu do registro (exercício removido do código, linha esquecida na tabela)
        # não pode aparecer: a admissão o recusaria, e o card seria um botão quebrado.
        if ex["slug"] not in EXERCISES:
            continue
        if not _visivel_por_maturidade(
            ex.get("maturity"), min_maturity=caps.min_maturity, is_admin=is_admin
        ):
            continue
        exigido = ex.get("min_plan")
        if exigido:
            ordem_exigida = ordens.get(exigido)
            if minha_ordem is None or ordem_exigida is None or minha_ordem < ordem_exigida:
                continue
        visiveis[ex["slug"]] = ex
    return visiveis


def _visivel_por_maturidade(maturidade: Any, *, min_maturity: str, is_admin: bool) -> bool:
    """O eixo maturidade da SPEC-020, em três linhas e uma ortogonalidade.

    **`beta` nunca é liberado por plano.** É ferramenta de dev, não degrau comercial: um
    exercício `beta` tem limiares calibrados só contra o boneco sintético, e a lição do
    `[A/T-106]` é que isso não sobrevive a gente de verdade. A comparação ordenada
    (`MATURITY_RANK`) resolveria o caso por acidente — `beta` vale 0 e os dois valores que o
    `Plan` aceita valem 1 e 2 —, mas por *acidente*: bastaria alguém gravar `min_maturity="beta"`
    por SQL, fora do formulário que valida, para o produto inteiro passar a mostrar exercício de
    laboratório. O `if` explícito é o que torna a regra uma regra.

    **Maturidade desconhecida some para quem não é admin.** Valor fora do vocabulário (linha
    editada por fora, nível novo em deploy pela metade) não é `validado`, e tratá-lo como tal
    liberaria justamente o caso em que ninguém sabe o que aquilo é.

    `is_admin` vê tudo — é o mesmo direito das ferramentas de dev da T-048, e o único jeito de
    alguém conferir um `beta` em produção antes de promovê-lo.
    """
    texto = str(maturidade or "")
    if texto == Maturity.BETA.value:
        return is_admin
    if is_admin:
        return True
    return MATURITY_RANK.get(texto, -1) >= MATURITY_RANK.get(min_maturity, 0)


def config_payload(user=None, *, now: datetime | None = None) -> dict[str, Any]:
    """Corpo do `GET /api/config` — catálogo e capacidades num payload só (SPEC-018)."""
    caps = capabilities_for(user, now=now)
    catalogo = exercises_for(user, now=now)

    return {
        "config_version": caps.config_version,
        "plan": {
            "slug": caps.plan_slug,
            "name": caps.plan_name,
            "daily_sessions": caps.daily_sessions,
            "quota_message": caps.quota_message,
            "allow_cloud": caps.allow_cloud,
            "history_limit": caps.history_limit,
            "kcal_accumulation": caps.kcal_accumulation,
            "effects_enabled": caps.effects_enabled,
            "flags": caps.flags,
        },
        "session": {
            "duration_s": caps.duration_s(),
            "min_s": caps.session_min_s,
            "max_s": caps.session_max_s,
            "countdown_default_s": caps.default_countdown_s,
            "countdown_max_s": caps.countdown_max_s,
            # SPEC-023 §4: se este plano tem modo contado. Booleano pronto, e não a régua para o
            # cliente aplicar sobre `max_s`: quem decide é a admissão (`resolve_set`), e uma
            # segunda implementação da mesma comparação divergiria no dia em que a régua mudasse
            # — com o sintoma aparecendo como um montador que oferece a meta e um
            # `POST /sessions` que responde 403. A trava continua sendo o servidor; isto é só o
            # que permite a UI refletir a trava em vez de descobri-la batendo nela (mesmo papel
            # do `GET /api/quota` na SPEC-016).
            "counted": caps.allows_counted,
        },
        "steppers": {
            "series_min": caps.series_min,
            "series_max": caps.series_max,
            "series_default": caps.series_default,
            "reps_min": caps.reps_min,
            "reps_max": caps.reps_max,
            "reps_default": caps.reps_default,
        },
        # Lista e não dicionário: a ordem de exibição é dado, e objeto JSON não promete ordem.
        "exercises": _catalogo_serializado(catalogo),
        # Dicionário aqui, ao contrário do catálogo: quem lê procura POR código, e não existe
        # ordem de exibição — o relatório ordena por frequência, o HUD por prioridade.
        "feedback": _mensagens_de_feedback(),
    }


@lru_cache(maxsize=1)
def _mensagens_de_feedback() -> dict[str, dict[str, str]]:
    """Código → texto em pt-BR, do mesmo YAML que o feedback engine carrega (SPEC-018 §C).

    **Por que o cliente precisa disto.** O `feedback.issued` que chega ao vivo traz a frase
    pronta, mas o relatório (SPEC-010) guarda só `{código: contagem}` — e aí o cliente tem de
    traduzir sozinho. Ele traduzia com um mapa próprio, escrito quando o polichinelo era o
    único exercício que contava; hoje há oito códigos de execução e o mapa conhece dois. Os
    outros seis chegavam à tela em CAIXA ALTA, com nome de constante.

    A alternativa era copiar as frases para dentro do bundle. Seria a mesma decisão de novo, só
    que maior: dois arquivos de texto para manter em sincronia, e a promessa da SPEC-018 §C
    ("reescrever sem deploy") valendo para o HUD e não para o relatório.

    `lru_cache` porque o arquivo é do deploy, não do banco: mudou o YAML, mudou o processo.
    """
    try:
        from workers.analysis_worker.feedback import FeedbackCatalog

        entradas = FeedbackCatalog.load().entries
    except Exception:  # P2: configuração indisponível nunca derruba a resposta.
        logger.warning("catalogo de feedback indisponivel; cliente cai no embutido", exc_info=True)
        return {}

    return {
        code.value: {"message": entrada.message, **({"hint": entrada.hint} if entrada.hint else {})}
        for code, entrada in entradas.items()
    }


#: Campos que ficam no servidor. `enabled` e `min_plan` são a *regra*: quem chegou ao payload já
#: passou por ela, e mandá-la junto contaria ao Free o que existe atrás do cadeado. O cadeado com
#: motivo é a T-091, e mesmo lá o motivo é texto, não a regra.
_INTERNO = frozenset({"enabled", "min_plan"})


def _catalogo_serializado(catalogo: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Serializa o catálogo resolvido para o cliente.

    Devolve **lista vazia** quando o que há é só o piso do registro (slugs sem apresentação,
    banco fora): vazio quer dizer "não sei, use o seu", e é assim que o cliente lê. Mandar
    `{"slug": "squat"}` sem nome faria a tela Escolha desenhar um card em branco — pior que não
    mandar nada, porque parece dado.
    """
    completos = [ex for ex in catalogo.values() if "display_name" in ex]
    return [{k: v for k, v in ex.items() if k not in _INTERNO} for ex in completos]


def config_etag(user=None, *, now: datetime | None = None) -> str:
    """ETag por (versão, plano, `is_admin`) — as três dimensões que mudam o corpo.

    Um ETag só sobre `config_version` seria um vazamento: o payload varia por plano (capacidades
    e, com a SPEC-020, o próprio conteúdo do catálogo), então um proxy no caminho serviria a
    resposta do assinante para o próximo Free que revalidasse. Junto com `Cache-Control: private`
    na view, é o que impede a trava de plano de ser furada por cache.
    """
    caps = capabilities_for(user, now=now)
    is_admin = bool(getattr(user, "is_admin", False))
    cru = f"{caps.config_version}|{caps.plan_slug}|{int(is_admin)}"
    return '"' + hashlib.sha256(cru.encode()).hexdigest()[:16] + '"'


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
