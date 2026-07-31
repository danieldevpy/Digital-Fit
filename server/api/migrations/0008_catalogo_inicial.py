"""Os dois exercícios de hoje, com os valores de hoje (SPEC-018, T-074).

Fonte destes dados: `web/src/session/catalog.ts`, que era a fonte da verdade da apresentação
até esta task. **Copiado, não gerado** — migration é retrato do passado e precisa continuar
rodando igual no dia em que o arquivo do cliente mudar ou sumir.

Duas conversões acontecem aqui, e as duas importam:

1. **Categoria vira slug.** O cliente guardava a string de exibição (`'Cardio'`, `'Força'`);
   a SPEC-020 fez de `category` um vocabulário de contrato, porque as conquistas da SPEC-019 e o
   mix por objetivo da SPEC-022 consomem os slugs. Copiar a string quebraria os dois em silêncio.
2. **Maturidade nasce `validado` por decisão declarada, não por medição.** Pelos critérios da
   SPEC-020 nem o polichinelo nem o agachamento seriam `validado` hoje: o agachamento não tem
   corpus real (T-053 segue aberta) e a paridade edge×cloud×browser da T-040 tem uma passada
   manual pendente. Aplicar o critério retroativamente deixaria o Free **sem exercício nenhum**
   no dia em que esta migration subir — a task que prometia não mudar comportamento desligaria
   o produto. Está escrito na SPEC-018 §Grandfathering para ninguém ler o selo como evidência.

MET: valores de tabela (Compendium) da SPEC-020 §Roadmap — polichinelo 8, agachamento 5.
"""

from django.db import migrations

EXERCICIOS = [
    {
        "slug": "jumping_jack",
        "display_name": "Polichinelo",
        "category": "cardio",
        "muscle_group": "Corpo inteiro",
        "default_tip": "Mantenha o core contraído e movimentos controlados.",
        "main_angle": "arm_abduction",
        "demo_img": "/img/guia/polichinelo-2.jpg",
        "dot_color": "#34d399",
        "ordem": 0,
        "met": 8,
        "passos": [
            (
                "/img/guia/polichinelo-1.jpg",
                "Fique em pé, de frente para a câmera, corpo inteiro visível, braços ao lado do corpo.",
            ),
            (
                "/img/guia/polichinelo-2.jpg",
                "Salte abrindo as pernas e levando os braços acima da cabeça, ao mesmo tempo.",
            ),
            (
                "/img/guia/polichinelo-1.jpg",
                "Volte à posição inicial no salto seguinte — cada ida e volta conta uma repetição.",
            ),
        ],
    },
    {
        "slug": "squat",
        "display_name": "Agachamento",
        "category": "forca",
        "muscle_group": "Pernas e glúteos",
        "default_tip": "Desça com o peso nos calcanhares e o peito aberto.",
        # `none` não é ausência de dado: de frente, o ângulo do joelho MENTE (a T-052 mediu 133°
        # onde o corpo fazia 80°), e um número parado na tela durante o esforço lê como "não
        # está me vendo".
        "main_angle": "none",
        "demo_img": "/img/guia/agachamento-2.jpg",
        "dot_color": "#4d8cff",
        "ordem": 1,
        "met": 5,
        "passos": [
            (
                "/img/guia/agachamento-1.jpg",
                "Pés na largura dos ombros, pontas levemente para fora, braços à frente para equilibrar.",
            ),
            (
                "/img/guia/agachamento-2.jpg",
                "Desça empurrando o quadril para trás, peso nos calcanhares, até as coxas ficarem paralelas ao chão.",
            ),
            (
                "/img/guia/agachamento-1.jpg",
                "Suba estendendo as pernas sem tirar os pés do chão — subida completa conta a repetição.",
            ),
        ],
    },
]


def cria(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")
    ExerciseGuideStep = apps.get_model("api", "ExerciseGuideStep")

    for dados in EXERCICIOS:
        passos = dados.pop("passos")
        exercicio, criado = Exercise.objects.get_or_create(
            slug=dados["slug"],
            defaults={**dados, "enabled": True, "maturity": "validado", "min_plan": None},
        )
        dados["passos"] = passos  # a migration pode rodar duas vezes num banco remendado
        if not criado:
            continue
        for ordem, (img, texto) in enumerate(passos):
            ExerciseGuideStep.objects.create(
                exercise=exercicio, ordem=ordem, img=img, texto=texto
            )


def remove(apps, schema_editor):
    Exercise = apps.get_model("api", "Exercise")
    Exercise.objects.filter(slug__in=[e["slug"] for e in EXERCICIOS]).delete()


class Migration(migrations.Migration):
    dependencies = [("api", "0007_exercise_exerciseguidestep")]

    operations = [migrations.RunPython(cria, remove)]
