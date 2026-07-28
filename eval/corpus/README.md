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
5. Alguns segundos parados no começo são bem-vindos — é o que acontece quando a pessoa apoia o
   celular e se afasta.

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
