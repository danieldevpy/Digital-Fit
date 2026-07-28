"""Barramento de eventos sobre Redis Streams (SPEC-002).

Uma casca fina: publica envelopes com `MAXLEN ~`, lê por consumer group e dá ack. Nenhuma
regra de negócio — quem decide o que fazer com o evento é o worker.

`EventBus` é protocolo para que worker e gateway sejam testáveis com um barramento em memória,
sem Redis no loop de teste.
"""

from __future__ import annotations

import logging
import time
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

    def consume_pending(
        self, stream: Stream, *, group: str, consumer: str, count: int = 100
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

    def consume_pending(
        self, stream: Stream, *, group: str, consumer: str, count: int = 100
    ) -> list[tuple[str, Envelope]]:
        """O que já foi entregue a este consumidor e ainda não teve ack (o PEL do Redis).

        É o que torna verdadeiro o critério 2 da SPEC-010: o processo morre no meio, e ao
        reiniciar os eventos ainda não confirmados voltam. Só funciona com **nome de
        consumidor estável** — o PEL é indexado por nome, então um nome com o PID dentro
        deixaria as pendências órfãs a cada restart.
        """
        resposta = self._client.xreadgroup(group, consumer, {stream.value: "0"}, count=count)
        eventos: list[tuple[str, Envelope]] = []
        for _, mensagens in resposta or []:
            for id_bruto, campos in mensagens:
                id_mensagem = id_bruto.decode() if isinstance(id_bruto, bytes) else str(id_bruto)
                try:
                    eventos.append((id_mensagem, from_stream_fields(campos)))
                except EventValidationError:
                    logger.warning("pendencia fora do contrato descartada: %s", id_mensagem)
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
        #: Entregue e ainda sem ack — o PEL do Redis, em lista. Sem isto o dublê não
        #: conseguiria exercitar a recuperação após crash, que é critério de aceite da
        #: SPEC-010: todo teste de reinício passaria por não haver o que reentregar.
        self._entregues: dict[Stream, list[tuple[str, Envelope]]] = {}
        self._proximo_id = 0

    def published_in(self, stream: Stream) -> list[Envelope]:
        """Só o que foi publicado neste stream."""
        return [envelope for destino, envelope in self.routed if destino is stream]

    def ensure_group(self, stream: Stream, group: str) -> None:
        self.groups.add((stream.value, group))

    def feed(self, stream: Stream, *envelopes: Envelope, arrived_ms: int | None = None) -> None:
        """Coloca eventos para serem consumidos.

        O ID imita o do Redis (`<ms-do-servidor>-<n>`) porque ele **é dado**: o pose-worker
        mede a espera na fila por ele (SPEC-005). Com um contador começando em 1, todo frame
        pareceria ter chegado em 1970 e o worker descartaria tudo — o dublê precisa ser fiel
        nesse ponto, senão esconde exatamente o comportamento que se quer testar.
        """
        base = arrived_ms if arrived_ms is not None else int(time.time() * 1000)
        for envelope in envelopes:
            self._proximo_id += 1
            self._pendentes.setdefault(stream, []).append((f"{base}-{self._proximo_id}", envelope))

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
        self._entregues.setdefault(stream, []).extend(lote)
        return lote

    def consume_pending(
        self, stream: Stream, *, group: str, consumer: str, count: int = 100
    ) -> list[tuple[str, Envelope]]:
        del group, consumer
        return list(self._entregues.get(stream, []))[:count]

    def ack(self, stream: Stream, group: str, message_id: str) -> None:
        del group
        self.acked.append(message_id)
        entregues = self._entregues.get(stream)
        if entregues is not None:
            self._entregues[stream] = [item for item in entregues if item[0] != message_id]

    def published_of(self, tipo) -> list[Envelope]:
        """Envelopes publicados de um tipo — atalho para asserções de teste."""
        return [envelope for envelope in self.published if envelope.type is tipo]
