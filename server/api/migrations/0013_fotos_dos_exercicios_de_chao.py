"""Flexão e abdominal ganham foto de demonstração (T-106/T-107).

A `0012` cadastrou os dois com `demo_img` vazio porque a foto não existia — a tela caía na
figura do exercício, que é o fallback certo mas não é o produto. Agora existem quatro fotos no
mesmo padrão das outras (900×900, ~90 KB, mesmo ginásio escuro, mesmo esqueleto neon).

**As fotos são de PERFIL, com a câmera no chão**, e isso é conteúdo, não estética: a demo do
Guia é a primeira coisa que ensina o enquadramento, e enquadramento errado num exercício de
chão faz a sessão inteira sair zerada. Uma foto frontal aqui seria uma instrução errada com
cara de instrução certa.

`update` e não `get_or_create`: as linhas já existem desde a 0012. Rodar duas vezes é
inofensivo, e um banco onde alguém já trocou a foto pelo painel **não** é sobrescrito — o
filtro só pega quem ainda está com o campo vazio, que é exatamente o estado que esta migration
existe para consertar.
"""

from django.db import migrations

FOTOS = {
    "flexao": {
        "demo_img": "/img/guia/flexao-2.jpg",
        "passos": [
            "/img/guia/flexao-1.jpg",
            "/img/guia/flexao-1.jpg",
            "/img/guia/flexao-2.jpg",
        ],
    },
    "abdominal": {
        "demo_img": "/img/guia/abdominal-2.jpg",
        "passos": [
            "/img/guia/abdominal-1.jpg",
            "/img/guia/abdominal-1.jpg",
            "/img/guia/abdominal-2.jpg",
        ],
    },
}


def aplica(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")

    for slug, dados in FOTOS.items():
        exercicio = Exercise.objects.filter(slug=slug, demo_img="").first()
        if exercicio is None:
            continue  # não existe, ou alguém já pôs uma foto pelo painel
        exercicio.demo_img = dados["demo_img"]
        exercicio.save(update_fields=["demo_img"])
        for passo, img in zip(exercicio.guide_steps.order_by("ordem"), dados["passos"]):
            if passo.img:
                continue
            passo.img = img
            passo.save(update_fields=["img"])


def desfaz(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")

    for slug, dados in FOTOS.items():
        exercicio = Exercise.objects.filter(slug=slug, demo_img=dados["demo_img"]).first()
        if exercicio is None:
            continue
        exercicio.demo_img = ""
        exercicio.save(update_fields=["demo_img"])
        exercicio.guide_steps.filter(img__in=dados["passos"]).update(img="")


class Migration(migrations.Migration):
    dependencies = [("api", "0012_exercicios_de_chao")]

    operations = [migrations.RunPython(aplica, desfaz)]
