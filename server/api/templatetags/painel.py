"""Os números do topo do painel (SPEC-018, T-130).

O dashboard de fábrica do Django é uma lista de links para as tabelas. Isso responde "onde
eu mudo X" e não responde nenhuma das perguntas com que se abre um painel de operação: o
produto rodou hoje? alguém entrou? o que está no ar? o que eu mudei ontem já está valendo?

Este módulo responde essas quatro, e **só** essas quatro. Não é analytics — relatório de
verdade é a SPEC-010, sai do Parquet e não de quatro `COUNT(*)` no Postgres de produção.

Duas regras de construção, herdadas do P2 da SPEC-018 ("nenhuma leitura de configuração pode
falhar uma sessão"), aqui na forma "nenhum número pode derrubar o painel":

1. **Consulta que falhar devolve `None`**, e o template simplesmente não desenha a faixa. Um
   painel sem os números continua servindo para tudo o que servia antes; um painel que
   responde 500 na home não serve para nada — inclusive para consertar o que quebrou.
2. **Nada de `count()` sem recorte.** As tabelas que crescem sem limite (`SessionResult`,
   `SessionClaim`) só são contadas dentro da janela do dia.
"""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from django import template
from django.db.models import Q, Sum
from django.utils import timezone

from api.exercise_health import JANELA_PADRAO_DIAS, LIMITE_ZERO, coletar
from api.models import Exercise, Plan, SessionResult, SiteConfig, User

logger = logging.getLogger(__name__)

register = template.Library()


@register.simple_tag
def painel_resumo() -> dict[str, Any] | None:
    """Devolve os números do topo, ou `None` se qualquer consulta falhar."""
    try:
        return _resumo()
    except Exception:  # banco fora, migration pendente, tabela nova ainda não aplicada
        logger.exception("painel: resumo indisponível")
        return None


def _resumo() -> dict[str, Any]:
    agora = timezone.now()
    # `TIME_ZONE = "UTC"` no settings, então "hoje" é o dia UTC — o mesmo corte que o
    # `date_hierarchy` das listas usa. Um fuso local aqui faria o cartão e a lista abaixo
    # dele discordarem em até três horas, todo dia, no fim da noite.
    inicio_do_dia = agora.replace(hour=0, minute=0, second=0, microsecond=0)

    sessoes_hoje = SessionResult.objects.filter(created_at__gte=inicio_do_dia)
    total_sessoes = sessoes_hoje.count()
    reps_hoje = sessoes_hoje.aggregate(total=Sum("rep_count"))["total"] or 0

    contas_ativas = User.objects.filter(is_active=True).count()
    novas_na_semana = User.objects.filter(date_joined__gte=agora - timedelta(days=7)).count()

    exercicios_no_ar = Exercise.objects.filter(enabled=True).count()
    exercicios_total = Exercise.objects.count()

    plano_default = Plan.objects.filter(is_default=True).first()
    config = SiteConfig.objects.filter(pk=1).first()

    return {
        "sessoes_hoje": total_sessoes,
        "reps_hoje": reps_hoje,
        "contas_ativas": contas_ativas,
        "novas_na_semana": novas_na_semana,
        "exercicios_no_ar": exercicios_no_ar,
        "exercicios_total": exercicios_total,
        "plano_default": plano_default,
        "config": config,
        "avisos": _avisos(plano_default, config),
    }


def _avisos(plano_default: Plan | None, config: SiteConfig | None) -> list[str]:
    """Configurações que não quebram nada agora e quebram alguma coisa depois.

    O critério para entrar nesta lista é estreito de propósito: só o que é **silencioso**. O
    produto continua de pé em todos os casos abaixo, e é justamente por isso que ninguém
    descobriria sozinho — o sintoma aparece dias depois, num número que não bate.
    """
    avisos: list[str] = []

    if plano_default is None:
        avisos.append(
            "Nenhum plano marcado como padrão: toda conta sem plano cai no piso do código, e "
            "o que estiver configurado aqui é ignorado."
        )
    if not Plan.objects.filter(slug="anon").exists():
        avisos.append(
            "Não existe plano `anon`: o visitante (funil de entrada) resolve pelo piso do "
            "código em vez de pelo painel."
        )
    if config is None:
        avisos.append(
            "Sem linha de configuração global: duração, countdown e capacidade cloud saem "
            "todos das constantes do código."
        )

    # `met` ou cadência em zero **desliga o card de calorias** do exercício (mostra "--"), sem
    # erro nenhum em lugar nenhum. É a descoberta que a T-128 pagou para aprender.
    sem_kcal = list(
        Exercise.objects.filter(enabled=True)
        .filter(Q(met=0) | Q(ref_cadence_rpm=0))
        .values_list("display_name", flat=True)[:5]
    )
    if sem_kcal:
        avisos.append(
            "Sem MET ou sem cadência de referência (o card de calorias mostra '--'): "
            + ", ".join(sem_kcal)
        )

    avisos.extend(_avisos_de_saude())
    return avisos


def _avisos_de_saude() -> list[str]:
    """Exercício no ar contando zero para gente de verdade (T-104 / SPEC-020).

    Entra na faixa pelo mesmo critério dos outros avisos: é **silencioso**. Nada quebra, nada
    responde erro — o exercício simplesmente devolve relatório vazio para quem treinou, e só
    aparece aqui ou numa reclamação.

    A regra é a do comando, e vem de lá para que os dois nunca discordem: a taxa é sobre as
    sessões `completed`, e sessão sem frame (`no_data`) fica de fora. Somar as duas foi o que
    fez o agachamento parecer quebrado por semanas (T-133) — e um painel que grita errado é
    pior que um painel calado, porque ensina o operador a ignorar a faixa.
    """
    acima = [
        exercicio
        for exercicio in coletar(JANELA_PADRAO_DIAS)
        if exercicio.enabled and exercicio.veredito == "atencao"
    ]
    if not acima:
        return []
    detalhes = ", ".join(
        f"{e.display_name} ({e.zeradas}/{e.completas})"
        for e in acima
        # `taxa_zero` não é None aqui: o veredito `atencao` exige sessões completas.
    )
    return [
        f"Exercício no ar com mais de {LIMITE_ZERO * 100:.0f}% das sessões completas contando "
        f"zero repetição, nos últimos {JANELA_PADRAO_DIAS} dias: {detalhes}. "
        "Detalhe por `manage.py exercise_health`."
    ]


#: Para que serve cada tela, na linguagem de quem abre o painel — "trocar a senha de alguém",
#: e não "gerenciar instâncias de User". As chaves são o `model_str` do menu do jazzmin
#: (`app_label.objectname`, minúsculo). Modelo sem legenda aqui aparece sem legenda nenhuma:
#: a lista do dashboard continua vindo do Django, então esquecer de acrescentar uma entrada
#: não esconde tela — só deixa de explicá-la.
_PARA_QUE = {
    "api.user": "Trocar senha, ver e atribuir plano, desativar conta.",
    "api.sessionresult": "O treino que aconteceu. Responde a “meu treino não apareceu”.",
    "api.sessionclaim": "De quem é cada sessão (conta ou aparelho).",
    "api.plan": "Quanto cada plano libera. Muda a admissão sem restart.",
    "api.exercise": "O que aparece no app: nome, foto, ordem, MET, e o que está ligado.",
    "api.siteconfig": "Duração, countdown, vagas de cloud e as faixas da pré-configuração.",
    "admin.logentry": "Quem mudou o quê, e quando. Somente leitura.",
}


@register.filter
def para_que(model_str: str) -> str:
    return _PARA_QUE.get(str(model_str).lower(), "")
