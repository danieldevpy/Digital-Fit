"""`Exercise.ref_cadence_rpm`: o ritmo em que o MET de tabela vale (SPEC-016, T-128).

Coluna **e** valores na mesma migration, de propósito. Uma coluna de cadência com `0` em todas
as linhas não é um estado neutro: `0` significa "desconhecido", e desconhecido apaga o card de
calorias (`--`). Subir a coluna vazia e preencher depois seria desligar o kcal do produto entre
dois deploys — o oposto do que esta task faz.

**Por que a cadência precisa existir.** O MET não é um número solto: ele descreve o gasto *a uma
intensidade*. Para um exercício contado por repetição, essa intensidade é um ritmo. Sem ele não
há como converter MET (por minuto) em caloria por repetição — e foi por não ter esta coluna que a
T-063 acabou faturando tempo de tela: `MET × minutos` cobra o mesmo de quem faz 40 polichinelos
e de quem fica parado olhando a câmera.

**Os números são premissa, e é por isso que são dado.** Cada valor abaixo é o ritmo típico em
que a fonte do MET (Compendium of Physical Activities) descreve aquele esforço — polichinelo e
flexão entram como "vigoroso", agachamento e abdominal como "moderado". Não medimos nenhum
deles em bancada. Ficarem em tabela é o que permite corrigi-los pelo painel quando o corpus da
SPEC-012 tiver algo melhor a dizer, sem deploy e sem tocar em código.
"""

from django.db import migrations, models
from django.db.models import F

#: slug → rep/min em que o `met` da linha vale. Copiados para cá e não importados: migration é
#: retrato do passado e precisa continuar rodando igual no dia em que o catálogo mudar.
CADENCIAS = {
    "jumping_jack": 50,  # MET 8,0 — "jumping jacks, vigorous"
    "squat": 20,  # MET 5,0 — agachamento livre, esforço moderado
    "flexao": 25,  # MET 8,0 — "push ups, vigorous effort"
    "abdominal": 20,  # MET 3,8 — abdominal/sit-up, esforço moderado
}


def preenche(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")
    mudou = 0
    for slug, rpm in CADENCIAS.items():
        # `filter(ref_cadence_rpm=0)` e não `update` cego: se alguém já ajustou a cadência pelo
        # painel entre este deploy e o próximo, o número dele não pode ser sobrescrito pelo
        # palpite desta migration.
        mudou += Exercise.objects.filter(slug=slug, ref_cadence_rpm=0).update(ref_cadence_rpm=rpm)
    if mudou:
        apps.get_model("api", "SiteConfig").objects.filter(pk=1).update(version=F("version") + 1)


def esvazia(apps, schema_editor):
    """Simétrico: só desfaz o que `preenche` fez, e a coluna some logo em seguida."""
    Exercise = apps.get_model("api", "Exercise")
    for slug, rpm in CADENCIAS.items():
        Exercise.objects.filter(slug=slug, ref_cadence_rpm=rpm).update(ref_cadence_rpm=0)


class Migration(migrations.Migration):
    dependencies = [("api", "0013_fotos_dos_exercicios_de_chao")]

    operations = [
        migrations.AddField(
            model_name="exercise",
            name="ref_cadence_rpm",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text="Ritmo em que o MET acima vale. 0 = desconhecido (o app mostra '--').",
                verbose_name="cadência de referência (rep/min)",
            ),
        ),
        migrations.RunPython(preenche, esvazia),
    ]
