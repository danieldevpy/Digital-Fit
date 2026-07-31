"""Planos e configuração inicial com os valores de HOJE (SPEC-018, T-073).

O ponto desta migration é que ela **não muda produto nenhum**. Ligar a SPEC-018 troca a origem
dos números (constante em código → linha em tabela), não os números:

- `anon.daily_sessions = 3` e a mensagem de recusa são o trial da SPEC-011 (`api/trial.py`).
- `free.daily_sessions = 0` (ilimitado) porque **hoje conta logada não tem quota nenhuma**. A
  SPEC-016 propõe 10/dia, e quem liga isso é a T-063. Uma migration que já entregasse o limite
  novo faria a T-073 mudar comportamento no dia do deploy, escondida atrás de "só infraestrutura".
- Duração 30–30 s para todo mundo: a faixa configurável é a T-064.
- `allow_cloud = True` em todos: cloud hoje é livre para quem passa no probe, e a trava por
  plano é da SPEC-011 Evolução.

As colunas que a Fase 5 vai consumir (`streak_protections_month`, `min_maturity`,
`daily_workout`) nascem aqui no valor **neutro** — o que cada uma faz é decidido pela spec dona
(SPEC-019/020/022), e nenhum consumidor delas existe ainda.
"""

from django.db import migrations

#: Igual a `api.trial.TRIAL_MESSAGE`. Copiado, e não importado: migration é um retrato do
#: passado e precisa continuar rodando igual no dia em que a constante mudar de valor ou sumir.
TRIAL_MESSAGE = (
    "Você já fez suas 3 sessões grátis de hoje. "
    "Crie uma conta para continuar treinando — é de graça e leva 30 segundos."
)

PLANOS = [
    {
        "slug": "anon",
        "nome": "Visitante",
        "is_default": False,  # escolhido pela ausência de usuário, nunca por ser o default
        "ordem": 0,
        "daily_sessions": 3,
        "quota_message": TRIAL_MESSAGE,
        "streak_protections_month": 0,
        "daily_workout": False,
    },
    {
        "slug": "free",
        "nome": "Free",
        "is_default": True,
        "ordem": 1,
        "daily_sessions": 0,
        "quota_message": "",
        "streak_protections_month": 1,
        "daily_workout": False,
    },
    {
        "slug": "subscriber",
        "nome": "Assinatura",
        "is_default": False,
        "ordem": 2,
        "daily_sessions": 0,
        "quota_message": "",
        "streak_protections_month": 2,
        "daily_workout": True,
    },
]

COMUM = {
    "session_min_s": 30,
    "session_max_s": 30,
    "countdown_max_s": 10,
    "allow_cloud": True,
    "history_limit": 50,
    "kcal_accumulation": False,
    "effects_enabled": False,
    "min_maturity": "validado",
    "flags": {},
}


def cria(apps, schema_editor):
    Plan = apps.get_model("api", "Plan")
    SiteConfig = apps.get_model("api", "SiteConfig")

    for dados in PLANOS:
        # `get_or_create` e não `create`: a migration precisa poder rodar num banco onde alguém
        # já criou o plano à mão (o caminho real de um ambiente que foi remendado antes do
        # deploy). Repetir o slug estouraria o índice único e travaria o `migrate`.
        Plan.objects.get_or_create(slug=dados["slug"], defaults={**COMUM, **dados})

    SiteConfig.objects.get_or_create(pk=1)


def remove(apps, schema_editor):
    Plan = apps.get_model("api", "Plan")
    Plan.objects.filter(slug__in=[p["slug"] for p in PLANOS]).delete()
    apps.get_model("api", "SiteConfig").objects.filter(pk=1).delete()


class Migration(migrations.Migration):
    dependencies = [("api", "0005_plan_siteconfig_user_plan_until_user_plan")]

    operations = [migrations.RunPython(cria, remove)]
