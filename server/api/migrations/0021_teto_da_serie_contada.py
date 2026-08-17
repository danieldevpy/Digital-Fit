"""Sobe o teto de sessão da assinatura para 180 s — o que destrava o modo contado (SPEC-023 §4).

A §4 decidiu que o modo contado **não tem flag própria**: o gate dele é ter `session_max_s`
generoso, e o teto da série é esse mesmo número. O código da T-136 implementa a régua
(`COUNTED_MIN_CEILING_S = 60`), mas os três planos saíram da `0006` com `session_max_s = 30` —
então, sem esta migration, o modo contado nasceria recusado para todo mundo, inclusive para
quem paga. Uma feature que sobe morta e depende de alguém lembrar de ligá-la no painel é uma
feature que a T-137 vai construir para ninguém.

Aqui vale a mesma inversão da `0010`: a `0006` documentou que migration de infra não entrega
mudança de produto, e este arquivo entrega — porque mudar comportamento **é** o ponto da task, e
a mudança aparece no nome do arquivo em vez de se esconder atrás de "só configuração".

**Três minutos, e por quê.** 15 repetições (a meta padrão) a 5 rpm; mais lento do que isso não é
alguém treinando devagar, é alguém que parou. O teto é também a alavanca de capacidade da VPS
(§Notas técnicas: sessão contada alonga a média e reduz a vazão de cloud por hora), e é por isso
que ele mora no `Plan` — subir ou descer este número é decisão de operação, feita no painel,
sem deploy.

**Só toca no que ainda está no valor neutro** (`session_max_s=30`), pela razão da `0010`: quem
já tiver escolhido um teto no formulário não pode perdê-lo para o número que a spec propôs
antes. Free e visitante ficam nos 30 s — é o conteúdo do cadeado da SPEC-016, e o modo livre de
30 s continua completo e bom.

A versão da configuração sobe junto (carimbo da T-075), e o snapshot em cache não é invalidado
daqui: quem cobre a janela é o TTL de 5 min, que existe para o `.update()` que escapa do signal.
"""

from django.db import migrations
from django.db.models import F

#: Espelha `api.config._FLOOR_PLAN["subscriber"]["session_max_s"]`. Copiado e não importado:
#: migration é retrato do passado e precisa rodar igual no dia em que a constante mudar.
TETO_DA_ASSINATURA_S = 180

#: O valor neutro da `0006`, que é também o teto do Free de hoje.
TETO_NEUTRO_S = 30


def sobe(apps, schema_editor):
    Plan = apps.get_model("api", "Plan")
    mudou = Plan.objects.filter(slug="subscriber", session_max_s=TETO_NEUTRO_S).update(
        session_max_s=TETO_DA_ASSINATURA_S
    )
    if mudou:
        apps.get_model("api", "SiteConfig").objects.filter(pk=1).update(version=F("version") + 1)


def desce(apps, schema_editor):
    Plan = apps.get_model("api", "Plan")
    # Simétrico ao `sobe`: só desfaz o que ele fez. Um teto de 300 s escolhido no painel não
    # volta para 30 aqui.
    mudou = Plan.objects.filter(slug="subscriber", session_max_s=TETO_DA_ASSINATURA_S).update(
        session_max_s=TETO_NEUTRO_S
    )
    if mudou:
        apps.get_model("api", "SiteConfig").objects.filter(pk=1).update(version=F("version") + 1)


class Migration(migrations.Migration):
    dependencies = [("api", "0020_treino_em_series")]

    operations = [migrations.RunPython(sobe, desce)]
