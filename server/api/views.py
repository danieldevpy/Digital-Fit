"""Views da API.

Saude, ciclo de sessao (SPEC-009), relatorio (SPEC-010) e o que a conta acrescenta a eles
(SPEC-011): trial anonimo, posse da sessao e historico. As rotas de auth ficam em `api/auth.py`.
"""

import logging
from typing import Any

from django.conf import settings
from django.db import connection
from rest_framework.decorators import api_view
from rest_framework.request import Request
from rest_framework.response import Response

from api import trial
from api.config import capabilities_for, config_etag, config_payload, exercises_for
from api.models import SessionClaim, SessionResult
from api.sessions import DENIED_CLOUD, SessionRequest, bus, create_session

logger = logging.getLogger("api")

#: Quantas sessoes o historico devolve. Sem paginacao na Fase Inicial: a spec pede "historico
#: do usuario", e quem tem 500 sessoes ainda nao existe. Paginar entra quando existir.
HISTORY_LIMIT = 50


def _usuario(request: Request):
    """Usuario autenticado, ou `None`. Anonimo e o caso normal — nao e erro."""
    usuario = request.user
    return usuario if usuario is not None and usuario.is_authenticated else None


@api_view(["GET"])
def healthz(_request: Request) -> Response:
    """Liveness: o processo esta de pe. Nao toca em dependencias externas."""
    return Response({"status": "ok", "service": "api"})


@api_view(["GET"])
def readyz(_request: Request) -> Response:
    """Readiness: Postgres e Redis respondem."""
    checks: dict[str, Any] = {}

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["postgres"] = "ok"
    except Exception as exc:  # readiness reporta o erro, nao trata
        checks["postgres"] = f"error: {exc.__class__.__name__}"

    try:
        import redis

        redis.Redis.from_url(settings.REDIS_URL, socket_connect_timeout=2).ping()
        checks["redis"] = "ok"
    except Exception as exc:
        checks["redis"] = f"error: {exc.__class__.__name__}"

    ready = all(value == "ok" for value in checks.values())
    return Response({"status": "ready" if ready else "degraded", "checks": checks})


@api_view(["GET"])
def config(request: Request) -> Response:
    """`GET /api/config` — catálogo e capacidades num payload só (SPEC-018).

    **A resposta é privada.** Ela varia por plano (capacidades, mensagem de quota) e, com a
    SPEC-020, varia no próprio conteúdo do catálogo — o assinante enxerga o que o Free não
    enxerga. Sem `Cache-Control: private`, um proxy no caminho serviria a resposta do assinante
    para o próximo Free que revalidasse, furando a trava de plano sem ninguém ver. Pelo mesmo
    motivo o ETag não é só a versão da configuração (ver `config_etag`).

    O cliente mantém os defaults dele em código para o primeiro paint e para o caso offline: a
    tela não espera por esta rota para desenhar, e o servidor vence quando chega.
    """
    usuario = _usuario(request)
    etag = config_etag(usuario)

    if request.headers.get("If-None-Match") == etag:
        resposta = Response(status=304)
    else:
        resposta = Response(config_payload(usuario))

    resposta["ETag"] = etag
    resposta["Cache-Control"] = "private, must-revalidate"
    # Sem isto um cache que respeitasse `private` ainda poderia servir a mesma entrada para
    # dois usuários da mesma origem.
    resposta["Vary"] = "Authorization"
    return resposta


@api_view(["GET", "POST"])
def sessions(request: Request) -> Response:
    """`POST /api/sessions` admite; `GET /api/sessions?mine` lista o historico (SPEC-011).

    Mesmo caminho por decisao: a spec nomeia `GET /sessions?mine`, e a colecao e a mesma —
    criar um `/api/sessions/mine` faria a mesma coisa ter dois enderecos.
    """
    if request.method == "GET":
        return _historico(request)
    return _admitir(request)


def _admitir(request: Request) -> Response:
    """Admite a sessao e devolve o ticket do WebSocket (SPEC-009 + trial da SPEC-011).

    A sessao de 30s e a unidade de carga: o token expira com o TTL (45s) e o timer autoritativo
    roda no analysis-worker, nao aqui.
    """
    try:
        pedido = SessionRequest.parse(request.data)
    except ValueError as exc:
        return Response({"detail": str(exc)}, status=400)

    usuario = _usuario(request)
    # Logado não carrega device: o aparelho só interessa a quem não tem conta.
    device_id = "" if usuario else trial.device_id_from(request.headers)

    # P1 da SPEC-018: quem lê configuração é a fronteira da API, uma vez por admissão, e o valor
    # resolvido viaja daqui para baixo. `capabilities_for` nunca levanta — banco ou cache fora
    # devolvem o piso do código, que é o comportamento anterior a esta spec (P2).
    caps = capabilities_for(usuario)

    # A UI nunca é a única trava (SPEC-018 §B / SPEC-016). Até aqui a admissão só perguntava se
    # o slug existia no registro de código — desligar um exercício no painel o tirava da tela e
    # deixava a porta aberta para quem chamasse a API direto. Mesmo resolvedor do
    # `GET /api/config`, de propósito: card na tela e sessão admitida vêm da mesma lista.
    permitidos = exercises_for(usuario)
    if pedido.exercise not in permitidos:
        return Response(
            {
                "detail": "este exercicio nao esta disponivel para voce agora",
                "code": "exercise_unavailable",
                "exercise": pedido.exercise,
            },
            # 403 e não 404: o exercício existe, o acesso é que não. E não 400, porque o corpo
            # da requisição está correto — mudou a permissão, não a sintaxe.
            status=403,
        )

    try:
        cliente = bus().client
    except Exception as exc:
        logger.exception("falha ao falar com o Redis")
        return Response({"detail": f"nao foi possivel criar a sessao: {exc}"}, status=503)

    # A quota do anônimo agora é o `daily_sessions` do plano `anon`, não mais uma constante em
    # `trial.py`. Conta logada segue sem limite porque o plano `free` nasce com 0 (= ilimitado),
    # que é o comportamento de hoje — quem liga o limite do Free é a T-063, mudando uma linha no
    # painel, e o contador por usuário (`df:quota:{user}:{dia}`) nasce lá com ele.
    status = None
    if usuario is None and not caps.unlimited_sessions:
        status = trial.status_for(cliente, device_id, limit=caps.daily_sessions)
        if not status.allowed:
            return Response(
                {
                    "detail": caps.quota_message or trial.TRIAL_MESSAGE,
                    "code": "trial_exhausted",
                    "device_id": device_id,
                    "trial": status.to_dict(),
                },
                # 429 e nao 403: nao e falta de permissao, e limite por tempo — e a mesma
                # requisicao passa amanha sem o cliente mudar nada.
                status=429,
            )

    try:
        ticket = create_session(
            pedido,
            redis_client=cliente,
            caps=caps,
            duration_s=caps.duration_s(),
            countdown_s=caps.countdown_s(pedido.countdown_s),
            ttl_s=caps.ticket_ttl_s,
        )
    except Exception as exc:  # Redis fora do ar: o cliente merece um erro claro
        logger.exception("falha ao criar sessao")
        return Response({"detail": f"nao foi possivel criar a sessao: {exc}"}, status=503)

    corpo = ticket.to_dict()
    # O `device_id` volta sempre: na primeira visita ele foi gerado aqui, e o cliente precisa
    # guardar o MESMO id para que a 4a sessao de hoje seja reconhecida como dele.
    corpo["device_id"] = device_id

    if ticket.mode == DENIED_CLOUD:
        # Sessao negada nao nasceu: nao tem dono e nao gasta trial.
        corpo["trial"] = status.to_dict() if status else None
        return Response(corpo, status=201)

    SessionClaim.objects.create(session_id=ticket.session_id, user=usuario, device_id=device_id)
    if usuario is None and not caps.unlimited_sessions:
        status = trial.consume(cliente, device_id, limit=caps.daily_sessions)
    if status is not None:
        corpo["trial"] = status.to_dict()
    return Response(corpo, status=201)


def _historico(request: Request) -> Response:
    """`GET /api/sessions?mine` — sessoes do usuario logado (SPEC-011, criterio 2)."""
    usuario = _usuario(request)
    if usuario is None:
        return Response({"detail": "autenticacao necessaria"}, status=401)
    if "mine" not in request.query_params:
        # Nao existe listagem global: sem o filtro, a pergunta seria "as sessoes de quem?".
        return Response({"detail": "use ?mine para listar suas sessoes"}, status=400)

    ids = list(
        SessionClaim.objects.filter(user=usuario).values_list("session_id", flat=True)[
            :HISTORY_LIMIT
        ]
    )
    resultados = SessionResult.objects.filter(session_id__in=ids)
    # A ordem vem do `SessionResult` (`-created_at`): o relatorio e o que a tela mostra, e a
    # sessao sem relatorio (abortada antes do primeiro frame) nao tem o que exibir.
    return Response({"count": len(resultados), "results": [r.to_report() for r in resultados]})


@api_view(["GET"])
def session_report(request: Request, session_id: str) -> Response:
    """`GET /api/sessions/{id}/report` — relatorio consolidado da sessao (SPEC-010).

    **404 nao quer dizer "nao existe", quer dizer "ainda nao"**: o relatorio nasce depois do
    `session.completed`, quando o report-builder consome o evento. O cliente que acabou de
    encerrar a sessao vai bater aqui antes disso e precisa distinguir os dois casos — por isso
    a resposta traz `pending: true` em vez de so um detalhe em texto.

    Sessao de outra pessoa tambem responde 404, e sem `pending` (SPEC-011, criterio 2): 403
    confirmaria que a sessao existe, e um `pending: true` poria o cliente a repetir para
    sempre um pedido que nunca vai ser atendido.
    """
    dono = SessionClaim.objects.filter(session_id=session_id).values_list("user_id", flat=True)
    dono_id = dono[0] if dono else None
    usuario = _usuario(request)
    if dono_id is not None and (usuario is None or usuario.pk != dono_id):
        return Response(
            {"detail": "relatorio nao encontrado", "pending": False, "session_id": session_id},
            status=404,
        )

    try:
        resultado = SessionResult.objects.get(session_id=session_id)
    except SessionResult.DoesNotExist:
        return Response(
            {"detail": "relatorio ainda nao disponivel", "pending": True, "session_id": session_id},
            status=404,
        )
    return Response(resultado.to_report())
