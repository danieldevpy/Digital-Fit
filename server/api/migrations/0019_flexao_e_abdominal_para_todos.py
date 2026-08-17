"""Flexão e abdominal vão para a prateleira de todo mundo: `validado` (T-113 / SPEC-020).

**Decisão de produto do Daniel, tomada com o risco na mesa.** O pedido foi direto: ao deslogar,
os dois somem, e ele quer os dois visíveis para qualquer pessoa. `validado` é o único valor que
faz isso — `calibrado` para no assinante e `beta` para no `is_admin`.

Os dois chegam aqui com lastro **muito** diferente, e registrar isso é a razão desta docstring
existir:

- **`flexao` tem medição.** A T-111 lhe deu oito itens de corpus, cinco com rótulo contado a mão,
  e ela fecha com MAE de **0,20 repetição** (16/16, 16/16, 11/11, 20/20, 26/25) nas duas vistas,
  depois de um conserto estrutural que não retunou limiar nenhum. Do critério de `validado` da
  SPEC-020 falta só a semana em produção e a paridade edge×cloud×navegador — e as duas exigem
  gente usando, que é o que esta migration libera.

- **`abdominal` não tem medição nenhuma.** Zero vídeo de gente real; os limiares vêm inteiros do
  gerador sintético (`tests/synthetic_keypoints.py`). É **exatamente** a posição em que a flexão
  estava quando passou 19 h em produção contando zero — o incidente que originou o
  `test_corpus_regressao.py`. A dívida continua declarada em `SEM_MATERIAL_REAL`, e o teste
  `test_exercicio_novo_nao_entra_em_producao_sem_video_de_gente_real` continua apontando para
  ela. O que muda aqui é só quem vê o exercício, não o que se sabe sobre ele.

Concretamente: se o abdominal contar errado, ele contará errado **para todo visitante**, e não
há um número neste repositório que preveja se isso vai acontecer. O caminho de volta é barato e
não exige deploy — é o campo Maturidade no painel (SPEC-018), que rebaixa em uma edição.

O que basta para fechar essa lacuna: **um** vídeo de abdominal de gente real no corpus. Com ele,
a mesma bancada que mediu a flexão hoje mede o abdominal em minutos.
"""

from django.db import migrations


def liberar_para_todos(apps, _schema_editor) -> None:
    Exercise = apps.get_model("api", "Exercise")
    # Só sobe quem está abaixo. Um `update` cego passaria por cima de um rebaixamento feito no
    # painel — e rebaixar no painel é justamente o freio de mão que esta migration deixa à mão.
    Exercise.objects.filter(slug="flexao", maturity__in=["beta", "calibrado"]).update(
        maturity="validado"
    )
    Exercise.objects.filter(slug="abdominal", maturity__in=["beta", "calibrado"]).update(
        maturity="validado"
    )


def voltar_ao_degrau_anterior(apps, _schema_editor) -> None:
    """Desfaz devolvendo cada um ao degrau que a medição sustenta, não a um valor comum.

    A flexão volta para `calibrado` (tem corpus) e o abdominal para `beta` (não tem). Um
    `down` que devolvesse os dois ao mesmo lugar apagaria a diferença que a `up` documenta.
    """
    Exercise = apps.get_model("api", "Exercise")
    Exercise.objects.filter(slug="flexao", maturity="validado").update(maturity="calibrado")
    Exercise.objects.filter(slug="abdominal", maturity="validado").update(maturity="beta")


class Migration(migrations.Migration):
    dependencies = [("api", "0018_flexao_calibrada")]

    operations = [migrations.RunPython(liberar_para_todos, voltar_ao_degrau_anterior)]
