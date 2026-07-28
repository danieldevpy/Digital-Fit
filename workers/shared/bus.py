"""Barramento de eventos sobre Redis Streams (SPEC-002).

Uma casca fina: publica envelopes com `MAXLEN ~`, lê por consumer group e dá ack. Nenhuma
regra de negócio — quem decide o que fazer com o evento é o worker.

`EventBus` é protocolo para que worker e gateway sejam testáveis com um barramento em memória,
sem Redis no loop de teste.
"""

from __future__ import annotations

import logging
from typing import Protocol

from workers.shared.events import (
    CONSUMER_GROUPS,
    STREAM_MAXLEN,
    Envelope,
    EventValidationError,
    Stream,
    from_stream_fields,
    to_stream_fields,
)

__all__ = ["EventBus", "InMemoryBus", "RedisBus"]

logger = logging.getLogger(__name__)


class EventBus(Protocol):
    """O que um worker precisa de um barramento."""

    def ensure_group(self, stream: Stream, group: str) -> None: ...

    def publish(self, envelope: Envelope, *, stream: Stream | None = None) -> str: ...

    def consume(
        self, stream: Stream, *, group: str, consumer: str, block_ms: int = 1000, count: int = 50
    ) -> list[tuple[str, Envelope]]: ...

    def ack(self, stream: Stream, group: str, message_id: str) -> None: ...


class RedisBus:
    """Implementação real. Um cliente Redis por processo."""

    __slots__ = ("_client", "_maxlen")

    def __init__(self, client, *, maxlen: int = STREAM_MAXLEN) -> None:
        self._client = client
        self._maxlen = maxlen

    @property
    def client(self):
        """Cliente Redis cru — para quem precisa de chaves comuns (ex.: registro de sessao)."""
        return self._client

    @classmethod
    def from_url(cls, url: str, **kwargs) -> RedisBus:
        import redis

        return cls(redis.Redis.from_url(url), **kwargs)

    def ensure_group(self, stream: Stream, group: str) -> None:
        """Cria o consumer group (e o stream, se preciso). Idempotente."""
        import redis

        try:
            self._client.xgroup_create(stream.value, group, id="0", mkstream=True)
        except redis.ResponseError as exc:
            if "BUSYGROUP" not in str(exc):
                raise

    def ensure_declared_groups(self) -> None:
        """Cria todos os grupos que o contrato declara (`CONSUMER_GROUPS`)."""
        for stream, grupos in CONSUMER_GROUPS.items():
            for grupo in grupos:
                self.ensure_group(stream, grupo)

    def publish(self, envelope: Envelope, *, stream: Stream | None = None) -> str:
        destino = stream or envelope.stream
        id_mensagem = self._client.xadd(
            destino.value,
            to_stream_fields(envelope),
            maxlen=self._maxlen,
            approximate=True,
        )
        return id_mensagem.decode() if isinstance(id_mensagem, bytes) else str(id_mensagem)

    def consume(
        self, stream: Stream, *, group: str, consumer: str, block_ms: int = 1000, count: int = 50
    ) -> list[tuple[str, Envelope]]:
        """Lê o próximo lote. Envelope inválido é logado e descartado, não derruba o loop."""
        resposta = self._client.xreadgroup(
            group, consumer, {stream.value: ">"}, count=count, block=block_ms
        )
        eventos: list[tuple[str, Envelope]] = []
        for _, mensagens in resposta or []:
            for id_bruto, campos in mensagens:
                id_mensagem = id_bruto.decode() if isinstance(id_bruto, bytes) else str(id_bruto)
                try:
                    eventos.append((id_mensagem, from_stream_fields(campos)))
                except EventValidationError:
                    logger.warning("evento fora do contrato descartado: %s", id_mensagem)
                    self.ack(stream, group, id_mensagem)
        return eventos

    def ack(self, stream: Stream, group: str, message_id: str) -> None:
        self._client.xack(stream.value, group, message_id)

    def close(self) -> None:
        self._client.close()


class InMemoryBus:
    """Barramento de teste: mesma interface, listas Python no lugar do Redis."""

    def __init__(self) -> None:
        self.published: list[Envelope] = []
        #: `(stream efetivo, envelope)` de cada publicação. Existe porque o roteamento é
        #: comportamento testável: `frame.raw` tem de cair em `frames.raw`, e sem registrar o
        #: destino um erro de rota passaria por este dublê sem nenhum teste falhar.
        self.routed: list[tuple[Stream, Envelope]] = []
        self.acked: list[str] = []
        self.groups: set[tuple[str, str]] = set()
        self._pendentes: dict[Stream, list[tuple[str, Envelope]]] = {}
        self._proximo_id = 0

    def published_in(self, stream: Stream) -> list[Envelope]:
        """Só o que foi publicado neste stream."""
        return [envelope for destino, envelope in self.routed if destino is stream]

    def ensure_group(self, stream: Stream, group: str) -> None:
        self.groups.add((stream.value, group))

    def feed(self, stream: Stream, *envelopes: Envelope) -> None:
        """Coloca eventos para serem consumidos."""
        for envelope in envelopes:
            self._proximo_id += 1
            self._pendentes.setdefault(stream, []).append((f"{self._proximo_id}-0", envelope))

    def publish(self, envelope: Envelope, *, stream: Stream | None = None) -> str:
        # Mesmo default do RedisBus: sem destino explícito vale a rota do contrato.
        self.published.append(envelope)
        self.routed.append((stream or envelope.stream, envelope))
        self._proximo_id += 1
        return f"{self._proximo_id}-0"

    def consume(
        self, stream: Stream, *, group: str, consumer: str, block_ms: int = 1000, count: int = 50
    ) -> list[tuple[str, Envelope]]:
        del group, consumer, block_ms
        fila = self._pendentes.get(stream, [])
        lote, self._pendentes[stream] = fila[:count], fila[count:]
        return lote

    def ack(self, stream: Stream, group: str, message_id: str) -> None:
        del stream, group
        self.acked.append(message_id)

    def published_of(self, tipo) -> list[Envelope]:
        """Envelopes publicados de um tipo — atalho para asserções de teste."""
        return [envelope for envelope in self.published if envelope.type is tipo]
