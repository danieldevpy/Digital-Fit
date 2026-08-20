"""Ciclo de vida da sessão de 30 s (SPEC-009, Fase Inicial).

A API cria a sessão, guarda um registro em Redis com TTL e devolve ao cliente o que ele precisa
para abrir o WebSocket. Quem conta o tempo de verdade é o `analysis-worker` (o timer do HUD é
cosmético) — aqui só nasce a sessão e se define o prazo.

Estado da sessão vive em Redis (`session:{id}`, hash com TTL), não em Postgres: a Fase 0 é
anônima e a sessão é efêmera. Persistência de resultado é a SPEC-010 (T-020).
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings

from api.i18n import SOURCE_LOCALE
from api.i18n import messages as i18n_messages
from api.tokens import DEFAULT_TTL_S, issue_token
from workers.analysis_worker.exercises import EXERCISES
from workers.shared.bus import RedisBus
from workers.shared.events import (
    DEFAULT_COUNTDOWN_S,
    CameraView,
    Mode,
    SessionCapability,
    SessionStarted,
    SetMode,
    Source,
    Stream,
    clamp_countdown_s,
    make_envelope,
    parse_camera_view,
    parse_set_mode,
)
from workers.shared.slots import CloudSlots

__all__ = [
    "COUNTED_UNAVAILABLE",
    "DEFAULT_DURATION_S",
    "DENIED_CLOUD",
    "CountedUnavailable",
    "SessionRequest",
    "SessionTicket",
    "SetPlan",
    "create_session",
    "resolve_set",
    "session_key",
]

#: Sessão de 30 s é a unidade de carga do produto (SPEC-009 / ADR-006).
DEFAULT_DURATION_S = 30

#: Resposta quando o cliente pede cloud e não há como atender.
DENIED_CLOUD = "denied_cloud"

#: Código da recusa do modo contado (HTTP 403). Distinto da quota porque a ação de quem lê é
#: outra: aqui não adianta esperar amanhã — ou treina no modo livre, ou muda de plano.
COUNTED_UNAVAILABLE = "counted_unavailable"

_bus: RedisBus | None = None


def bus() -> RedisBus:
    """Barramento da API (mesmo `RedisBus` dos workers)."""
    global _bus
    if _bus is None:
        _bus = RedisBus.from_url(settings.REDIS_URL)
    return _bus


def session_key(session_id: str) -> str:
    return f"session:{session_id}"


@dataclass(frozen=True, slots=True)
class SessionRequest:
    """Corpo do `POST /api/sessions` já validado."""

    exercise: str
    requested_mode: Mode
    probe: dict[str, Any] | None = None
    #: Preparação antes de a contagem valer (T-049). Preferência de quem treina, não medição.
    countdown_s: int = DEFAULT_COUNTDOWN_S
    #: De que lado a câmera está, escolhido na pré-configuração (T-111). `None` = não veio, e
    #: aí o exercício decide sozinho.
    view: CameraView | None = None
    #: O que o cliente PEDIU para esta série (SPEC-023). São pedidos, não resolução: quem decide
    #: o modo, a meta e o teto é `resolve_set`, com o plano na mão. O nome dos campos é o do
    #: contrato para que o caminho corpo → evento seja lido de uma vez só.
    set_mode: SetMode = SetMode.LIVRE
    target_reps: int = 0
    set_index: int = 0
    set_total: int = 0

    @classmethod
    def parse(cls, data: Any) -> SessionRequest:
        if not isinstance(data, dict):
            raise ValueError("corpo deve ser objeto JSON")

        exercise = str(data.get("exercise") or "jumping_jack")
        if exercise not in EXERCISES:
            disponiveis = ", ".join(sorted(EXERCISES))
            raise ValueError(f"exercicio desconhecido: {exercise!r} (disponiveis: {disponiveis})")

        bruto = data.get("requested_mode") or Mode.EDGE.value
        try:
            requested_mode = Mode(bruto)
        except ValueError:
            raise ValueError(f"requested_mode invalido: {bruto!r}") from None

        probe = data.get("probe_result")
        if probe is not None and not isinstance(probe, dict):
            raise ValueError("probe_result deve ser objeto")

        return cls(
            exercise=exercise,
            requested_mode=requested_mode,
            probe=probe,
            # `clamp` em vez de recusar: é conforto, não parâmetro de medição. Derrubar a
            # sessão inteira porque veio `-1` trocaria um treino por uma mensagem de erro.
            countdown_s=clamp_countdown_s(data.get("countdown_s", DEFAULT_COUNTDOWN_S)),
            # Mesma tolerância do `countdown_s`, e pelo mesmo motivo: vista desconhecida vira
            # "ninguém disse" em vez de derrubar a admissão. O cliente que mandar `lateral` em
            # vez de `profile` perde a escolha, não o treino — e o exercício ainda tem a
            # detecção geométrica embaixo.
            view=parse_camera_view(data.get("view")),
            # Mesma tolerância dos dois acima, e a mesma do worker (`parse_set_mode`): modo de
            # série desconhecido vira `livre`, que é o comportamento de todo cliente anterior à
            # SPEC-023. Recusar aqui faria um cliente novo, com um valor que este servidor ainda
            # não conhece, perder o treino inteiro.
            set_mode=parse_set_mode(data.get("set_mode")),
            target_reps=_pedido_inteiro(data.get("target_reps")),
            set_index=_pedido_inteiro(data.get("set_index")),
            set_total=_pedido_inteiro(data.get("set_total")),
        )


def _pedido_inteiro(valor: Any) -> int:
    """Número pedido pelo cliente: inteiro não negativo, `0` para qualquer coisa torta.

    Mesma leniência do `_stamp_int` do contrato, aplicada uma camada antes. `0` significa
    "não pediu" em todos os três campos, e é o que a resolução trata."""
    try:
        numero = int(valor)
    except (TypeError, ValueError):
        return 0
    return max(0, numero)


@dataclass(frozen=True, slots=True)
class SetPlan:
    """A série como o **servidor** a resolveu (SPEC-023 §4, T-136).

    É a resposta ao critério de aceite 4: forjar `target_reps` ou o teto no cliente não muda
    nada, porque o que viaja no `session.started` é este objeto — construído por `resolve_set`
    a partir do plano, e não do corpo da requisição. O cliente pede; o servidor resolve. Mesma
    prova da quota (SPEC-016 §4) e mesma razão pela qual o timer dos 30 s é autoridade do
    servidor (SPEC-009).

    `duration_s` mora aqui e não ao lado porque no modo contado ela **é** a resolução: o teto da
    série é o `session_max_s` do plano, e um teto separado do modo é o par que alguém esquece de
    atualizar junto — uma série contada com 30 s de teto seria cortada no meio, que é exatamente
    o defeito que a §4 existe para evitar.
    """

    set_mode: SetMode = SetMode.LIVRE
    target_reps: int = 0
    set_index: int = 0
    set_total: int = 0
    #: Janela no modo livre; **teto** no modo contado. O worker lê os dois casos pelo mesmo
    #: campo do evento (`duration_s`) — quem muda de significado é o modo, não o número.
    duration_s: int = DEFAULT_DURATION_S


class CountedUnavailable(Exception):
    """Modo contado pedido por quem não tem teto de sessão para ele (SPEC-023 §4).

    Exceção e não retorno de erro porque quem chama é a view, e o caminho dela é `return
    Response(403)`: um `SetPlan | Erro` obrigaria todo chamador a lembrar de checar qual dos
    dois veio — e o chamador que esquecesse admitiria a série contada assim mesmo.
    """

    def __init__(self, *, ceiling_s: int, locale: str = SOURCE_LOCALE) -> None:
        #: O teto que este plano tem hoje. A régua que ele não alcançou é
        #: `config.COUNTED_MIN_CEILING_S`, e ela não viaja na resposta: para quem lê, o que
        #: importa é o que o plano dele dá, não o número interno que o servidor compara.
        self.ceiling_s = ceiling_s
        # `detail` voltado ao cliente (SPEC-025, T-145): explica um limite de plano de verdade,
        # não um contrato de API — por isso sai do YAML, resolvido no idioma de quem pediu.
        # `locale` tem default (`SOURCE_LOCALE`) porque `resolve_set` é chamada também sem
        # requisição nenhuma (`evalctl`, teste) — nesses casos vale o texto de origem.
        texto = i18n_messages.load(locale).error("counted_unavailable", ceiling_s=ceiling_s)
        super().__init__(texto)


def resolve_set(request: SessionRequest, caps, *, locale: str = SOURCE_LOCALE) -> SetPlan:
    """Resolve a série na admissão: modo, meta, teto e o carimbo de posição no treino.

    Junto de quota, duração, countdown e cloud — todos resolvidos aqui, na fronteira da API, uma
    vez por sessão (P1 da SPEC-018). O worker não pergunta nada a ninguém: ele recebe o resultado
    carimbado no `session.started`, e é isso que mantém a promessa da SPEC-010 (o mesmo replay
    dá o mesmo relatório, hoje e daqui a um mês).

    **Modo livre não passa por nada disto.** Ele é o comportamento de hoje e continua sendo a
    janela do plano — a SPEC-023 §1 é explícita em não mudar uma linha dele, e é por isso que o
    caminho livre sai na primeira condição, sem tocar em meta nem em teto.

    **Modo contado exige teto** (`caps.allows_counted`): sem ele a recusa é legível e acontece
    ANTES de a sessão nascer e de a quota ser gasta. Cortar a série no meio seria a alternativa,
    e ela é pior de um jeito específico — a pessoa faria 8 de 15 e receberia um relatório dizendo
    que terminou.

    `set_index`/`set_total` são carimbo puro (§3): o servidor não é dono do treino na Fase
    Inicial, então ele não tem o que validar aí. Normaliza a incoerência e segue — "série 4 de 3"
    vira sessão avulsa, porque número errado na tela é pior do que número nenhum (SPEC-014).

    `locale` só importa para o texto da recusa (`CountedUnavailable`, SPEC-025, T-145) — não
    muda meta, teto nem modo. Default `SOURCE_LOCALE` porque esta função também é chamada sem
    requisição (`evalctl`, teste).
    """
    duracao_livre = caps.duration_s()
    if request.set_mode is not SetMode.CONTADO:
        return SetPlan(duration_s=duracao_livre, **_carimbo(request))

    if not caps.allows_counted:
        raise CountedUnavailable(ceiling_s=caps.session_max_s, locale=locale)

    return SetPlan(
        set_mode=SetMode.CONTADO,
        # A meta que vale é esta, não a do corpo: o cliente pede, o plano limita (`reps_min`…
        # `reps_max`), e o número resolvido é o que o worker usa para encerrar a série.
        target_reps=caps.target_reps(request.target_reps),
        # O teto é o `session_max_s` que já existe — sem coluna nova (§4). Note que ele NÃO
        # passa por `duration_s()`: aquele clamp entrega a janela do modo livre (o
        # `default_duration_s`, 30 s), e usá-lo aqui daria à série contada o teto de 30 s de
        # que ela acabou de provar não precisar.
        duration_s=caps.session_max_s,
        **_carimbo(request),
    )


def _carimbo(request: SessionRequest) -> dict[str, int]:
    """`set_index`/`set_total` normalizados (SPEC-023 §3).

    Carimbo incoerente (série 4 de 3, ou índice sem total) vira `0/0`, que é como toda sessão
    avulsa do passado se apresenta. O relatório prefere não dizer nada a dizer errado.
    """
    indice, total = request.set_index, request.set_total
    if indice < 1 or total < 1 or indice > total:
        return {"set_index": 0, "set_total": 0}
    return {"set_index": indice, "set_total": total}


@dataclass(frozen=True, slots=True)
class SessionTicket:
    """O que o cliente recebe para abrir o WebSocket."""

    session_id: str
    token: str
    ws_url: str
    mode: str
    exercise: str
    duration_s: int
    expires_at: int
    #: A série como o servidor a resolveu. Volta no ticket porque o HUD desenha `7/15` com ESTA
    #: meta: o cliente que pediu 500 precisa ver 30 na tela, senão a barra andaria contra um
    #: número que o worker não vai usar. Default livre — o ticket de toda sessão avulsa.
    set_plan: SetPlan = field(default_factory=SetPlan)

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "token": self.token,
            "ws_url": self.ws_url,
            "mode": self.mode,
            "exercise": self.exercise,
            "duration_s": self.duration_s,
            "expires_at": self.expires_at,
            # Aditivos e sempre presentes: cliente que não conhece a SPEC-023 ignora os quatro,
            # e cliente novo não precisa tratar ausência como "livre" (ausência também é o que
            # ele veria num corpo truncado — mesmo argumento do `quota` no ticket).
            "set_mode": self.set_plan.set_mode.value,
            "target_reps": self.set_plan.target_reps,
            "set_index": self.set_plan.set_index,
            "set_total": self.set_plan.set_total,
        }


def _ws_url(session_id: str, token: str) -> str:
    base = getattr(settings, "GATEWAY_WS_URL", "ws://localhost:8001").rstrip("/")
    return f"{base}/ws/session/{session_id}?token={token}"


def create_session(
    request: SessionRequest,
    *,
    duration_s: int = DEFAULT_DURATION_S,
    ttl_s: int = DEFAULT_TTL_S,
    countdown_s: int | None = None,
    now: int | None = None,
    redis_client=None,
    event_bus=None,
    slots=None,
    caps=None,
    set_plan: SetPlan | None = None,
) -> SessionTicket:
    """Admite a sessão: registra em Redis, publica `session.started` e devolve o ticket.

    Edge entra sempre (sem limite na Fase Inicial). Cloud depende do plano (`allow_cloud`,
    SPEC-018) **e** de vaga no semáforo (`slots:cloud = 3`, SPEC-009): sem qualquer um dos dois,
    a resposta é `mode: "denied_cloud"` e o cliente trata como indisponibilidade momentânea. Os
    dois motivos dão a mesma resposta de propósito — para quem está do outro lado, "seu plano não
    tem" e "não há vaga agora" pedem a mesma ação, e distinguir aqui só vazaria configuração.

    `caps` é o resultado de `capabilities_for()`, resolvido pela view (P1: quem lê configuração é
    a fronteira da API). Ausente, os parâmetros explícitos mandam — é o que mantém esta função
    testável sem banco, como ela já era.

    `config_version` é a exceção a essa regra: sai de `caps` sozinho, sem o chamador pedir. Ele
    não é uma escolha da admissão (como duração e countdown, que o cliente pede e o plano
    limita) — é a **procedência** da resolução que produziu `caps`. Fosse mais um parâmetro,
    esquecê-lo carimbaria `0` num evento cuja configuração veio do banco, e o relatório passaria
    a mentir em silêncio: exatamente o defeito que este campo existe para eliminar.

    `set_plan` é a série já resolvida por `resolve_set` (T-136) e **manda na duração**: no modo
    contado ela é o teto do plano, e o `duration_s` solto continuaria sendo a janela de 30 s.
    Ausente (chamada de teste, `evalctl`, qualquer caminho sem admissão), vale o `duration_s` de
    sempre e a série é livre — que é toda sessão anterior a esta task.
    """
    serie = set_plan if set_plan is not None else SetPlan(duration_s=duration_s)
    duration_s = serie.duration_s
    agora = now if now is not None else int(time.time())
    session_id = str(uuid.uuid4())
    token = issue_token(session_id, ttl_s=ttl_s, now=agora)
    expires_at = agora + ttl_s

    cliente = redis_client if redis_client is not None else bus().client

    # A vaga é tomada ANTES de a sessão existir. Registrar primeiro e pedir vaga depois
    # deixaria uma janela em que a sessão está no Redis, o token vale, e o WS abriria para
    # uma sessão que nunca foi admitida.
    if request.requested_mode is Mode.EDGE:
        modo = Mode.EDGE
    elif caps is not None and not caps.allow_cloud:
        modo = None
    else:
        if slots is not None:
            semaforo = slots
        elif caps is not None:
            semaforo = CloudSlots(cliente, limit=caps.cloud_slots, grace_ms=caps.cloud_grace_ms)
        else:
            semaforo = CloudSlots(cliente)
        # O prazo da vaga cobre a SÉRIE, não o ticket. Até a T-136 os dois davam no mesmo (30 s
        # de sessão dentro de 45 s de TTL), e a vaga expirava depois do fim por construção. Com o
        # modo contado a sessão pode durar 3 min: mantido o prazo do ticket, o semáforo devolveria
        # a vaga aos 60 s com a pessoa ainda treinando, e uma 4ª sessão cloud entraria — três
        # `pose-worker` viram quatro, e o orçamento da VPS que a SPEC-009 protege vira ficção.
        # O `max` é o que mantém o modo livre com o número de antes.
        prazo_da_vaga_s = max(ttl_s, duration_s)
        modo = (
            Mode.CLOUD
            if semaforo.acquire(session_id, ttl_ms=prazo_da_vaga_s * 1000, now_ms=agora * 1000)
            else None
        )

    ticket = SessionTicket(
        session_id=session_id,
        token=token,
        ws_url=_ws_url(session_id, token),
        mode=modo.value if modo else DENIED_CLOUD,
        exercise=request.exercise,
        duration_s=duration_s,
        expires_at=expires_at,
        set_plan=serie,
    )
    if modo is None:
        # Sessão negada não nasce: sem registro, sem evento, sem slot ocupado.
        return ticket

    cliente.hset(
        session_key(session_id),
        mapping={
            "exercise": request.exercise,
            "mode": modo.value,
            "state": "created",
            "duration_s": duration_s,
            "created_at": agora,
        },
    )
    cliente.expire(session_key(session_id), ttl_s)

    barramento = event_bus if event_bus is not None else bus()
    ts_ms = agora * 1000
    abertura = make_envelope(
        SessionStarted(
            exercise=request.exercise,
            mode=modo,
            duration_s=duration_s,
            # A preferência do cliente já veio normalizada pelo teto do CÓDIGO (`parse`); aqui
            # ela passa pelo teto do PLANO, quando há um. Os dois clamps não são redundância: o
            # primeiro protege contra lixo no corpo da requisição, o segundo é capacidade.
            countdown_s=request.countdown_s if countdown_s is None else countdown_s,
            # A vista atravessa a admissão sem que a API opine: ela é escolha de quem treina e
            # significado do exercício, e a API não sabe — nem deve saber — que a flexão tem
            # duas geometrias e o polichinelo não.
            view=request.view,
            # Carimbo da SPEC-018 (P1): a versão que valia no instante da admissão viaja com a
            # sessão. `0` quando não houve resolução de configuração — chamada de teste sem
            # `caps`, ou banco/cache fora (P2, `from_db=False`). "Não sei" dito como número.
            config_version=getattr(caps, "config_version", 0),
            # A série resolvida (T-136). Estes quatro campos são o que faz o critério 4 valer:
            # o worker encerra a série pela meta que ESTÁ AQUI, e nada do corpo da requisição
            # chega até ele sem passar por `resolve_set`.
            set_mode=serie.set_mode,
            target_reps=serie.target_reps,
            set_index=serie.set_index,
            set_total=serie.set_total,
        ),
        session_id=session_id,
        ts=ts_ms,
        seq=0,
        source=Source.SYSTEM,
    )
    barramento.publish(abertura, stream=Stream.POSE_FRAMES)
    # O MESMO evento também na saída da análise, para o report-builder (SPEC-010). Sem isto
    # `events.analysis` não diria qual exercício a sessão foi — e o relatório teria de
    # perguntar ao Redis, quebrando a propriedade que a spec exige: relatório derivável 100%
    # por replay dos eventos. O contrato prevê este caso (ver `STREAM_FOR_TYPE`): a rota
    # padrão é uma, publicar para outra audiência é permitido.
    barramento.publish(abertura, stream=Stream.EVENTS_ANALYSIS)
    if request.probe:
        # O resultado do probe interessa a relatório e dataset; a FSM ignora.
        barramento.publish(
            make_envelope(
                SessionCapability(
                    mode=modo,
                    # `probe_fps` é o nome do campo no contrato (`session.capability`); o
                    # cliente manda o payload do evento inteiro. `fps` fica aceito porque a
                    # T-011 nasceu com esse nome e há ticket antigo no formato.
                    probe_fps=float(
                        request.probe.get("probe_fps") or request.probe.get("fps") or 0.0
                    ),
                    webgl=bool(request.probe.get("webgl", False)),
                    ua=str(request.probe.get("ua") or ""),
                    # Enquadramento (SPEC-027 §Eventos): vem do mesmo payload do probe, e é o
                    # que permite ao dataset distinguir "filmado por outra pessoa, deitado" de
                    # "celular apoiado, em pé". Ausente vira vazio — o `from_data` do contrato
                    # já garante isso, e repetir aqui é só não depender da ordem de quem lê.
                    facing=str(request.probe.get("facing") or ""),
                    orientation=str(request.probe.get("orientation") or ""),
                ),
                session_id=session_id,
                ts=ts_ms,
                seq=1,
                source=Source.SYSTEM,
            ),
            stream=Stream.POSE_FRAMES,
        )

    return ticket
