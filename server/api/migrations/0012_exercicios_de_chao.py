"""Flexão e abdominal entram no catálogo (T-106/T-107), nascendo `beta`.

Mesma forma da `0008_catalogo_inicial`: dados copiados, não gerados — migration é retrato do
passado e precisa continuar rodando igual no dia em que o catálogo do cliente mudar.

**A maturidade aqui é `beta` de verdade, e isso tem consequência visível**: pelos critérios da
SPEC-020 o `beta` não é liberado por plano nenhum — só aparece para conta com `is_admin`. Os
dois exercícios sobem a produção invisíveis para o usuário comum, e é assim que tem de ser:
os limiares foram calibrados no gerador sintético, contra nenhum vídeo de gente fazendo
flexão. Promover a `calibrado` é a task do corpus (≥ 8 vídeos rotulados por exercício), não
esta.

Diferente dos dois primeiros exercícios, estes **não têm foto de demonstração**. `demo_img` e
os passos vão vazios de propósito: a tela cai na figura do exercício (o boneco de
`EXERCISE_FIGURES`) em vez de apontar para um arquivo que não existe. Trocar por foto depois é
edição no painel, sem deploy.

`scene_tip` é o campo que a T-106 criou e o motivo pelo qual estes dois exercícios podiam ter
subido quebrados: a frase fixa da tela mandava apoiar o celular na vertical a 2 metros, que é
o oposto do que uma flexão precisa.

MET: valores de tabela (Compendium) — flexão 8,0 (calistenia vigorosa), abdominal 3,8.
"""

from django.db import migrations

CENA_CHAO = (
    "celular deitado no chão, de lado, a uns 2 metros — a tela precisa ver seu corpo "
    "inteiro de perfil, da cabeça aos pés."
)

EXERCICIOS = [
    {
        "slug": "flexao",
        "display_name": "Flexão de braço",
        "category": "forca",
        "muscle_group": "Peito, ombro e tríceps",
        "default_tip": "Corpo numa linha reta da cabeça aos pés, do começo ao fim.",
        # `none` pelo mesmo motivo do agachamento: o cliente só sabe desenhar abdução de
        # braço, e o ângulo que importaria aqui (cotovelo) ele não calcula.
        "main_angle": "none",
        "demo_img": "",
        "dot_color": "#f59e0b",
        "ordem": 2,
        "met": 8,
        "scene_tip": CENA_CHAO,
        "passos": [
            (
                "",
                "Deite o celular no chão, de lado, e fique de perfil para ele — ele precisa "
                "ver você da cabeça aos pés.",
            ),
            (
                "",
                "Comece na prancha: mãos abaixo dos ombros, braço estendido, corpo numa linha "
                "reta da cabeça aos calcanhares.",
            ),
            (
                "",
                "Desça dobrando o cotovelo até uns 90°, com o peito perto do chão, e suba "
                "estendendo o braço — a subida completa conta a repetição.",
            ),
        ],
    },
    {
        "slug": "abdominal",
        "display_name": "Abdominal",
        "category": "core",
        "muscle_group": "Abdômen",
        "default_tip": "Suba com o abdômen, devagar, sem puxar o pescoço.",
        "main_angle": "none",
        "demo_img": "",
        "dot_color": "#a78bfa",
        "ordem": 3,
        "met": 3.8,
        "scene_tip": CENA_CHAO,
        "passos": [
            (
                "",
                "Deite o celular no chão, de lado, e deite-se de perfil para ele — ele precisa "
                "ver seu tronco e seus joelhos.",
            ),
            (
                "",
                "Deite de costas com os joelhos dobrados e os pés apoiados, calcanhar perto do "
                "quadril: é o joelho levantado que serve de referência para a contagem.",
            ),
            (
                "",
                "Suba encolhendo o abdômen até as escápulas saírem do chão, mantendo a lombar "
                "apoiada, e volte devagar — a descida completa conta a repetição.",
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
            defaults={**dados, "enabled": True, "maturity": "beta", "min_plan": None},
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
    dependencies = [("api", "0011_exercise_scene_tip")]

    operations = [migrations.RunPython(cria, remove)]
