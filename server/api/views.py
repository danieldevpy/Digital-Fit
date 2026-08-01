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

from api import quota as quota_rule
from api.config import capabilities_for, config_etag, config_payload, exercises_for
from api.models import SessionClaim, SessionResult
from api.sessions import DENIED_CLOUD, SessionRequest, bus, create_session

logger = logging.getLogger("api")

#: Quantas sessoes o historico devolve. Sem paginacao na Fase Inicial: a spec pede "historico
#: do usuario", e quem tem 500 sessoes ainda nao existe. Paginar entra quando existir.
HISTORY_LIMIT = 50

#: Recusa por quota. Dois codigos e nao um porque a acao de quem le e outra: o visitante cria
#: conta (e a conta resolve hoje), quem ja tem conta espera o dia virar ou assina. Um codigo so
#: obrigaria o cliente a olhar se ha usuario para escolher a mensagem — e o servidor ja sabe.
TRIAL_EXHAUSTED = "trial_exhausted"
QUOTA_EXCEEDED = "quota_exceeded"


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


@api_view(["GET"])
def quota(request: Request) -> Response:
    """`GET /api/quota` — quanto ainda da para treinar hoje (SPEC-016, criterio 1).

    Existe por causa de uma palavra do criterio: o sheet de limite tem de aparecer *"antes
    mesmo de abrir a camera"*. A camera abre na pre-configuracao, antes de qualquer
    `POST /sessions` — entao um 429 na hora do play chegaria tarde: a pessoa ja teria dado
    permissao de camera, esperado o landmarker aquecer e se enquadrado para ouvir "nao".

    **Por que nao no `GET /api/config`.** Seria a rota obvia, e seria um bug: aquela resposta e
    cacheada por ETag de (versao, plano, `is_admin`) e nenhum dos tres muda quando o contador
    anda. O `used` congelaria no primeiro valor do dia e o cliente exibiria "restam 7" para
    sempre — um numero errado na tela, que e pior do que numero nenhum (SPEC-014).

    Esta rota nao e a trava e nao pretende ser: a trava e a admissao (criterio 4). Ela e o que
    permite a UI *refletir* o limite em vez de descobri-lo batendo nele.
    """
    usuario = _usuario(request)
    device_id = "" if usuario else quota_rule.device_id_from(request.headers)
    caps = capabilities_for(usuario)

    if caps.unlimited_sessions:
        # Sem limite nao ha contador para ler — e ler assim mesmo criaria a unica chamada de
        # Redis do assinante nesta rota, para receber de volta o que o plano ja dizia.
        status = _sem_limite(caps)
    else:
        try:
            status = quota_rule.status_for(
                bus().client, quota_rule.quota_key(usuario, device_id), limit=caps.daily_sessions
            )
        except Exception:
            # Redis fora: "nao sei" dito como erro, e nao como `used: 0`. Um zero inventado
            # aqui apagaria o sheet de quem ja esgotou, e o proximo passo dessa pessoa seria a
            # camera abrindo para nada. O cliente trata a falha ficando com o que ja tinha.
            logger.warning("nao foi possivel ler a quota", exc_info=True)
            return Response({"detail": "quota indisponivel agora"}, status=503)

    corpo = _snapshot_de_quota(caps, status, usuario)
    if usuario is None:
        # Mesma razao do ticket: na primeira visita quem gerou o id foi o servidor, e contar
        # amanha na mesma chave depende de o cliente guardar ESTE id.
        corpo["device_id"] = device_id
    # Contador do dia nao e cacheavel por ninguem: e o valor que muda a cada sessao.
    resposta = Response(corpo)
    resposta["Cache-Control"] = "no-store"
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
    device_id = "" if usuario else quota_rule.device_id_from(request.headers)

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

    # A quota vale para TODO plano desde a T-063 (SPEC-016): o que muda entre o visitante e a
    # conta Free e a chave do contador (`trial:{device}:{dia}` x `df:quota:{user}:{dia}`), nao
    # a regra. Ate aqui so o anonimo era contado, porque so ele tinha limite.
    #
    # Plano ilimitado (`daily_sessions = 0`, e o caso da assinatura) nao le nem escreve
    # contador nenhum: uma chave por dia por assinante seria lixo no Redis para responder uma
    # pergunta cuja resposta e sempre "pode".
    chave = quota_rule.quota_key(usuario, device_id)
    status = _sem_limite(caps)
    if not caps.unlimited_sessions:
        status = quota_rule.status_for(cliente, chave, limit=caps.daily_sessions)
        if not status.allowed:
            return Response(
                {
                    "detail": caps.quota_message or _mensagem_padrao_de_quota(usuario),
                    "code": QUOTA_EXCEEDED if usuario else TRIAL_EXHAUSTED,
                    "device_id": device_id,
                    "quota": _snapshot_de_quota(caps, status, usuario),
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
        # Sessao negada nao nasceu: nao tem dono e nao gasta quota.
        corpo["quota"] = _snapshot_de_quota(caps, status, usuario)
        return Response(corpo, status=201)

    SessionClaim.objects.create(session_id=ticket.session_id, user=usuario, device_id=device_id)
    if not caps.unlimited_sessions:
        status = quota_rule.consume(cliente, chave, limit=caps.daily_sessions)
    corpo["quota"] = _snapshot_de_quota(caps, status, usuario)
    return Response(corpo, status=201)


def _snapshot_de_quota(caps, status: quota_rule.QuotaStatus, usuario) -> dict[str, Any]:
    """A quota como o cliente a le — o MESMO corpo nos tres lugares que a devolvem.

    Tres, e um so formato: o ticket do 201, a recusa do 429 e o pre-voo do `GET /api/quota`.
    Montar cada um no seu lugar daria tres formatos parecidos, e o cliente precisaria de tres
    leitores para o mesmo numero. O `plan_name` e a `message` viajam junto dos contadores
    porque e disso que o sheet e feito: quem esta falando, quanto sobrou, e o que dizer.
    """
    recusa = caps.quota_message or _mensagem_padrao_de_quota(usuario)
    return {
        "plan": caps.plan_slug,
        "plan_name": caps.plan_name,
        # Vazio quando o plano e ilimitado: `message` e o texto da RECUSA, e quem nao tem
        # limite nao tem recusa. Mandar "suas sessoes de hoje acabaram" para um assinante seria
        # deixar uma frase falsa no corpo esperando um consumidor descuidado que a exiba.
        "message": "" if status.unlimited else recusa,
        **status.to_dict(),
    }


def _sem_limite(caps) -> quota_rule.QuotaStatus:
    """O status de quem nao tem limite, montado sem tocar no Redis.

    Existe para a resposta carregar `quota` SEMPRE. Um campo que some quando o plano e
    ilimitado obrigaria o cliente a tratar ausencia como permissao — e ausencia tambem e o que
    ele veria numa resposta velha, num proxy que corta corpo, ou num bug. `unlimited: true`
    dito em voz alta nao tem esse duplo sentido.
    """
    return quota_rule.QuotaStatus(
        used=0, limit=caps.daily_sessions, resets_at=quota_rule.resets_at()
    )


def _mensagem_padrao_de_quota(usuario) -> str:
    """Piso da mensagem de recusa, quando o plano nao traz a dele (P2 da SPEC-018)."""
    return quota_rule.TRIAL_MESSAGE if usuario is None else quota_rule.FREE_MESSAGE


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
