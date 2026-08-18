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

from api import quota
from api.i18n import SOURCE_LOCALE, resolve_locale
from api.i18n import messages as i18n_messages
from api.models import DailyGoal, SessionClaim, User

__all__ = [
    "AuthThrottle",
    "adotar_sessoes_do_aparelho",
    "login",
    "me",
    "refresh",
    "register",
    "tokens_for",
]

logger = logging.getLogger("api")


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
    def parse(
        cls, data: Any, *, com_nome: bool = False, locale: str = SOURCE_LOCALE
    ) -> Credentials:
        """Levanta `ValueError` com o `detail` já no idioma de `locale` (SPEC-025, T-145).

        A checagem de forma do corpo ("corpo deve ser objeto JSON") fica **fora** do catálogo de
        propósito: é erro de quem manda a requisição errada, não de quem preenche o formulário —
        a mesma fronteira que a spec traça entre texto de cliente e mensagem de desenvolvedor.
        """
        if not isinstance(data, dict):
            raise ValueError("corpo deve ser objeto JSON")

        msgs = i18n_messages.load(locale)
        email = str(data.get("email") or "").strip().lower()
        if not email:
            raise ValueError(msgs.error("email_required"))
        try:
            validate_email(email)
        except DjangoValidationError:
            raise ValueError(msgs.error("email_invalid", email=repr(email))) from None

        senha = data.get("password")
        if not isinstance(senha, str) or not senha:
            raise ValueError(msgs.error("password_required"))

        nome = str(data.get("name") or "").strip()[:80] if com_nome else ""
        return cls(email=email, password=senha, name=nome)


def tokens_for(usuario: User) -> dict[str, str]:
    """Par access/refresh do usuário."""
    refresh_token = RefreshToken.for_user(usuario)
    return {"access": str(refresh_token.access_token), "refresh": str(refresh_token)}


def _sessao_aberta(usuario: User, status: int, **extra: Any) -> Response:
    return Response({"user": usuario.to_dict(), **tokens_for(usuario), **extra}, status=status)


def adotar_sessoes_do_aparelho(usuario: User, device_id: str) -> int:
    """Passa as sessões órfãs deste aparelho para a conta recém-criada (SPEC-019 §Anônimo).

    É o que torna literal a promessa do README — *"a conta serve para guardar o histórico"*. Como
    o fogo é **derivado** das claims (SPEC-019), adotar a claim adota a sequência junto: quem
    treinou quatro dias como visitante e cria conta no quinto não recomeça do zero. Sem isto, a
    dor de perder a sequência seria causada exatamente pela ação que o app pediu.

    As três fronteiras da spec, e as três estão nesta função:

    - **Só claims órfãs.** O filtro `user__isnull=True` é o que impede um aparelho já adotado por
      uma conta de ser reivindicado por outra: o segundo a se cadastrar no mesmo celular não leva
      nada. Sem ele, dois cadastros disputariam as mesmas sessões — e o último ganharia.
    - **Uma vez, por construção.** Depois de rodar não há mais claim órfã daquele aparelho, então
      repetir é idempotente sem precisar de flag nem de tabela de controle.
    - **Só no registro.** Não existe rota que chame isto depois; não é um botão "importar
      aparelho". Quem quiser essa função vai ter de escrevê-la, e aí revisar estas fronteiras.

    `update()` e não um laço com `save()`: é um `UPDATE` só, no índice de `device_id`, e não
    dispara `post_save` de `SessionClaim` — o que não custa nada porque não há signal nessa
    tabela. O cache de engajamento da conta também não precisa de limpeza: a conta nasceu nesta
    mesma requisição, e ninguém leu o engajamento dela antes desta linha.

    Limitação aceita e documentada na spec: aparelho compartilhado adota sessões de outra pessoa.
    É o mesmo furo — e a mesma aceitação — do trial por device-id (SPEC-011). Fechá-lo exigiria
    fingerprinting, que é o que este projeto decidiu não fazer.
    """
    if not device_id:
        return 0
    return SessionClaim.objects.filter(user__isnull=True, device_id=device_id).update(user=usuario)


@api_view(["POST"])
@throttle_classes([AuthThrottle])
def register(request: Request) -> Response:
    """`POST /api/auth/register` — cria a conta, adota o aparelho e já devolve os tokens.

    Já devolve logado de propósito: obrigar um `login` logo depois do cadastro é um passo a
    mais no funil que não protege nada.

    O `X-Device-Id` é o **mesmo cabeçalho** do trial, e é lido aqui sem gerar um novo: o cadastro
    não é o lugar de batizar aparelho nenhum. Ver `adotar_sessoes_do_aparelho`.
    """
    locale = resolve_locale(request)
    try:
        dados = Credentials.parse(request.data, com_nome=True, locale=locale)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    try:
        validate_password(dados.password)
    except DjangoValidationError as exc:
        # Mensagem do próprio `django.contrib.auth.password_validation`, não deste catálogo: o
        # projeto não ativa `django.utils.translation` (painel fica em `USE_I18N = False`,
        # SPEC-025 §Escopo), então este texto já não segue `locale` — fora do alcance desta task.
        return Response({"detail": " ".join(exc.messages)}, status=400)

    try:
        usuario = User.objects.create_user(
            email=dados.email, password=dados.password, name=dados.name
        )
    except IntegrityError:
        # Corrida entre dois cadastros do mesmo e-mail — o banco é quem decide, não um
        # `exists()` antes que sempre teria janela.
        return Response({"detail": i18n_messages.load(locale).error("email_taken")}, status=409)

    adotadas = adotar_sessoes_do_aparelho(usuario, quota.device_id_declarado(request.headers))
    # O número volta no corpo para que a tela possa confirmar a promessa que o CTA fez ("crie
    # uma conta para não perder seu fogo"). Zero é resposta legítima — quem cria conta antes de
    # treinar não perdeu nada —, e é por isso que o campo não some quando é zero.
    return _sessao_aberta(usuario, 201, adopted_sessions=adotadas)


@api_view(["POST"])
@throttle_classes([AuthThrottle])
def login(request: Request) -> Response:
    """`POST /api/auth/login` — troca e-mail e senha por access + refresh."""
    locale = resolve_locale(request)
    try:
        dados = Credentials.parse(request.data, locale=locale)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    # `authenticate` e não `check_password` direto: é ele que passa pelo `ModelBackend`, que
    # recusa conta inativa e faz o trabalho de tempo constante para e-mail inexistente.
    usuario = authenticate(request, username=dados.email, password=dados.password)
    if usuario is None:
        # Mensagem única para e-mail inexistente e senha errada (`invalid_credentials`). Duas
        # mensagens diferentes transformariam o login num verificador de "esta pessoa tem conta
        # aqui?".
        msgs = i18n_messages.load(locale)
        return Response({"detail": msgs.error("invalid_credentials")}, status=401)

    return _sessao_aberta(usuario, 200)


@api_view(["POST"])
@throttle_classes([AuthThrottle])
def refresh(request: Request) -> Response:
    """`POST /api/auth/refresh` — access novo a partir do refresh.

    Sem rotação (`ROTATE_REFRESH_TOKENS=False`): o refresh continua valendo, e o cliente só
    troca o access. Isso é o que deixa a renovação ser um detalhe invisível durante o treino.
    """
    locale = resolve_locale(request)
    msgs = i18n_messages.load(locale)
    bruto = request.data.get("refresh") if isinstance(request.data, dict) else None
    if not isinstance(bruto, str) or not bruto:
        return Response({"detail": msgs.error("refresh_required")}, status=400)

    try:
        token = RefreshToken(bruto)
    except TokenError:
        # Expirado, adulterado ou de outra chave de assinatura: para o cliente é tudo a mesma
        # coisa — é hora de pedir login de novo.
        return Response({"detail": msgs.error("refresh_invalid")}, status=401)

    return Response({"access": str(token.access_token)})


@api_view(["GET", "PATCH"])
def me(request: Request) -> Response:
    """`GET /api/me` — quem está logado. `PATCH` edita o perfil. 401 quando não há ninguém.

    O `PATCH` nasce com **um** campo, `daily_goal` (SPEC-019): a meta é escolha do usuário e
    precisa de uma rota para mudar. Mesma URL do `GET` porque é o mesmo recurso — abrir um
    `/api/me/goal` daria a cada campo do perfil um endereço próprio, e o perfil ainda vai ganhar
    peso e altura (SPEC-017) e objetivo (SPEC-022).

    Só o que está na lista é aceito. Um `PATCH` genérico sobre o modelo deixaria `is_admin` e
    `plan` a um campo de distância de serem editáveis pelo dono da conta.
    """
    usuario = request.user
    if usuario is None or not usuario.is_authenticated:
        locale = resolve_locale(request)
        return Response({"detail": i18n_messages.load(locale).error("auth_required")}, status=401)

    if request.method == "PATCH":
        try:
            _atualizar_perfil(usuario, request.data)
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=400)

    return Response(usuario.to_dict())


def _atualizar_perfil(usuario: User, dados: Any) -> None:
    """Aplica os campos editáveis do perfil. Levanta `ValueError` no que não serve."""
    if not isinstance(dados, dict):
        raise ValueError("corpo deve ser objeto JSON")

    campos: list[str] = []

    if "daily_goal" in dados:
        meta = dados.get("daily_goal")
        if meta not in DailyGoal.values:
            aceitos = ", ".join(DailyGoal.values)
            raise ValueError(f"meta invalida: {meta!r}. Use um de: {aceitos}.")
        usuario.daily_goal = meta
        campos.append("daily_goal")

    if not campos:
        # Corpo sem nenhum campo conhecido é engano de quem chama — provavelmente um nome
        # errado. Responder 200 faria a tela mostrar "salvo" sobre uma gravação que não houve.
        raise ValueError("nenhum campo editavel no corpo")

    # `update_fields` para não reescrever a linha inteira: o `post_save` que invalida o cache de
    # engajamento dispara igual, e uma escrita menor não pisa em campo que outra requisição
    # tenha mudado no meio.
    usuario.save(update_fields=campos)
