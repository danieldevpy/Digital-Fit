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
import time
from datetime import date
from typing import Any

from django.core.cache import cache
from django.utils import timezone

from api import engagement as regra
from api.config import capabilities_for
from api.fuso import FUSO_PADRAO
from api.i18n import DEFAULT_LOCALE
from api.i18n import messages as i18n_messages

__all__ = [
    "chave_de_cache",
    "com_xp",
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


def _versao_de(user_id: int) -> str:
    """O selo que invalida o cache deste usuário sem apagar chave nenhuma (T-156).

    **Por que deixou de ser `cache.delete`.** A chave ganhou o fuso como quinta dimensão, e
    fuso não se enumera: são centenas de nomes IANA, e o `_limpar` roda FORA de qualquer
    requisição (signal de `SessionResult`/`User`), sem `X-Timezone` nenhum para saber quais
    existem. O truque de percorrer os locales — que já era um remendo declarado na T-143 —
    simplesmente não escala para a dimensão nova, e varrer por padrão (`KEYS df:eng:*`) é a
    operação que trava um Redis em produção.

    Então a invalidação para de apagar e passa a **mudar o endereço**: o selo entra na chave, e
    trocá-lo torna inalcançável tudo o que foi escrito antes, em qualquer fuso e qualquer
    idioma, de uma vez. O lixo some sozinho pelo TTL, que nunca passa de um dia.

    Custa uma leitura a mais por payload. Vale: o `_limpar` deixou de ter um `for` sobre uma
    dimensão e de estar errado sobre a outra.
    """
    try:
        selo = cache.get(_chave_de_versao(user_id))
    except Exception:
        logger.warning("cache indisponivel ao ler a versao do engajamento", exc_info=True)
        return "0"
    return str(selo) if selo is not None else "0"


def _chave_de_versao(user_id: int) -> str:
    return f"df:eng:v:{user_id}"


def chave_de_cache(user_id: int, hoje: date, locale: str, fuso: str = str(FUSO_PADRAO)) -> str:
    """`{chave pura}:{locale}:{fuso}` — as dimensões de transporte da chave (T-143, T-156).

    **Composta aqui em cima da chave pura, e não dentro dela.** `api.engagement.chave_de_cache`
    é a metade sem I/O do engajamento (contrato da SPEC-019: função pura, sem locale, sem nada
    que não seja `(user, dia)`) — a negociação de locale é harness de transporte da SPEC-025, não
    regra de derivação, e não é este módulo que decide onde a fronteira entre as duas fica.

    **Por que o locale precisa estar na chave.** O corpo guardado é o payload já renderizado por
    `payload_de` (`_derivar` → `regra.resumo(...).to_dict()` + nome/descrição de conquista
    resolvidos por `_conquistas_traduzidas`, T-145), em qualquer locale suportado. Sem o locale
    na chave, a primeira leitura do dia grava UM idioma sob a chave `(user, dia)`, e todo mundo
    que ler depois — inclusive alguém que troque o app para outra língua no mesmo dia — recebe
    essa mesma resposta pronta até a meia-noite de São Paulo, mesmo pedindo em outra língua.

    **Por que o fuso também precisa estar na chave** (T-156). O `hoje` já é o dia resolvido no
    fuso de quem pediu — mas duas pessoas em fusos diferentes podem estar no MESMO dia-calendário
    e mesmo assim discordar sobre a que dia pertence uma sessão das 23h30. O payload guardado
    traz o streak e a meta de hoje já contados; sem o fuso na chave, o primeiro a ler grava a
    contagem do fuso dele para quem vier depois no mesmo dia.
    """
    return f"{regra.chave_de_cache(user_id, hoje)}:{locale}:{fuso}"


def _conquistas_traduzidas(conquistas: list[dict[str, Any]], locale: str) -> list[dict[str, Any]]:
    """Acrescenta `name`/`description` a cada conquista do catálogo puro (SPEC-025, T-145).

    `regra.catalogo_de_conquistas` devolve só `slug`+`earned` (`Conquista` não sabe de locale,
    ver `api/engagement.py`); o texto vem de `server/api/i18n/messages.<locale>.yaml`, resolvido
    aqui — na metade com I/O — e não lá.
    """
    catalogo = i18n_messages.load(locale)
    traduzidas = []
    for conquista in conquistas:
        texto = catalogo.achievement(conquista["slug"])
        traduzidas.append(
            {
                **conquista,
                "name": texto.get("name", conquista["slug"]),
                "description": texto.get("description", ""),
            }
        )
    return traduzidas


def _derivar(usuario, *, locale: str, fuso=FUSO_PADRAO) -> dict[str, Any]:
    """Deriva do banco, sem tocar no cache. É o caminho que o cache existe para evitar — e o
    caminho que responde igual quando o Redis está fora (P2 da SPEC-018)."""
    caps = capabilities_for(usuario)
    corpo = regra.resumo(
        sessoes_de(usuario),
        hoje=regra.dia_do_fogo(timezone.now(), fuso),
        fuso=fuso,
        protecoes_mes=caps.streak_protections_month,
        meta=usuario.daily_goal,
        # Vazio até a T-098: nenhum exercício é `hold` hoje, e slug ausente do mapa vale `reps`.
        # Quando a coluna existir, este argumento passa a sair do catálogo — e é o único lugar
        # que muda, porque a modalidade entra na derivação por parâmetro.
        scoring_por_slug={},
    ).to_dict()
    corpo["achievements"] = _conquistas_traduzidas(corpo["achievements"], locale)
    return corpo


def payload_de(usuario, *, locale: str = DEFAULT_LOCALE, fuso=FUSO_PADRAO) -> dict[str, Any]:
    """Corpo do `GET /api/engagement`, do cache quando houver.

    Cache é otimização, nunca fonte: as duas travessias estão em `try` porque Redis fora do ar
    tem de sair mais devagar, não com erro na cara de quem ia ver o próprio fogo.

    `locale` entra na chave (`chave_de_cache`, SPEC-025) **e** no cálculo (T-145): `_derivar`
    resolve nome/descrição de conquista neste idioma antes de guardar. O default
    (`DEFAULT_LOCALE`) só cobre quem chama sem resolver locale nenhum, coerente com
    `api.i18n.resolve_locale` na mesma ausência de sinal.

    `fuso` faz o mesmo pelo eixo do tempo (T-156): decide qual dia é "hoje", entra na chave e
    manda no TTL. O default (`FUSO_PADRAO`) mantém intacto o comportamento de quem não manda
    `X-Timezone` — cliente antigo, `evalctl`, teste.
    """
    agora = timezone.now()
    chave = chave_de_cache(
        usuario.pk, regra.dia_do_fogo(agora, fuso), locale, f"{fuso}:{_versao_de(usuario.pk)}"
    )

    try:
        guardado = cache.get(chave)
    except Exception:
        logger.warning("cache indisponivel ao ler engajamento; derivando direto", exc_info=True)
        return _derivar(usuario, locale=locale, fuso=fuso)

    if guardado is not None:
        return guardado

    corpo = _derivar(usuario, locale=locale, fuso=fuso)
    try:
        cache.set(chave, corpo, regra.ttl_ate_a_virada(agora, fuso))
    except Exception:
        logger.warning("falha ao gravar o engajamento no cache", exc_info=True)
    return corpo


def com_xp(relatorio: dict[str, Any]) -> dict[str, Any]:
    """Acrescenta a decomposição de XP a um corpo de `to_report()` (SPEC-019 §Superfícies).

    **Enriquecimento na view, e não dentro de `to_report()`**, por duas razões que se somam:

    1. `to_report()` é o payload **replay-derivável** da SPEC-010 — o que sai dos eventos, e
       nada além. XP é leitura de produto sobre esse fato, e mora do lado de quem lê.
    2. XP não existe para o visitante (§Planos: anônimo não tem XP nem nível). Quem chama isto
       é a view, que sabe se há conta; `to_report()` não sabe e não deve saber.

    A chave é aditiva: cliente que não a conhece continua lendo o relatório como antes.
    """
    return {
        **relatorio,
        "xp": regra.decomposicao_de_xp(
            regra.Sessao(
                created_at=timezone.now(),  # não entra na conta do XP; só o construtor exige
                exercise=str(relatorio.get("exercise", "")),
                rep_count=int(relatorio.get("rep_count", 0)),
                feedback_counts=relatorio.get("feedback_counts") or {},
                scene_warning_counts=relatorio.get("scene_warning_counts") or {},
            )
        ),
    }


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
    """Muda o selo de versão deste usuário — o que torna inalcançável TODA chave anterior.

    Uma escrita, e acabou: vale para qualquer locale (o `for` que a T-143 precisava) e para
    qualquer fuso (que a T-156 não teria como enumerar). Ver `_versao_de` para o porquê de a
    invalidação ter deixado de apagar chave.

    O selo é o instante em nanossegundos, e não um contador: `cache.incr` exige a chave já
    existir, e o caso mais comum aqui é justamente a primeira invalidação de um usuário. Sem
    expiração de propósito — um selo que vencesse devolveria o cache velho ao alcance.
    """
    cache.set(_chave_de_versao(user_id), str(time.time_ns()), None)
