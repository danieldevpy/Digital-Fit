"""A orientação em que cada exercício rende (SPEC-027 §E, T-174).

Duas operações e uma só ideia. O campo nasce com `qualquer` — default que não muda nada para
quem já existe — e a segunda operação preenche os quatro do catálogo de hoje, porque deixá-los
todos em `qualquer` faria a feature nascer inerte e, pior, faria o **embutido do cliente
divergir do banco**: o `catalog.test.ts` cobra que os dois espelhem, e é o `[A/T-051]` que
essa cobrança existe para impedir.

Os valores não são chute — são o que o `scene_tip` já dizia em texto. Flexão e abdominal são
de chão, o corpo fica na horizontal e a câmera vai deitada; polichinelo e agachamento são em
pé, e é a ALTURA do quadro que precisa sobrar (no polichinelo os braços ainda sobem acima da
cabeça). Esta migration só transforma uma frase que a tela não conseguia comparar num valor
que ela consegue.
"""

from django.db import migrations, models


def preenche(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")
    for slug, valor in (
        ("jumping_jack", "retrato"),
        ("squat", "retrato"),
        ("flexao", "paisagem"),
        ("abdominal", "paisagem"),
    ):
        Exercise.objects.filter(slug=slug).update(orientacao_recomendada=valor)


def desfaz(apps, schema_editor):
    """Volta todo mundo para `qualquer` — o estado em que a coluna nasce."""
    Exercise = apps.get_model("api", "Exercise")
    Exercise.objects.update(orientacao_recomendada="qualquer")


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0024_enderecos_publicos_dos_exercicios"),
    ]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="orientacao_recomendada",
            field=models.CharField(
                choices=[
                    ("retrato", "Em pé (retrato)"),
                    ("paisagem", "Deitado (paisagem)"),
                    ("qualquer", "Tanto faz"),
                ],
                default="qualquer",
                help_text="Aparece como conselho na pré-configuração quando o aparelho está na outra orientação. Nunca impede treinar.",
                max_length=10,
                verbose_name="orientação recomendada",
            ),
        ),
        migrations.RunPython(preenche, desfaz),
    ]
