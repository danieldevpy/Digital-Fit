# Dataset de keypoints — schema

Corpus gravado pelo `dataset-writer` (SPEC-010, T-021): **um arquivo Parquet por sessão**,
uma linha por frame. É o ativo de longo prazo do projeto — o classificador temporal da SPEC-007
(Fase Evolução) e qualquer treino futuro saem daqui, não de vídeo.

```
dataset/
  2026-07-28/
    529fad43-1d0e-4b0a-9c11-8a3f7e2b1c00.parquet
    f1e71237-....parquet
  2026-07-29/
    ...
```

A pasta é o **dia UTC do relógio do servidor**, não o `ts` do evento: `ts` vem do cliente, e um
celular com a data errada espalharia sessões por 1970 e 2038 dentro do corpus.

## Ler

```python
import pandas as pd

df = pd.read_parquet("dataset/2026-07-28/529fad43-....parquet")
df.head()

# Todo o corpus de um dia:
import glob

todos = pd.concat(pd.read_parquet(p) for p in glob.glob("dataset/*/*.parquet"))
```

A matriz que um modelo temporal consome sai sem transformação:

```python
from workers.dataset_writer.parquet import COORD_COLUMNS

X = df[list(COORD_COLUMNS)].to_numpy()  # (n_frames, 132), float32
```

## Colunas

| coluna | tipo | o que é |
| --- | --- | --- |
| `session_id` | string | Sessão de origem. Repetido em toda linha do arquivo. |
| `seq` | int32 | Contador monotônico por sessão, direto do envelope. **Não é reindexado**: buracos são reais e significam frame perdido ou fora do contrato. |
| `ts` | int64 | Epoch em ms medido no produtor (**relógio do cliente**). Consistente dentro de uma sessão; comparar entre sessões é outra conversa. |
| `exercise` | string | Rótulo vindo do `session.started`. `unknown` quando o writer subiu no meio da sessão e não viu a abertura. |
| `source` | string | `edge` (extraído no navegador), `cloud` (pose-worker) ou `file` (bancada). Existe para que um replay de eval nunca se disfarce de sessão real. |
| `degraded` | bool | Frame com âncoras pouco visíveis (SPEC-006). Ver a ressalva abaixo. |
| 132 colunas `{landmark}_{x,y,z,v}` | float32 | Os 33 landmarks do MediaPipe. `v` é `visibility` (0–1), não uma coordenada. |

Os nomes dos landmarks são os de `Landmark` em `workers/shared/events.py`, em minúsculas:
`nose_x`, `nose_y`, `nose_z`, `nose_v`, `left_eye_inner_x`, … `right_foot_index_v`. A ordem das
componentes é sempre `[x, y, z, visibility]`.

`float32` porque o MediaPipe entrega precisão simples — `float64` guardaria zeros. Compressão
`zstd`. Uma sessão de 30 s a 15 fps dá ~450 linhas e ~250 KB.

## O que estes números **não** são

**Não são keypoints canônicos.** São os landmarks como chegaram: normalizados 0–1 no frame,
crus quanto a escala, posição e jitter. A canonicalização da SPEC-006 (torsos, recentragem,
One Euro) **não** é aplicada aqui de propósito: assá-la no arquivo congelaria os parâmetros de
filtro de hoje dentro do corpus, e mudar o `mincutoff` amanhã invalidaria tudo que já foi
gravado. O dataset guarda a entrada; a normalização é reproduzível a partir dela, e continua
sendo uma decisão revisável.

**`degraded` hoje é sempre `false`.** A coluna existe porque o contrato do `pose.frame` a tem,
mas quem calcula degradação é o `Normalizer` dentro do analysis-worker, e esse resultado não
volta para o evento. Enquanto isso não mudar (registrado em `BACKLOG.md`, Descobertas), quem
treinar deve derivar a própria máscara de qualidade pelas colunas `_v`.

## Garantias e limites

- **Sessão sem nenhum frame não gera arquivo** (SPEC-010, critério 3). Uma sessão abortada
  antes do primeiro frame simplesmente não aparece no corpus.
- **Escrita atômica**: o arquivo é gravado como `.parquet.tmp` e movido por cima. Um crash no
  meio da escrita deixa o arquivo anterior intacto em vez de um Parquet truncado.
- **Regravar substitui**: um replay da mesma sessão sobrescreve o arquivo, não duplica.
- **Best-effort, e isso é deliberado.** O ack ao Redis é imediato: se o writer estiver fora do
  ar durante uma sessão, aquela sessão não entra no corpus e ninguém é avisado. Segurar as
  mensagens até gravar seria teatro — `pose.frames` é aparado por `MAXLEN ~5000` (~11 sessões)
  e entrada aparada some do stream mesmo continuando pendente. A sessão do usuário nunca
  depende deste serviço: ele está fora do hot path por construção.
- **Uma réplica.** Duas dividiriam os frames de uma mesma sessão entre dois buffers, gerando
  dois arquivos parciais no lugar de um inteiro.

## Versão do schema

`SCHEMA_VERSION` (hoje **2**) vai nos metadados de cada arquivo, junto de
`digitalfit.landmark_count`:

```python
import pyarrow.parquet as pq

pq.read_schema("....parquet").metadata
# {b'digitalfit.schema_version': b'2', b'digitalfit.landmark_count': b'33', ...}
```

### O que mudou

**2 (T-176, SPEC-027)** — entram duas colunas de procedência da imagem, constantes na sessão
inteira como o `exercise`:

| coluna | valores | para quê |
|---|---|---|
| `facing` | `user`, `environment`, `""` | qual câmera filmou. Sessão em que uma pessoa filma a outra tem estatística de enquadramento diferente — quem segura o aparelho enquadra melhor que um celular apoiado. |
| `orientation` | `portrait`, `landscape`, `landscape_forced`, `""` | como o aparelho estava. **`landscape_forced` é o valor que justifica a coluna**: é o celular com a rotação de tela travada cujo dono pediu o layout deitado, e nele o quadro da câmera *não* girou junto — o mundo chega deitado, e as contas da SPEC-003 sobre a altura do frame passam a medir outra coisa. É o único jeito de excluir essas sessões de uma calibração. |

`""` significa "esta sessão não soube dizer" — cliente anterior à T-176, ou origem em arquivo
(a superfície de dev, que roda sobre vídeo gravado e não tem aparelho na mão). É diferente de
qualquer um dos outros valores, e de propósito: carimbar `user`/`portrait` por padrão poria no
corpus uma afirmação que ninguém fez.

Arquivo da versão 1 continua legível — as colunas novas simplesmente não existem lá. Quem
passar a **exigir** o rótulo é que precisa olhar a versão antes de perguntar.

Mudar, remover ou reordenar coluna é quebra: sobe a versão em
`workers/dataset_writer/parquet.py` e registra aqui o que mudou.
