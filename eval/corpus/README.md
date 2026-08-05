# Corpus de avaliação — guia de gravação (SPEC-012 / T-038)

Os vídeos deste diretório **não vão para o git** (`.gitignore`); só o `manifest.yaml` vai.
Quem clonar o repositório precisa das gravações para rodar a bancada.

```bash
uv run python -m eval.evalctl run eval/corpus/ --report eval/out/eval.json
uv run python -m eval.evalctl parity eval/corpus/polichinelo-01.mp4 --expected-reps 20
```

## Para que serve

A bancada mede acurácia **sem sistema no ar e sem câmera**. É o que permite mexer na FSM sem
medo: `evalctl compare` reprova a mudança que piora a contagem. Um corpus pequeno e honesto
vale mais que um grande e mal rotulado — o rótulo é a verdade contra a qual tudo é medido.

## Como gravar

O essencial, em ordem de importância:

1. **Corpo inteiro no quadro, o tempo todo.** Pés e mãos inclusive — no topo do polichinelo as
   mãos sobem acima da cabeça. Se a mão sai do quadro, a rep não fecha.
2. **Celular parado.** Apoiado em algo, na horizontal ou vertical, sem ninguém segurando.
   Câmera tremendo vira ruído que a normalização não tem como distinguir de movimento.
3. **Conte as repetições enquanto grava** e anote. Esse número é o `expected_reps`, e é a
   única coisa do manifest que não dá para recuperar depois sem reassistir.
4. **20 a 30 segundos.** A sessão do produto é de 30s; vídeos muito mais longos não
   representam o uso real.
5. **Comece com 2 a 3 segundos parado, em pé, braços ao lado do corpo.** Não é preferência: o
   sistema mede o corpo nesse intervalo (a calibração da SPEC-004) e só depois começa a
   contar. Um vídeo que emenda direto no exercício perde as repetições que acontecem durante
   a medição — e o número que a bancada reporta deixa de representar o produto, onde sempre há
   countdown. Os vídeos `02` e `03` do corpus foram gravados sem isso e perdem 2 reps cada por
   esse motivo.

## O que variar entre os vídeos

Um corpus com 15 gravações idênticas mede uma condição só. O valor está na variedade:

| dimensão | variações que interessam |
|---|---|
| distância | perto (corpo ocupa quase todo o quadro), média, longe |
| luz | dia, à noite com luz de teto, contraluz (janela atrás) |
| ângulo | de frente, ligeiramente de lado (~30°) |
| roupa | contraste alto e baixo com o fundo |
| fundo | liso, bagunçado, com outras pessoas passando |
| execução | limpa, "preguiçosa" (braços não sobem tudo), rápida demais |

As execuções **imperfeitas são as mais valiosas**: são elas que testam o feedback engine
(SPEC-008) e os sinais de qualidade, não só a contagem.

## Como registrar no manifest

```yaml
- file: polichinelo-02.mp4
  exercise: jumping_jack
  expected_reps: 18
  conditions:
    distancia: longe
    luz: contraluz
    execucao: preguicosa
```

Os campos de `conditions` são livres, mas **use os mesmos nomes entre vídeos**: o relatório
agrupa por eles (`por luz`, `por distancia`) e é assim que se descobre "erra sempre em
contraluz". Campo vazio é melhor que campo errado.

## Nomeação

`<exercicio>-<numero>.mp4`, dois dígitos: `polichinelo-01.mp4`, `polichinelo-02.mp4`.

## Exercícios de chão: flexão e abdominal (T-106/T-107)

Estes dois nasceram **calibrados só no gerador sintético** — não existe um único vídeo de gente
de verdade por trás dos limiares deles. É exatamente para isso que este corpus existe, e é o
que separa `beta` de `calibrado` na SPEC-020: **8 vídeos rotulados por exercício**.

A gravação muda em três pontos, e os três importam mais que no polichinelo:

1. **Celular DEITADO no chão, de lado.** Não é preferência de enquadramento: de frente, uma
   flexão é um corpo encolhendo contra a lente, e não há feature que sobreviva a isso. A pessoa
   fica de perfil para a câmera, corpo inteiro no quadro, da cabeça aos pés.
2. **Comece 2 a 3 segundos parado NA POSIÇÃO DO EXERCÍCIO** — na prancha (flexão) ou deitado de
   joelho dobrado (abdominal), não em pé. A calibração mede o corpo nesse intervalo, e ela
   precisa medir o corpo que vai treinar.
3. **No abdominal, calcanhar perto do quadril.** A altura do joelho é a referência da contagem;
   pé longe demais abaixa a referência e infla a medida. Gravar uma variação com o pé longe é
   útil — é justamente a condição que a bancada precisa medir —, mas anote em `conditions`.

O que vale a pena variar, além da tabela acima:

| dimensão | variações que interessam |
|---|---|
| lado | perfil para a esquerda e para a direita (a FSM não deve se importar) |
| formato | vídeo em paisagem e em retrato — é o eixo que a anisotropia do espaço normalizado ataca (ver `[A/T-106]` no BACKLOG) |
| execução (flexão) | limpa, meia amplitude, quadril caindo, quadril empinado, de joelhos |
| execução (abdominal) | limpa, curta demais, no impulso (rápida), pé longe do quadril |

```yaml
- file: flexao-01.mp4
  exercise: flexao
  expected_reps: 12
  conditions:
    orientacao: paisagem
    angulo: perfil esquerdo
    inicio: ~3s parado na prancha
    execucao: limpa
```

### Vídeos da internet servem?

Servem, e são o caminho mais rápido para os 8 primeiros — desde que **o rótulo seja seu**:
`expected_reps` é a contagem que uma pessoa fez assistindo, e um número herdado de outra fonte
envenena a bancada inteira. Duas ressalvas práticas: o vídeo tem de ter a pessoa de perfil e
inteira no quadro (a maioria dos tutoriais corta na cintura ou troca de ângulo no meio), e
corte de câmera no meio da série invalida a gravação para contagem — a FSM não sabe que houve
corte, e o pulo vira repetição fantasma ou repetição perdida.

Há corpus público com este recorte: o **RepCount** (`svip-lab.github.io/dataset/RepCount_dataset.html`)
tem `pushup` e `situp` entre suas 7 classes, com anotação de início e fim de cada repetição —
ou seja, já traz o rótulo no formato de que esta bancada precisa. Serve para as primeiras
varreduras; o corpus próprio continua sendo o que decide, porque é ele que tem as condições do
produto (celular no chão, 30 s, luz de casa).

Rodada típica de uma varredura de limiar, depois que os vídeos existirem:

```bash
uv run python -m eval.evalctl run eval/corpus/ --report eval/out/flexao-baseline.json
# mexe no limiar em workers/analysis_worker/exercises/flexao.py
uv run python -m eval.evalctl run eval/corpus/ --report eval/out/flexao-novo.json
uv run python -m eval.evalctl compare eval/out/flexao-baseline.json eval/out/flexao-novo.json
```

A tabela da varredura vai para o DEVLOG — limiar escolhido sem o número que o justificou é
chute com aparência de medição.
