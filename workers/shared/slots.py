"""Semáforo de slots do modo cloud (SPEC-009, T-017).

O modo cloud custa CPU no servidor: cada sessão ocupa um `pose-worker` extraindo pose de
verdade. São 3 vagas simultâneas (SPEC-005/009) e o orçamento da VPS depende disso ser
respeitado — não é uma preferência, é o que impede o sistema de derreter.

## Por que ZSET e não INCR/DECR

A nota técnica da SPEC-009 sugeria `INCR` + verificação + `DECR` em Lua. Um contador atende ao
critério 1 (negar a 4ª sessão), mas **não** ao critério 2, que exige liberar o slot em TODOS os
finais — inclusive crash de worker. Quem crasha não decrementa: cada crash comeria uma vaga
para sempre, e depois de três o modo cloud estaria permanentemente esgotado, sem nada errado
aparecendo em log nenhum.

Aqui cada sessão é um membro de um ZSET com score = instante de expiração. Toda operação
começa varrendo os vencidos, então uma sessão cujo dono morreu libera a vaga sozinha quando o
prazo passa. É o mesmo raciocínio do TTL da chave de sessão, aplicado por membro em vez de por
chave.

Os scripts rodam em Lua porque varrer-conferir-inserir precisa ser **um** passo: entre o
`ZCARD` e o `ZADD` de dois processos concorrentes cabem duas admissões para a mesma vaga.
"""

from __future__ import annotations

import logging
import time

__all__ = ["CLOUD_SLOTS_KEY", "DEFAULT_CLOUD_SLOTS", "GRACE_MS", "CloudSlots"]

logger = logging.getLogger(__name__)

#: Chave do semáforo. `slots:` é prefixo de capacidade, não de dado de sessão.
CLOUD_SLOTS_KEY = "slots:cloud"

#: Vagas simultâneas do modo cloud (SPEC-009). Com 2 pose-workers de 1 vCPU, três sessões a
#: 10fps é o que a VPS aguenta sem roubar CPU do gateway.
DEFAULT_CLOUD_SLOTS = 3

#: Margem sobre o prazo da sessão antes de a vaga ser recolhida à força. Serve para não
#: recolher a vaga de uma sessão que ainda está fechando (o worker emite `session.completed`,
#: o relatório consome, e só então o slot deixa de importar).
GRACE_MS = 15_000

# Varre vencidos, respeita idempotência e insere se houver vaga. Um passo só.
_ACQUIRE = """
local chave = KEYS[1]
local sessao = ARGV[1]
local agora = tonumber(ARGV[2])
local expira_em = tonumber(ARGV[3])
local limite = tonumber(ARGV[4])

redis.call('ZREMRANGEBYSCORE', chave, '-inf', agora)

-- Repetir a admissão da MESMA sessão não pode consumir uma segunda vaga: um retry de rede
-- viraria vazamento silencioso.
if redis.call('ZSCORE', chave, sessao) then
  redis.call('ZADD', chave, expira_em, sessao)
  return 1
end

if redis.call('ZCARD', chave) >= limite then
  return 0
end

redis.call('ZADD', chave, expira_em, sessao)
-- TTL de segurança na chave inteira: se o processo todo sumir, a chave não fica órfã.
redis.call('PEXPIRE', chave, expira_em - agora + 60000)
return 1
"""

_ACTIVE = """
redis.call('ZREMRANGEBYSCORE', KEYS[1], '-inf', tonumber(ARGV[1]))
return redis.call('ZCARD', KEYS[1])
"""


def _agora_ms() -> int:
    return int(time.time() * 1000)


class CloudSlots:
    """Semáforo de sessões cloud sobre um cliente Redis."""

    __slots__ = ("_acquire", "_active", "_client", "_key", "_limit")

    def __init__(
        self,
        client,
        *,
        limit: int = DEFAULT_CLOUD_SLOTS,
        key: str = CLOUD_SLOTS_KEY,
    ) -> None:
        self._client = client
        self._limit = limit
        self._key = key
        self._acquire = client.register_script(_ACQUIRE)
        self._active = client.register_script(_ACTIVE)

    @property
    def limit(self) -> int:
        return self._limit

    def acquire(self, session_id: str, *, ttl_ms: int, now_ms: int | None = None) -> bool:
        """Tenta ocupar uma vaga. `False` = sem vaga (o cliente vê `denied_cloud`).

        Idempotente por `session_id`: chamar duas vezes para a mesma sessão não gasta duas
        vagas, só estende o prazo.
        """
        agora = now_ms if now_ms is not None else _agora_ms()
        concedido = bool(
            self._acquire(
                keys=[self._key],
                args=[session_id, agora, agora + ttl_ms + GRACE_MS, self._limit],
            )
        )
        if not concedido:
            logger.info("slot cloud negado para %s (limite %s)", session_id, self._limit)
        return concedido

    def release(self, session_id: str) -> bool:
        """Devolve a vaga. `True` se ela era desta sessão.

        Chamável para QUALQUER sessão, inclusive edge, que nunca ocupou vaga: remover um
        membro ausente é no-op. Isso é de propósito — quem encerra a sessão não precisa
        lembrar em que modo ela estava, e é justamente esse tipo de "lembrar" que vaza slot.
        """
        return bool(self._client.zrem(self._key, session_id))

    def active(self, *, now_ms: int | None = None) -> int:
        """Quantas vagas estão ocupadas agora (já descontando as vencidas)."""
        agora = now_ms if now_ms is not None else _agora_ms()
        return int(self._active(keys=[self._key], args=[agora]))

    def available(self, *, now_ms: int | None = None) -> int:
        return max(0, self._limit - self.active(now_ms=now_ms))
