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
    Mode,
    SessionCapability,
    SessionStarted,
    Source,
    Stream,
    make_envelope,
)

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

        return cls(exercise=exercise, requested_mode=requested_mode, probe=probe)


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
    now: int | None = None,
    redis_client=None,
    event_bus=None,
) -> SessionTicket:
    """Admite a sessão: registra em Redis, publica `session.started` e devolve o ticket.

    Fase 0 é **edge only**: pedido de cloud é recusado com `mode: "denied_cloud"` porque não
    existe `pose-worker` nem semáforo de slots ainda (T-016/T-017). O cliente trata isso como
    indisponibilidade momentânea, exatamente como a SPEC-009 previu.
    """
    agora = now if now is not None else int(time.time())
    session_id = str(uuid.uuid4())
    modo = Mode.EDGE if request.requested_mode is Mode.EDGE else None
    token = issue_token(session_id, ttl_s=ttl_s, now=agora)
    expires_at = agora + ttl_s

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

    cliente = redis_client if redis_client is not None else bus().client
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
    barramento.publish(
        make_envelope(
            SessionStarted(exercise=request.exercise, mode=modo, duration_s=duration_s),
            session_id=session_id,
            ts=ts_ms,
            seq=0,
            source=Source.SYSTEM,
        ),
        stream=Stream.POSE_FRAMES,
    )
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
