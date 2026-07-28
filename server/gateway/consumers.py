"""Consumer WebSocket da sessão (SPEC-002, Fase Inicial).

`wss://…/ws/session/{session_id}?token=…`

Entrada (cliente → servidor): envelope MessagePack. O gateway valida o envelope, confere que a
sessão do envelope é a da URL e publica no stream de entrada da análise. Nada de regra de
negócio aqui — o gateway é encanamento.

Saída (servidor → cliente): o relay (`relay.py`) lê `events.analysis` e faz `group_send` para
o grupo desta sessão; o consumer repassa ao WebSocket os tipos de `CLIENT_PUSH_TYPES`.

**Backpressure** (SPEC-002): os frames de entrada passam por uma fila de 3; cheia, o mais antigo
é descartado — frame novo vale mais que frame velho.
"""

from __future__ import annotations

import asyncio
import logging
from collections import deque

from api.tokens import InvalidToken, verify_token
from channels.generic.websocket import AsyncWebsocketConsumer

from workers.shared.events import (
    CLIENT_PUSH_TYPES,
    Envelope,
    EventType,
    EventValidationError,
    Stream,
    decode_envelope,
    encode_envelope,
)

__all__ = ["SessionConsumer", "session_group"]

logger = logging.getLogger("gateway")

#: Frames em espera antes de descartar o mais antigo (SPEC-002: buffer de 3).
INGEST_BUFFER = 3

#: Códigos de fechamento próprios (4000+ é a faixa livre do protocolo WebSocket).
CLOSE_BAD_TOKEN = 4401
CLOSE_BAD_SESSION = 4400


def session_group(session_id: str) -> str:
    """Grupo do channel layer de uma sessão — o relay publica nele."""
    return f"session.{session_id}"


class SessionConsumer(AsyncWebsocketConsumer):
    """Uma conexão = uma sessão."""

    async def connect(self) -> None:
        self.session_id = self.scope["url_route"]["kwargs"]["session_id"]
        self.dropped_frames = 0
        self._queue: deque[Envelope] = deque(maxlen=INGEST_BUFFER)
        self._publisher: asyncio.Task | None = None

        token = _token_from_scope(self.scope)
        try:
            await asyncio.to_thread(verify_token, self.session_id, token)
        except InvalidToken as exc:
            logger.info("WS recusado para %s: %s", self.session_id, exc)
            await self.close(code=CLOSE_BAD_TOKEN)
            return

        await self.channel_layer.group_add(session_group(self.session_id), self.channel_name)
        await self.accept()
        self._publisher = asyncio.create_task(self._publish_loop())
        logger.info("WS aberto para sessao %s", self.session_id)

    async def disconnect(self, code: int) -> None:
        if self._publisher is not None:
            self._publisher.cancel()
        await self.channel_layer.group_discard(session_group(self.session_id), self.channel_name)
        if self.dropped_frames:
            logger.info(
                "WS fechado (%s) sessao %s, %s frames descartados por backpressure",
                code,
                self.session_id,
                self.dropped_frames,
            )

    # ------------------------------------------------------------------ ingestão

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        """Envelope binário do cliente. Texto é rejeitado: o transporte é MessagePack."""
        if bytes_data is None:
            logger.warning("sessao %s enviou texto no WS; ignorado", self.session_id)
            return

        try:
            envelope = decode_envelope(bytes_data)
        except EventValidationError as exc:
            # Critério 3 da SPEC-002: loga e segue, sem derrubar a conexão.
            logger.warning("envelope invalido na sessao %s: %s", self.session_id, exc)
            return

        if envelope.type not in CLIENT_INGEST_TYPES:
            logger.warning(
                "cliente da sessao %s tentou publicar %s; recusado",
                self.session_id,
                envelope.type.value,
            )
            return

        if envelope.session_id != self.session_id:
            logger.warning(
                "envelope da sessao %s chegou pela conexao de %s; conexao encerrada",
                envelope.session_id,
                self.session_id,
            )
            await self.close(code=CLOSE_BAD_SESSION)
            return

        if len(self._queue) == self._queue.maxlen:
            self.dropped_frames += 1  # o `deque` já descarta o mais antigo
        self._queue.append(envelope)

    async def _publish_loop(self) -> None:
        """Publica o que está na fila. Tarefa separada para o `receive` nunca bloquear."""
        from gateway.relay import publish_envelope

        while True:
            if not self._queue:
                await asyncio.sleep(0.005)
                continue
            envelope = self._queue.popleft()
            try:
                # Todo evento de entrada vai para o stream de ENTRADA da análise, inclusive o
                # encerramento (ver `ANALYSIS_INPUT_TYPES` no contrato).
                await asyncio.to_thread(publish_envelope, envelope, Stream.POSE_FRAMES)
            except Exception:
                logger.exception("falha ao publicar evento da sessao %s", self.session_id)

    # --------------------------------------------------------------------- saída

    async def analysis_event(self, message: dict) -> None:
        """Chega do relay via `group_send`. Só os tipos que o cliente deve ver."""
        tipo = message.get("event_type")
        if tipo not in {membro.value for membro in CLIENT_PUSH_TYPES}:
            return
        await self.send(bytes_data=message["payload"])


#: O que o cliente **pode** publicar. Sem essa lista, um cliente conseguiria injetar
#: `rep.detected` ou `feedback.issued` direto no barramento — a contagem tem de nascer do
#: worker, nunca do navegador. (`frame.raw` → `frames.raw` entra na Fase 1, T-015.)
CLIENT_INGEST_TYPES: frozenset[EventType] = frozenset(
    {
        EventType.POSE_FRAME,
        EventType.SESSION_CAPABILITY,
        EventType.SESSION_COMPLETED,  # cliente encerrando a sessão (abort)
    }
)


def _token_from_scope(scope: dict) -> str:
    """Token do query string (`?token=…`)."""
    from urllib.parse import parse_qs

    bruto = scope.get("query_string") or b""
    consulta = parse_qs(bruto.decode() if isinstance(bruto, bytes) else str(bruto))
    valores = consulta.get("token") or []
    return valores[0] if valores else ""


def envelope_to_group_message(envelope: Envelope) -> dict:
    """Formato da mensagem que o relay manda ao grupo da sessão."""
    return {
        "type": "analysis.event",
        "event_type": envelope.type.value,
        "payload": encode_envelope(envelope),
    }
