"""A flexão sai do laboratório: `beta → calibrado` (T-111 / SPEC-020 §Maturidade).

**É a primeira promoção do produto, e é o que faz o eixo maturidade da T-090 mudar alguma coisa
para alguém**: a migration 0017 abriu o Laboratório 🧪 do assinante (`min_maturity: calibrado`) e
até hoje não havia nada dentro dele. A partir daqui a flexão aparece para assinante e para
`is_admin`; para o Free ela continua invisível, porque a prateleira do Free é `validado`.

O que a SPEC-020 cobra para esta promoção, e o que existe:

- **Corpus real rotulado.** A flexão passa a ter oito itens no `eval/corpus/manifest.yaml`,
  seis com `expected_reps` e cinco com rótulo contado a mão nesta task (vale a vale do ângulo
  de cotovelo cru, com conferência visual). Antes eram três itens e dois rótulos, ambos
  herdados de título de vídeo de rede social — o que a Descoberta `[A/T-108]` registrava como
  o impedimento exato desta promoção.
- **Varredura de limiares contra ele.** Está no DEVLOG, com a tabela. O resultado que
  importa: nenhum limiar de profundidade mudou. O conserto foi estrutural (porteiro de chão
  com histerese + profundidade pelo cotovelo nas duas vistas), e a varredura confirma que
  0,63/0,80 continua no meio do platô depois dele.
- **Erro ≤ ±1 rep/20.** MAE de **0,20 repetição** nos cinco vídeos de rótulo próprio (16/16,
  16/16, 11/11, 20/20, 26/25). Era 9,14.

O que ela **não** tem, e por isso não vai a `validado`: a paridade edge×cloud×navegador no
mesmo vídeo e a semana em produção com taxa de sessão zerada abaixo de 20%. As duas exigem o
produto rodando com gente, e é isso que este degrau existe para viabilizar — o assinante vê,
treina, e a semana começa a contar.

O `abdominal` fica onde está. Ele continua sem um único vídeo de gente real, que é exatamente a
posição de que a flexão está saindo agora.

`scene_tip` também muda aqui: a frase servida falava só do celular deitado, e agora as duas
vistas contam. O texto do painel passa a ser o da vista padrão com a menção à outra — quem
escolhe qual delas vale é a pré-configuração, e as instruções de cada uma vivem no bundle do
cliente (`web/src/session/exerciseViews.ts`), como a figura do exercício.
"""

from django.db import migrations

CENA_ANTIGA = (
    "celular deitado no chão, de lado, a uns 2 metros — a tela precisa ver seu corpo "
    "inteiro de perfil, da cabeça aos pés."
)

CENA_NOVA = (
    "celular deitado no chão de lado (você de perfil) ou em pé à sua frente — escolha a "
    "posição da câmera na pré-configuração, e monte a cena para a que escolheu."
)


def promover(apps, _schema_editor) -> None:
    Exercise = apps.get_model("api", "Exercise")
    Exercise.objects.filter(slug="flexao", maturity="beta").update(maturity="calibrado")
    # Mesma cautela da 0017: só sobrescreve o texto que a 0012 semeou. Quem editou a cena pelo
    # painel decidiu alguma coisa, e desfazer isso num deploy quebraria em silêncio a promessa
    # da SPEC-018 de configuração editável sem deploy.
    Exercise.objects.filter(slug="flexao", scene_tip=CENA_ANTIGA).update(scene_tip=CENA_NOVA)


def rebaixar(apps, _schema_editor) -> None:
    Exercise = apps.get_model("api", "Exercise")
    Exercise.objects.filter(slug="flexao", maturity="calibrado").update(maturity="beta")
    Exercise.objects.filter(slug="flexao", scene_tip=CENA_NOVA).update(scene_tip=CENA_ANTIGA)


class Migration(migrations.Migration):
    dependencies = [("api", "0017_laboratorio_do_assinante")]

    operations = [migrations.RunPython(promover, rebaixar)]
