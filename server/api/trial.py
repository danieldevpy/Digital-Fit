"""Trial anônimo: 3 sessões por dia por aparelho (SPEC-011, critério 1).

É **funil, não segurança** — a própria spec diz isso. Quem quiser burlar limpa o
`localStorage` e recomeça, e tudo bem: o objetivo é dar ao visitante prova do produto e
pedir a conta quando ele voltar, não trancar a porta. Tratar isto como controle de acesso
levaria a fingerprinting invasivo para proteger três sessões grátis.

O contador vive no Redis (`trial:{device}:{dia}` com TTL), como a spec manda, e não no
Postgres: é um número que expira sozinho, escrito no caminho quente da admissão.

**Desvio consciente da nota técnica da spec.** Ela sugere "cookie httpOnly + fingerprint
leve"; aqui o aparelho se identifica por um `X-Device-Id` que o cliente guarda em
`localStorage`. Motivo: cliente e API estão em origens diferentes (Vite em :5173, API em
:8000, e em produção domínios distintos), e cookie cross-site exige `SameSite=None; Secure`
— o que em desenvolvimento sobre http o navegador simplesmente descarta. O cookie httpOnly
seria mais difícil de apagar por engano, mas não mais difícil de burlar; e como a spec já
aceita que é burlável, a propriedade que ele acrescentaria não é a que importa.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime

__all__ = [
    "DEVICE_HEADER",
    "TRIAL_LIMIT",
    "TRIAL_MESSAGE",
    "TrialStatus",
    "consume",
    "device_id_from",
    "quota_key",
    "status_for",
]

#: Sessões por dia por aparelho, sem conta (SPEC-011, Fase Inicial).
TRIAL_LIMIT = 3

DEVICE_HEADER = "X-Device-Id"

#: Mensagem da recusa. Diz o que fazer, não só o que aconteceu: a 4ª tentativa do dia é
#: exatamente o momento em que a conta faz sentido para quem está do outro lado.
TRIAL_MESSAGE = (
    "Você já fez suas 3 sessões grátis de hoje. "
    "Crie uma conta para continuar treinando — é de graça e leva 30 segundos."
)

#: O contador morre sozinho. 48 h e não 24 h porque a chave já é do dia: a folga só garante
#: que nenhum contador do dia corrente evapore por diferença de relógio.
_TTL_S = 48 * 3600

#: Aceita o que um cliente honesto manda (UUID) e nada mais. Um id livre viraria chave de
#: Redis arbitrária vinda do navegador.
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@dataclass(frozen=True, slots=True)
class TrialStatus:
    """Quanto do trial deste aparelho já foi usado hoje."""

    used: int
    limit: int = TRIAL_LIMIT

    @property
    def allowed(self) -> bool:
        return self.used < self.limit

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def to_dict(self) -> dict[str, object]:
        return {"used": self.used, "limit": self.limit, "remaining": self.remaining}


def device_id_from(headers) -> str:
    """Id do aparelho a partir dos cabeçalhos, gerando um quando não vem nenhum.

    Gerar é o que faz o trial funcionar na primeira visita — e a resposta devolve o id para o
    cliente guardar. Um cliente que nunca guarda ganha um id novo a cada sessão e nunca
    esbarra no limite: é o preço de não fazer fingerprinting, e a spec aceita esse preço.
    """
    bruto = (headers.get(DEVICE_HEADER) or "").strip()
    return bruto if _DEVICE_RE.match(bruto) else uuid.uuid4().hex


def _dia(now: datetime | None = None) -> str:
    """Dia do contador, em UTC.

    UTC e não o fuso do usuário: o servidor não sabe onde a pessoa está, e um dia por
    `Accept-Language` seria adivinhação. Consequência real e assumida — no Brasil o trial
    reseta às 21 h locais, não à meia-noite.
    """
    return (now or datetime.now(UTC)).strftime("%Y-%m-%d")


def quota_key(device_id: str, *, now: datetime | None = None) -> str:
    return f"trial:{device_id}:{_dia(now)}"


def status_for(
    client, device_id: str, *, now: datetime | None = None, limit: int = TRIAL_LIMIT
) -> TrialStatus:
    """Lê o contador sem alterá-lo.

    `limit` é parâmetro desde a SPEC-018/T-073: o número vem do plano `anon`, resolvido pela
    view. A constante continua sendo o default porque ela é o piso do código (P2) — este módulo
    não consulta banco, e não deve passar a consultar.
    """
    bruto = client.get(quota_key(device_id, now=now))
    return TrialStatus(used=int(bruto) if bruto else 0, limit=limit)


def consume(
    client, device_id: str, *, now: datetime | None = None, limit: int = TRIAL_LIMIT
) -> TrialStatus:
    """Marca mais uma sessão usada. Chamado **depois** de a sessão nascer de verdade.

    A ordem importa: contar antes queimaria uma sessão do visitante toda vez que a admissão
    falhasse (Redis instável, cloud sem vaga) — e ele perderia um terço do trial sem nunca
    ter treinado. A janela entre checar e contar permite uma 4ª sessão em duas abas ao mesmo
    tempo; para um funil, isso é ruído, não furo.
    """
    chave = quota_key(device_id, now=now)
    usadas = int(client.incr(chave))
    if usadas == 1:
        client.expire(chave, _TTL_S)
    return TrialStatus(used=usadas, limit=limit)
