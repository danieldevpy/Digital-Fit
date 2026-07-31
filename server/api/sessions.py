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
from dataclasses import dataclass
from typing import Any

from django.conf import settings

from api.tokens import DEFAULT_TTL_S, issue_token
from workers.analysis_worker.exercises import EXERCISES
from workers.shared.bus import RedisBus
from workers.shared.events import (
    DEFAULT_COUNTDOWN_S,
    Mode,
    SessionCapability,
    SessionStarted,
    Source,
    Stream,
    clamp_countdown_s,
    make_envelope,
)
from workers.shared.slots import CloudSlots

__all__ = [
    "DEFAULT_DURATION_S",
    "DENIED_CLOUD",
    "SessionRequest",
    "SessionTicket",
    "create_session",
    "session_key",
]

#: Sessão de 30 s é a unidade de carga do produto (SPEC-009 / ADR-006).
DEFAULT_DURATION_S = 30

#: Resposta quando o cliente pede cloud e não há como atender.
DENIED_CLOUD = "denied_cloud"

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
        )


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "token": self.token,
            "ws_url": self.ws_url,
            "mode": self.mode,
            "exercise": self.exercise,
            "duration_s": self.duration_s,
            "expires_at": self.expires_at,
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
    """
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
        modo = (
            Mode.CLOUD
            if semaforo.acquire(session_id, ttl_ms=ttl_s * 1000, now_ms=agora * 1000)
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
            # Carimbo da SPEC-018 (P1): a versão que valia no instante da admissão viaja com a
            # sessão. `0` quando não houve resolução de configuração — chamada de teste sem
            # `caps`, ou banco/cache fora (P2, `from_db=False`). "Não sei" dito como número.
            config_version=getattr(caps, "config_version", 0),
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
                ),
                session_id=session_id,
                ts=ts_ms,
                seq=1,
                source=Source.SYSTEM,
            ),
            stream=Stream.POSE_FRAMES,
        )

    return ticket
