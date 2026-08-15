"""Quota diária de sessões (SPEC-016 Fase Inicial + SPEC-011 critério 1).

Este módulo é **uma regra só**: um contador por dia, com limite, que expira sozinho. O que
muda de um solicitante para outro é a **identidade do contado**, nunca a regra — é o que a
SPEC-018 §A diz com todas as letras ao transformar o anônimo em plano: *"o que continua
diferente é a chave do contador (`trial:{device}:{dia}` para anônimo, `df:quota:{user}:{dia}`
para logado) — a identidade do contado muda, a regra não"*.

Até a T-063 este arquivo se chamava `trial.py`, porque o trial anônimo era o único limite que
existia. O nome deixou de ser verdade no instante em que a conta Free ganhou quota: um módulo
chamado "trial" contando as sessões de quem tem conta seria o convite a escrever o segundo
contador — e dois contadores da mesma regra divergem, sempre, no dia em que só um dos dois for
corrigido.

**O limite não mora aqui.** Ele vem do `Plan` (`capabilities_for().daily_sessions`, SPEC-018),
resolvido pela view. As constantes deste arquivo são o **piso do código** (P2): o que vale
quando banco e cache não respondem. Por isso elas são o número real do produto, e não zero —
um piso que abrisse a quota transformaria um soluço de Postgres em sessões ilimitadas de
graça, em silêncio.

**Funil, não segurança** (continua valendo, e é a razão de o anônimo ser por aparelho). Quem
quiser burlar o trial limpa o `localStorage` e recomeça. O objetivo é dar prova do produto ao
visitante e pedir a conta quando ele voltar, não trancar a porta — tratar isto como controle
de acesso levaria a fingerprinting invasivo para proteger três sessões grátis. A quota da
**conta** é outra história: ela é por `user_id`, e trocar de navegador não a reinicia.

**Desvio consciente da nota técnica da SPEC-011.** Ela sugere "cookie httpOnly + fingerprint
leve"; aqui o aparelho se identifica por um `X-Device-Id` que o cliente guarda em
`localStorage`. Motivo: cliente e API estão em origens diferentes (Vite em :5173, API em :8000,
e em produção domínios distintos), e cookie cross-site exige `SameSite=None; Secure` — o que em
desenvolvimento sobre http o navegador simplesmente descarta. O cookie httpOnly seria mais
difícil de apagar por engano, mas não mais difícil de burlar; e como a spec já aceita que é
burlável, a propriedade que ele acrescentaria não é a que importa.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

__all__ = [
    "DEVICE_HEADER",
    "FREE_LIMIT",
    "FREE_MESSAGE",
    "TRIAL_LIMIT",
    "TRIAL_MESSAGE",
    "QuotaStatus",
    "account_key",
    "consume",
    "device_id_declarado",
    "device_id_from",
    "device_key",
    "quota_key",
    "resets_at",
    "status_for",
]

#: Sessões por dia por aparelho, sem conta (SPEC-011, Fase Inicial).
TRIAL_LIMIT = 3

#: Sessões por dia na conta Free (SPEC-016, "proposta inicial: 10/dia").
FREE_LIMIT = 10

DEVICE_HEADER = "X-Device-Id"

#: Mensagem da recusa do visitante. Diz o que fazer, não só o que aconteceu: a 4ª tentativa do
#: dia é exatamente o momento em que a conta faz sentido para quem está do outro lado.
TRIAL_MESSAGE = (
    "Você já fez suas 3 sessões grátis de hoje. "
    "Crie uma conta para continuar treinando — é de graça e leva 30 segundos."
)

#: Mensagem da recusa de quem tem conta Free. Sem número e sem horário **de propósito**: o
#: número está no corpo da resposta (`used`/`limit`) e o horário é calculado (`resets_at`).
#: Escrevê-los aqui faria a frase mentir no dia em que o painel mudasse o limite — e "renova à
#: meia-noite" já mentiria hoje, porque o dia do contador é UTC (21 h no Brasil).
FREE_MESSAGE = (
    "Você treinou muito hoje 🎉 Suas sessões de hoje acabaram. "
    "Descanso faz parte — e a assinatura tira o limite quando você quiser mais."
)

#: O contador morre sozinho. 48 h e não 24 h porque a chave já é do dia: a folga só garante
#: que nenhum contador do dia corrente evapore por diferença de relógio.
_TTL_S = 48 * 3600

#: Aceita o que um cliente honesto manda (UUID) e nada mais. Um id livre viraria chave de
#: Redis arbitrária vinda do navegador.
_DEVICE_RE = re.compile(r"^[A-Za-z0-9_-]{8,64}$")


@dataclass(frozen=True, slots=True)
class QuotaStatus:
    """Quanto da quota de hoje já foi usado, e quando ela vira.

    `limit <= 0` é ilimitado — é como o `Plan` diz "sem limite" (`daily_sessions = 0`), e este
    é o único lugar do projeto que interpreta essa convenção.
    """

    used: int
    limit: int
    #: Quando o contador zera: próxima meia-noite UTC. Vai no corpo para o cliente escrever
    #: "renova em 5h12" sem precisar saber em que fuso o servidor conta o dia.
    resets_at: datetime

    @property
    def unlimited(self) -> bool:
        return self.limit <= 0

    @property
    def allowed(self) -> bool:
        return self.unlimited or self.used < self.limit

    @property
    def remaining(self) -> int:
        return 0 if self.unlimited else max(0, self.limit - self.used)

    def to_dict(self) -> dict[str, object]:
        return {
            "used": self.used,
            "limit": self.limit,
            "remaining": self.remaining,
            "unlimited": self.unlimited,
            "allowed": self.allowed,
            # `Z` e não `+00:00`: é o que o `Date` do navegador lê sem ambiguidade em todo lugar.
            "resets_at": self.resets_at.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }


def device_id_declarado(headers) -> str:
    """Id do aparelho como ele veio. Vazio quando não veio nada — **nunca gera**.

    A adoção de sessões no cadastro (SPEC-019 §Anônimo / T-087) precisa desta versão e não da
    de baixo: um id inventado aqui não pertence a aparelho nenhum, e a única coisa que ele
    poderia fazer é adotar zero claims com ar de que tentou. "Não veio id" é resposta, e é a
    resposta certa para quem cria conta antes de treinar.
    """
    bruto = (headers.get(DEVICE_HEADER) or "").strip()
    return bruto if _DEVICE_RE.match(bruto) else ""


def device_id_from(headers) -> str:
    """Id do aparelho a partir dos cabeçalhos, gerando um quando não vem nenhum.

    Gerar é o que faz o trial funcionar na primeira visita — e a resposta devolve o id para o
    cliente guardar. Um cliente que nunca guarda ganha um id novo a cada sessão e nunca
    esbarra no limite: é o preço de não fazer fingerprinting, e a spec aceita esse preço.
    """
    return device_id_declarado(headers) or uuid.uuid4().hex


def _dia(now: datetime | None = None) -> str:
    """Dia do contador, em UTC.

    UTC e não o fuso do usuário: o servidor não sabe onde a pessoa está, e um dia por
    `Accept-Language` seria adivinhação. Consequência real e assumida — no Brasil a quota
    reseta às 21 h locais, não à meia-noite.

    **Divergência intencional com a SPEC-019**, que vira o dia do fogo em America/Sao_Paulo: lá
    o dia é o que a pessoa chama de dia (perder o fogo por causa de fuso seria cruel); aqui é
    contabilidade de carga, e o servidor conta em UTC como conta tudo o mais.
    """
    return (now or datetime.now(UTC)).strftime("%Y-%m-%d")


def resets_at(now: datetime | None = None) -> datetime:
    """Próxima virada do contador: meia-noite UTC do dia seguinte."""
    agora = (now or datetime.now(UTC)).astimezone(UTC)
    return (agora + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)


def device_key(device_id: str, *, now: datetime | None = None) -> str:
    """Chave do visitante.

    Continua `trial:` e não `df:quota:` de propósito: renomeá-la zeraria o contador de todo
    mundo no deploy, dando um dia grátis a mais justamente a quem já tinha esgotado. E o
    prefixo antigo não confunde ninguém, porque o novo diz de quem é (`df:quota:{user}`).
    """
    return f"trial:{device_id}:{_dia(now)}"


def account_key(user_id: int | str, *, now: datetime | None = None) -> str:
    """Chave da conta, no formato que a SPEC-016 nomeia."""
    return f"df:quota:{user_id}:{_dia(now)}"


def quota_key(user, device_id: str, *, now: datetime | None = None) -> str:
    """A chave deste solicitante — a única linha do projeto onde a identidade importa.

    Uma função, e não dois chamadores escolhendo: quem esquecesse de escolher contaria a
    sessão de uma conta na chave do aparelho, e o limite de quem tem conta passaria a ser por
    navegador — furável trocando de aba, que é exatamente o que a conta existe para impedir.
    """
    return device_key(device_id, now=now) if user is None else account_key(user.pk, now=now)


def status_for(client, key: str, *, limit: int, now: datetime | None = None) -> QuotaStatus:
    """Lê o contador sem alterá-lo.

    `limit` é parâmetro desde a SPEC-018/T-073: o número vem do plano, resolvido pela view. As
    constantes deste módulo continuam sendo o piso do código (P2) — ele não consulta banco, e
    não deve passar a consultar.
    """
    bruto = client.get(key)
    return QuotaStatus(used=int(bruto) if bruto else 0, limit=limit, resets_at=resets_at(now))


def consume(client, key: str, *, limit: int, now: datetime | None = None) -> QuotaStatus:
    """Marca mais uma sessão usada. Chamado **depois** de a sessão nascer de verdade.

    A ordem importa: contar antes queimaria uma sessão toda vez que a admissão falhasse (Redis
    instável, cloud sem vaga) — e o visitante perderia um terço do trial sem nunca ter
    treinado. A janela entre checar e contar permite uma sessão a mais em duas abas ao mesmo
    tempo; para um funil, isso é ruído, não furo.
    """
    usadas = int(client.incr(key))
    if usadas == 1:
        client.expire(key, _TTL_S)
    return QuotaStatus(used=usadas, limit=limit, resets_at=resets_at(now))
