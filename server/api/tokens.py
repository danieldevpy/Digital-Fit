"""Token de sessão assinado (HMAC) — autentica o WebSocket (SPEC-009).

A Fase 0 é anônima: não há usuário para autenticar, mas também não pode ser possível abrir um
WebSocket para uma sessão que não foi admitida pela API. O token resolve isso sem estado:
`{expira_em}.{assinatura}`, com a assinatura sobre `session_id|expira_em`.

- Expira junto com o TTL da sessão (45 s = 30 s + margem, SPEC-009).
- Assinatura com `compare_digest` — comparação em tempo constante.
- Sem segredo no cliente: o token é opaco para o navegador.

Emitido pela API (`POST /sessions`, T-011) e verificado pelo gateway (T-005).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import time

from django.conf import settings

__all__ = ["DEFAULT_TTL_S", "InvalidToken", "issue_token", "verify_token"]

#: TTL da sessão: 30 s de exercício + 15 s de margem (SPEC-009).
DEFAULT_TTL_S = 45

_SEPARATOR = "."
#: 16 bytes de HMAC-SHA256 truncado: 128 bits de segurança num token curto.
_DIGEST_SIZE = 16


class InvalidToken(Exception):
    """Token malformado, com assinatura errada ou expirado."""


def _secret() -> bytes:
    """Segredo de assinatura. Separado do `SECRET_KEY` quando configurado."""
    bruto = getattr(settings, "SESSION_TOKEN_SECRET", None) or settings.SECRET_KEY
    return bruto.encode() if isinstance(bruto, str) else bytes(bruto)


def _sign(session_id: str, expires_at: int) -> str:
    assinatura = hmac.new(
        _secret(), f"{session_id}|{expires_at}".encode(), hashlib.sha256
    ).digest()[:_DIGEST_SIZE]
    return base64.urlsafe_b64encode(assinatura).decode().rstrip("=")


def issue_token(session_id: str, *, ttl_s: int = DEFAULT_TTL_S, now: int | None = None) -> str:
    """Cria o token de uma sessão. `now` em epoch segundos (injetável para teste)."""
    if not session_id:
        raise ValueError("session_id vazio")
    expires_at = (now if now is not None else int(time.time())) + ttl_s
    return f"{expires_at}{_SEPARATOR}{_sign(session_id, expires_at)}"


def verify_token(session_id: str, token: str, *, now: int | None = None) -> int:
    """Valida o token e devolve o `expires_at`. Lança `InvalidToken` em qualquer problema."""
    if not token:
        raise InvalidToken("token ausente")

    expira_texto, _, assinatura = token.partition(_SEPARATOR)
    if not assinatura:
        raise InvalidToken("token malformado")
    try:
        expires_at = int(expira_texto)
    except ValueError:
        raise InvalidToken("validade invalida") from None

    if not hmac.compare_digest(assinatura, _sign(session_id, expires_at)):
        # Mensagem deliberadamente igual para assinatura errada e sessão trocada: não vale
        # contar ao cliente qual das duas coisas ele errou.
        raise InvalidToken("assinatura invalida")

    agora = now if now is not None else int(time.time())
    if agora >= expires_at:
        raise InvalidToken("token expirado")
    return expires_at
