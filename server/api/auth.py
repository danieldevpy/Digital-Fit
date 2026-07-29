"""Contas e JWT (SPEC-011, Fase Inicial).

`POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/refresh` e `GET /api/me`.

Validação à mão, com `dataclass` e `parse()`, no mesmo estilo do `SessionRequest` — o projeto
não usa serializers do DRF em lugar nenhum, e introduzir uma segunda forma de validar corpo
JSON só nesta rota deixaria duas convenções vivas.

**O que a autenticação NÃO toca**: o WebSocket. Ele é autenticado pelo token HMAC do ticket
(SPEC-009), que dura 45 s e não sabe nada de usuário. É por isso que o critério 3 da spec
("tokens expirados renovam sem derrubar sessão de treino em andamento") sai de graça: o JWT
só é exigido na admissão e no histórico, e um access vencido no meio dos 30 s não tem por
onde interferir.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any

from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.validators import validate_email
from django.db import IntegrityError
from rest_framework.decorators import api_view, throttle_classes
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.throttling import AnonRateThrottle
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken

from api.models import User

__all__ = ["AuthThrottle", "login", "me", "refresh", "register", "tokens_for"]

logger = logging.getLogger("api")

#: Mensagem única para e-mail inexistente e senha errada. Duas mensagens diferentes
#: transformariam o login num verificador de "esta pessoa tem conta aqui?".
_CREDENCIAIS_INVALIDAS = "E-mail ou senha incorretos."


class AuthThrottle(AnonRateThrottle):
    """Rate limit por IP nas rotas de auth (SPEC-011).

    `AnonRateThrottle` porque quem bate aqui ainda não tem token — a chave é o IP. É o que
    torna caro varrer senhas; não substitui senha boa, e não pretende.
    """

    scope = "auth"


@dataclass(frozen=True, slots=True)
class Credentials:
    """Corpo de `register` e `login` já validado."""

    email: str
    password: str
    name: str = ""

    @classmethod
    def parse(cls, data: Any, *, com_nome: bool = False) -> Credentials:
        if not isinstance(data, dict):
            raise ValueError("corpo deve ser objeto JSON")

        email = str(data.get("email") or "").strip().lower()
        if not email:
            raise ValueError("e-mail obrigatorio")
        try:
            validate_email(email)
        except DjangoValidationError:
            raise ValueError(f"e-mail invalido: {email!r}") from None

        senha = data.get("password")
        if not isinstance(senha, str) or not senha:
            raise ValueError("senha obrigatoria")

        nome = str(data.get("name") or "").strip()[:80] if com_nome else ""
        return cls(email=email, password=senha, name=nome)


def tokens_for(usuario: User) -> dict[str, str]:
    """Par access/refresh do usuário."""
    refresh_token = RefreshToken.for_user(usuario)
    return {"access": str(refresh_token.access_token), "refresh": str(refresh_token)}


def _sessao_aberta(usuario: User, status: int) -> Response:
    return Response({"user": usuario.to_dict(), **tokens_for(usuario)}, status=status)


@api_view(["POST"])
@throttle_classes([AuthThrottle])
def register(request: Request) -> Response:
    """`POST /api/auth/register` — cria a conta e já devolve os tokens.

    Já devolve logado de propósito: obrigar um `login` logo depois do cadastro é um passo a
    mais no funil que não protege nada.
    """
    try:
        dados = Credentials.parse(request.data, com_nome=True)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    try:
        validate_password(dados.password)
    except DjangoValidationError as exc:
        return Response({"detail": " ".join(exc.messages)}, status=400)

    try:
        usuario = User.objects.create_user(
            email=dados.email, password=dados.password, name=dados.name
        )
    except IntegrityError:
        # Corrida entre dois cadastros do mesmo e-mail — o banco é quem decide, não um
        # `exists()` antes que sempre teria janela.
        return Response(
            {"detail": "Já existe uma conta com este e-mail. Tente entrar."}, status=409
        )

    return _sessao_aberta(usuario, 201)


@api_view(["POST"])
@throttle_classes([AuthThrottle])
def login(request: Request) -> Response:
    """`POST /api/auth/login` — troca e-mail e senha por access + refresh."""
    try:
        dados = Credentials.parse(request.data)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    # `authenticate` e não `check_password` direto: é ele que passa pelo `ModelBackend`, que
    # recusa conta inativa e faz o trabalho de tempo constante para e-mail inexistente.
    usuario = authenticate(request, username=dados.email, password=dados.password)
    if usuario is None:
        return Response({"detail": _CREDENCIAIS_INVALIDAS}, status=401)

    return _sessao_aberta(usuario, 200)


@api_view(["POST"])
@throttle_classes([AuthThrottle])
def refresh(request: Request) -> Response:
    """`POST /api/auth/refresh` — access novo a partir do refresh.

    Sem rotação (`ROTATE_REFRESH_TOKENS=False`): o refresh continua valendo, e o cliente só
    troca o access. Isso é o que deixa a renovação ser um detalhe invisível durante o treino.
    """
    bruto = request.data.get("refresh") if isinstance(request.data, dict) else None
    if not isinstance(bruto, str) or not bruto:
        return Response({"detail": "refresh obrigatorio"}, status=400)

    try:
        token = RefreshToken(bruto)
    except TokenError:
        # Expirado, adulterado ou de outra chave de assinatura: para o cliente é tudo a mesma
        # coisa — é hora de pedir login de novo.
        return Response({"detail": "refresh invalido ou expirado"}, status=401)

    return Response({"access": str(token.access_token)})


@api_view(["GET"])
def me(request: Request) -> Response:
    """`GET /api/me` — quem está logado. 401 quando não há ninguém."""
    usuario = request.user
    if usuario is None or not usuario.is_authenticated:
        return Response({"detail": "autenticacao necessaria"}, status=401)
    return Response(usuario.to_dict())
