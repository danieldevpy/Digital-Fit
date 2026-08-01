"""Liga o limite diário do Free: 10 sessões/dia (SPEC-016, T-063).

A T-073 deixou esta linha em `daily_sessions = 0` (ilimitado) **de propósito**, e disse por
quê: "uma migration que já entregasse o limite novo faria a T-073 mudar comportamento no dia do
deploy, escondida atrás de 'só infraestrutura'". Aqui é o contrário — mudar comportamento é o
ponto da task, e a mudança aparece no nome do arquivo.

**Só toca no que ainda está no valor neutro.** `filter(daily_sessions=0)` não é paranoia: entre
a T-073 e hoje o painel existe, e quem já tiver escolhido um limite no formulário não pode
perdê-lo para o número que esta spec propôs meses antes. Migration de dados que sobrescreve
decisão de operação é a que ninguém percebe até o limite errado recusar um cliente.

`subscriber` fica em `0` (ilimitado). A SPEC-016 pede "limite diário generoso" para a
assinatura, e generoso não tem número: inventar um aqui seria escolher, por chute, o ponto em
que um assinante ouve não. Ilimitado atende o critério 2 ("assinante não é recusado") e deixa a
escolha para quando houver assinante de verdade para medir.

A versão da configuração sobe junto (`SiteConfig.version`), porque configuração mudou de fato —
é o carimbo que a T-075 pôs no `session.started` e no relatório. O snapshot em cache não é
invalidado daqui (`update()` não dispara `post_save`, e migration não deve escrever no cache):
quem cobre esta janela é o TTL de 5 min do próprio snapshot, que existe exatamente para o
`.update()` que escapa do signal.
"""

from django.db import migrations
from django.db.models import F

#: Copiados de `api.quota`, não importados: migration é um retrato do passado e precisa
#: continuar rodando igual no dia em que a constante mudar de valor ou sumir.
FREE_LIMIT = 10

FREE_MESSAGE = (
    "Você treinou muito hoje 🎉 Suas sessões de hoje acabaram. "
    "Descanso faz parte — e a assinatura tira o limite quando você quiser mais."
)


def liga(apps, schema_editor):
    Plan = apps.get_model("api", "Plan")
    mudou = Plan.objects.filter(slug="free", daily_sessions=0).update(
        daily_sessions=FREE_LIMIT, quota_message=FREE_MESSAGE
    )
    if mudou:
        apps.get_model("api", "SiteConfig").objects.filter(pk=1).update(version=F("version") + 1)


def desliga(apps, schema_editor):
    Plan = apps.get_model("api", "Plan")
    # Simétrico ao `liga`: só desfaz o que ele fez. Um Free com 15 no painel não volta a 0 aqui.
    mudou = Plan.objects.filter(slug="free", daily_sessions=FREE_LIMIT).update(
        daily_sessions=0, quota_message=""
    )
    if mudou:
        apps.get_model("api", "SiteConfig").objects.filter(pk=1).update(version=F("version") + 1)


class Migration(migrations.Migration):
    dependencies = [("api", "0009_sessionresult_config_version")]

    operations = [migrations.RunPython(liga, desliga)]
