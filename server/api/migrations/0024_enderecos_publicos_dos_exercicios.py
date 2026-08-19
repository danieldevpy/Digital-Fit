"""O endereço público de cada exercício em pt-BR (SPEC-026 §Escopo, T-165).

A `0023` criou as colunas; esta preenche a **base** dos quatro exercícios que existem.

**Por que isto é migration e não trabalho de painel.** Sem dado, `url_slug` cai no slug técnico
e a página nasce em `/exercicios/squat/` — endereço inglês numa URL portuguesa. A razão
declarada da task é que *a palavra na URL é sinal de busca*: ninguém procura "squat" em
português. Entregar o mecanismo e deixar o endereço errado seria entregar a task sem o
resultado dela. `Exercise.url_slug` é coluna base, o mesmo lugar de onde `display_name` já
nasceu semeado na `0008`.

**Por que o endereço em INGLÊS não entra aqui.** Ele mora em `ExerciseTranslation`, e a T-146
declarou — com teste próprio, `test_migration_nao_criou_traducao_nenhuma` — que nenhuma
migration cria linha de tradução: tradução é conteúdo de operador, e uma migration que a
inventasse tiraria do painel a autoria daquilo que ele é dono. Então o inglês continua vindo do
painel, e o que falta fica **visível** em vez de silencioso: `manage.py i18n_status` passou a
contar `url_slug` como campo traduzível nesta task, e é ele quem lista quem ainda está sem.

Até lá o endereço inglês cai no slug técnico. Para `squat` e `abdominal` isso já é a palavra
certa; para `jumping_jack` e `flexao` não é, e são esses dois que o `i18n_status` vai cobrar.

Só escreve onde está em branco: banco com endereço já editado no painel não é sobrescrito por
um deploy.
"""

from django.db import migrations

#: slug técnico → endereço público em pt-BR
ENDERECOS = {
    "jumping_jack": "polichinelo",
    "squat": "agachamento",
    "flexao": "flexao-de-braco",
    "abdominal": "abdominal",
}


def preenche(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")

    for slug, endereco in ENDERECOS.items():
        Exercise.objects.filter(slug=slug, url_slug="").update(url_slug=endereco)


def limpa(apps, schema_editor):
    """Devolve ao estado anterior: endereço em branco cai no slug técnico, e a página existe."""
    Exercise = apps.get_model("api", "Exercise")

    for slug, endereco in ENDERECOS.items():
        Exercise.objects.filter(slug=slug, url_slug=endereco).update(url_slug="")


class Migration(migrations.Migration):
    dependencies = [("api", "0023_paginas_publicas_por_exercicio")]

    operations = [migrations.RunPython(preenche, limpa)]
