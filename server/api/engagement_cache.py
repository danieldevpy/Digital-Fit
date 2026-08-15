"""A metade com I/O do engajamento (SPEC-019, T-086): consulta, cache e invalidação.

`api/engagement.py` é puro por contrato — a spec pede isso com todas as letras, e é o que
torna as fixtures listas de datas escritas à mão. Este módulo é o outro lado: ele lê o banco,
monta as `Sessao` e guarda o resultado pronto no Redis.

**Módulo próprio, e não o fim do `views.py`, por uma razão concreta.** Os signals que invalidam
o cache são ligados no `AppConfig.ready()`, e importar `api.views` de lá arrasta
`api.sessions` → `workers.analysis_worker` para dentro do *startup* do Django — que quebra
qualquer `manage.py` rodado de um diretório onde `workers` não está no path. O engajamento não
tem nada que ver com o registro de FSMs; a fronteira aqui evita a dependência acidental.
"""

from __future__ import annotations

import logging
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from api import engagement as regra
from api.config import capabilities_for

__all__ = [
    "invalidar_por_resultado",
    "invalidar_por_usuario",
    "payload_de",
    "sessoes_de",
]

logger = logging.getLogger("api")

#: Colunas que a derivação precisa. Cinco, e não a linha inteira: o streak precisa de **todas**
#: as datas do usuário (não dá para paginar como o histórico), e trazer os JSONs de cadência
#: junto faria a consulta crescer com o número de sessões sem nenhum uso.
_COLUNAS = ("exercise", "rep_count", "created_at", "feedback_counts", "scene_warning_counts")


def sessoes_de(usuario) -> list[regra.Sessao]:
    """As sessões do usuário, no formato da derivação.

    Sem `HISTORY_LIMIT`: o histórico mostra as 50 últimas, mas o fogo precisa de todas as datas
    — cortar em 50 encurtaria a sequência de quem treina todo dia, que é exatamente quem a
    mecânica existe para premiar.
    """
    from api.models import SessionClaim, SessionResult

    ids = SessionClaim.objects.filter(user=usuario).values_list("session_id", flat=True)
    linhas = SessionResult.objects.filter(session_id__in=ids).values_list(*_COLUNAS)
    return [
        regra.Sessao(
            exercise=exercise,
            rep_count=rep_count,
            created_at=created_at,
            feedback_counts=feedback_counts or {},
            scene_warning_counts=scene_warning_counts or {},
        )
        for exercise, rep_count, created_at, feedback_counts, scene_warning_counts in linhas
    ]


def _derivar(usuario) -> dict[str, Any]:
    """Deriva do banco, sem tocar no cache. É o caminho que o cache existe para evitar — e o
    caminho que responde igual quando o Redis está fora (P2 da SPEC-018)."""
    caps = capabilities_for(usuario)
    return regra.resumo(
        sessoes_de(usuario),
        hoje=regra.dia_sp(timezone.now()),
        protecoes_mes=caps.streak_protections_month,
        meta=usuario.daily_goal,
        # Vazio até a T-098: nenhum exercício é `hold` hoje, e slug ausente do mapa vale `reps`.
        # Quando a coluna existir, este argumento passa a sair do catálogo — e é o único lugar
        # que muda, porque a modalidade entra na derivação por parâmetro.
        scoring_por_slug={},
    ).to_dict()


def payload_de(usuario) -> dict[str, Any]:
    """Corpo do `GET /api/engagement`, do cache quando houver.

    Cache é otimização, nunca fonte: as duas travessias estão em `try` porque Redis fora do ar
    tem de sair mais devagar, não com erro na cara de quem ia ver o próprio fogo.
    """
    chave = regra.chave_de_cache(usuario.pk, regra.dia_sp(timezone.now()))

    try:
        guardado = cache.get(chave)
    except Exception:
        logger.warning("cache indisponivel ao ler engajamento; derivando direto", exc_info=True)
        return _derivar(usuario)

    if guardado is not None:
        return guardado

    corpo = _derivar(usuario)
    try:
        cache.set(chave, corpo, regra.ttl_ate_a_virada(timezone.now()))
    except Exception:
        logger.warning("falha ao gravar o engajamento no cache", exc_info=True)
    return corpo


def invalidar_por_resultado(instance=None, **_kwargs) -> None:
    """Derruba o cache do dono da sessão quando o relatório dela é gravado.

    O `SessionResult` **não sabe de quem é** — e não pode saber, porque ele é derivável por
    replay do stream e um replay não conhece quem estava logado (SPEC-010). O dono vive no
    `SessionClaim`, então a invalidação custa uma consulta por relatório escrito: uma vez por
    sessão, no processo do report-builder, fora do hot path dos 30 s.

    Sessão anônima não tem cache para limpar e sai pelo `if` — e é o caso mais comum do produto.
    """
    from api.models import SessionClaim

    try:
        dono = (
            SessionClaim.objects.filter(session_id=instance.session_id)
            .values_list("user_id", flat=True)
            .first()
        )
        if dono is not None:
            _limpar(dono)
    except Exception:
        # Cache velho por um dia é ruim; derrubar a gravação do relatório por causa dele seria
        # pior — o relatório é o dado, o engajamento é só a leitura dele.
        logger.warning("nao foi possivel invalidar o engajamento", exc_info=True)


def invalidar_por_usuario(instance=None, **_kwargs) -> None:
    """Meta diária e plano mudam o corpo sem passar por sessão nenhuma."""
    try:
        _limpar(instance.pk)
    except Exception:
        logger.warning("nao foi possivel invalidar o engajamento", exc_info=True)


def _limpar(user_id: int) -> None:
    """Apaga a chave de HOJE.

    Só a de hoje: as de ontem já expiraram sozinhas pelo TTL, e varrer chaves por padrão
    (`KEYS df:eng:*`) é a operação que trava um Redis em produção.
    """
    cache.delete(regra.chave_de_cache(user_id, regra.dia_sp(timezone.now())))
