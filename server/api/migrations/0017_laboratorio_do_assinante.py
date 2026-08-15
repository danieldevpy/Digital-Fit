"""O assinante passa a enxergar `calibrado` — o Laboratório 🧪 (SPEC-020 §Planos / T-090).

A migration 0006 semeou os três planos com `min_maturity: "validado"`, que era o valor neutro
correto naquele dia: a coluna nascia junto com a tabela e nada a lia ainda. A T-090 traz a regra
que a lê, e aí o valor deixa de ser neutro — com `validado` em todos, o eixo maturidade existiria
sem nunca mudar nada para ninguém.

**Só a linha do assinante, e só se ela ainda estiver no valor semeado.** Quem já mexeu nisso pelo
painel decidiu alguma coisa, e uma migration que sobrescrevesse essa decisão seria pior que não
existir: a SPEC-018 inteira é sobre configuração de negócio ser editável sem deploy, e um deploy
que desfaz a edição quebra essa promessa em silêncio.

Não muda nada observável hoje: nenhum exercício está em `calibrado` (os quatro do catálogo são
dois `validado` e dois `beta`). O efeito aparece na primeira promoção `beta → calibrado`, que é a
T-096/T-108.
"""

from django.db import migrations


def abrir_o_laboratorio(apps, _schema_editor) -> None:
    Plan = apps.get_model("api", "Plan")
    Plan.objects.filter(slug="subscriber", min_maturity="validado").update(min_maturity="calibrado")


def fechar_o_laboratorio(apps, _schema_editor) -> None:
    Plan = apps.get_model("api", "Plan")
    Plan.objects.filter(slug="subscriber", min_maturity="calibrado").update(min_maturity="validado")


class Migration(migrations.Migration):
    dependencies = [("api", "0016_meta_diaria")]

    operations = [migrations.RunPython(abrir_o_laboratorio, fechar_o_laboratorio)]
