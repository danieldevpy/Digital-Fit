# SPEC-023 — Treino: séries, ritmo e modos de sessão
Status: draft | Camada: contrato + api + worker + client | Depende de: SPEC-004, SPEC-007, SPEC-009, SPEC-010, SPEC-016, SPEC-018 | Referência: ideias `docs/IDEIAS-2026-08-05-conversa.md` §2.1, §2.2, §2.16, §2.17 (2026-08-05)

## Entidade e responsabilidade

O **treino**: uma sequência de séries, com descanso entre elas, em que quem manda no relógio é
o corpo de quem treina — não o cronômetro. É a entidade que faltava entre a *sessão* (SPEC-009,
unidade de carga) e o *conteúdo* (SPEC-020/022, qual exercício fazer).

Frase que originou a spec, e que é o critério de tudo aqui:

> "O aplicativo vai contar o que ela tá fazendo. Não é 'você tem 10 segundos pra fazer 20
> flexões'. Ele conta 1, 2… quando tu acabar, ele entende os 20 que tu fez, e vai o tempo de
> descanso." … **"Um aplicativo que não te apressa e também não te atrasa."**

Hoje o produto só sabe fazer uma coisa: contar o máximo de repetições em 30 s. Isso é bom, é
competitivo, e vai ganhar nome (**modo livre**). Mas não é treinar. Treinar é fazer a série
até o fim, descansar, e ir para a próxima — e o idoso demora três minutos na série que o
atleta faz em quarenta segundos.

### O que esta spec **não** é dona

- **Não é dona de qual exercício entra no treino.** A composição é da SPEC-022 (Treino do Dia).
  Esta spec define o *formato* do plano para que a 022 tenha o que preencher.
- **Não é dona da posição inicial.** O gate por pose de prontidão é da SPEC-004 (Evolução,
  T-030). Aqui nasce só o **gesto deliberado de "estou pronto"**, que é outra coisa — ver §4.
- **Não é dona da unidade de carga.** Continua sendo a sessão (SPEC-009). Uma série **é** uma
  sessão. Esta spec não cria semáforo, fila nem worker.

## 1. Os dois modos

Cada série roda num de dois modos. O modo é declarado por item do plano.

| | **Modo livre** | **Modo contado** |
|---|---|---|
| O que é | máximo de repetições numa janela fixa | uma meta de repetições, sem pressa |
| Fim da série | a janela acabou (`completed`) | a meta foi atingida (`target_reached`) ou o teto estourou (`completed`) |
| Relógio | conta para baixo | conta para cima |
| Número que importa | quantas reps | quanto tempo até a meta |
| Existe hoje | **sim** — é o comportamento atual, sem nome | não |

**Modo livre é o que já está no ar.** Esta spec não muda uma linha do seu comportamento; ela dá
nome a ele e o declara como a metade competitiva do produto (o "quem faz mais em menos tempo"
do áudio). Isso é de propósito: o recorte que exige código novo é só o modo contado, e o modo
livre entra como **teste de regressão**, não como refatoração.

## 2. O plano de treino

Um plano é uma **lista ordenada de itens**. Cada item é uma série:

```
PlanoItem = {
  exercise: str,          # slug do catálogo (SPEC-020)
  set_mode: "livre" | "contado",
  target_reps: int,       # > 0 no modo contado; 0 no livre
  window_s: int,          # modo livre: tamanho da janela
  rest_s: int,            # descanso DEPOIS deste item; 0 no último
}
```

**Nota (T-134, achada ao codar — spec corrigida, não driblada em silêncio):** o campo nasceu
`mode` neste rascunho, mas `session.started` **já tem** um `mode` — o de extração de pose
(`edge`/`cloud`, SPEC-001/005). São dois eixos diferentes de uma mesma sessão (por onde os
keypoints saíram × como a série termina) e colidem em todas as camadas que já leem `mode` hoje:
o contrato, a coluna do `SessionResult` e o `to_report()`. Renomeado para `set_mode` — ecoa
`set_index`/`set_total`, que já são vocabulário de série nesta spec.

**Por que uma lista de itens, e não "N séries do exercício X":** porque a SPEC-022 vai querer
produzir circuito (cardio → força → mobilidade) e, se o formato só souber repetir um exercício,
ela terá que mudar o contrato depois. O formato aceita circuito **hoje**; a UI da Fase Inicial
só monta plano de exercício único (N séries iguais). Forma agora, tela depois — o custo de
aceitar `exercise` por item é zero, porque cada item já vira uma sessão independente, que é o
mecanismo que a §3 descreve.

**Fora de escopo, com dono:** *quanto tempo você tem?* (`docs/IDEIAS…` §2.16) é entrada de
**composição** — quem transforma "tenho 10 minutos" em uma lista de itens é a SPEC-022, não
esta spec. Registrado aqui porque a ideia nasceu na mesma conversa e a fronteira precisa estar
escrita.

## 3. Uma série é uma sessão; o descanso não é nada

A decisão já estava tomada na Evolução da SPEC-009 — *"cada série é uma sessão do ponto de
vista do admission control (a unidade de carga não muda)"* — e esta spec a executa:

```
[série 1: SESSÃO] → descanso (cliente) → [série 2: SESSÃO] → descanso → [série 3: SESSÃO]
```

**O descanso não é sessão, não é evento e não existe no servidor.** Ele é uma tela do cliente
com um contador. Isso não é preguiça, é a escolha certa por três motivos que valem escrever:

1. **Descanso não segura slot.** Se o descanso fosse parte da sessão, três pessoas descansando
   ocupariam os três slots de cloud (SPEC-009) sem produzir um frame. O semáforo protege
   capacidade de *inferência*; descanso não consome inferência.
2. **Repetição feita no descanso não conta**, de graça e sem regra nova — não há sessão para
   contá-la, e o cliente para de transmitir (a lápide da T-077 já garante isso).
3. **Nenhuma tabela nova.** O treino não vira entidade persistida; ele é a sequência de
   `SessionResult` que ele produziu. Princípio de derivação da casa (SPEC-019): estado novo
   exige justificativa, e aqui não há fato que não seja derivável.

### O carimbo que torna a sequência legível

Sem nada, o histórico de um treino de 3 séries é indistinguível de 3 sessões avulsas. Por isso
`session.started` ganha dois campos **aditivos**, na natureza de carimbo (como `config_version`
da T-075 — ninguém na análise os lê):

- `set_index: int = 0` — qual série é esta (1-based; `0` = sessão avulsa, que é todo o passado)
- `set_total: int = 0` — de quantas

Eles viajam para o `SessionResult` e permitem o relatório dizer "série 2 de 3". **Não criam a
entidade treino**: agrupar continua sendo leitura, não escrita.

## 4. O teto: por que "não te apressa" ainda tem um limite

O modo contado termina quando a meta é atingida. Mas uma sessão sem fim é um slot de admissão
vazado e um TTL que nunca expira — o `no_data` da SPEC-009 existe exatamente para isso. Então
existe um **teto**, e ele é honesto:

- O teto é o **`Plan.session_max_s` que já existe** (T-073). Nenhuma coluna nova.
- Estourar o teto **não é erro**: a série termina com `reason: "completed"` e o `rep_count` que
  a pessoa fez. O relatório diz "10 de 15" sem drama. Ninguém é punido por não terminar.

**Por que nenhuma coluna nova, e por que isso não é preguiça.** O primeiro desenho desta spec
criava um `Plan.set_ceiling_s`, com o argumento de que a janela competitiva (curta de
propósito) não pode virar o teto de quem é lento. O argumento está certo sobre o **`duration_s`
do evento** — que no modo livre é a janela escolhida — e errado sobre a **coluna do plano**:
`session_max_s` nunca foi a janela, é o limite superior do que aquele plano pode pedir. Para
modo livre, `duration_s` ∈ [`session_min_s`, `session_max_s`]; para modo contado,
`duration_s` = `session_max_s`. Mesmo número, mesmo significado ("o máximo que uma sessão deste
plano dura"), dois usos.

A objeção sobrevivente é que o Free tem `session_max_s = 30`, teto que cortaria qualquer série
contada no meio. **É a resposta certa, não o problema**: o modo contado é benefício de plano
pago (é o conteúdo do cadeado da SPEC-016), e o Free fica no modo livre de 30 s, que é completo
e bom. O gate do modo contado **é** ter `session_max_s` generoso — não precisa de flag própria.

Coluna que existe e ninguém lê apodrece: é a lição registrada do `Plan.history_limit`
(Descoberta `[T-073]`). Uma coluna nova aqui teria nascido com o mesmo destino, porque o número
que ela guardaria já está guardado.

**Nota (T-136): "generoso" virou número.** Esta seção pedia um teto generoso sem dizer quanto,
e a admissão precisa de uma régua para responder sim ou não. São duas decisões, tomadas ao
codar e registradas aqui para a spec continuar sendo a fonte:

- **A régua**: `COUNTED_MIN_CEILING_S = 60` (`api/config.py`) — o dobro da janela livre. Teto
  menor que isso não é teto de série, é a mesma janela competitiva com outro nome. É constante
  de código, e não campo do painel, porque derivá-la de um valor editável (`default_duration_s`)
  deixaria alguém destravar o modo contado em plano que não o suporta ao mexer em outra coisa.
- **O teto da assinatura**: 180 s, pela migration `0021` (15 repetições a 5 rpm). Sem ela o
  modo contado nasceria recusado para todo mundo — os três planos saíram da `0006` com 30 s —,
  e a §4 estaria descrevendo uma capacidade que nenhum plano tem. Free e visitante ficam nos
  30 s: é exatamente o cadeado que esta seção defende.

## 5. O gesto de prontidão

> "Aí tu já vai se posicionar na frente. Se posicionou, o bagulho entendeu que tu tá
> posicionado. Tá pronto? **Ok, eu levanto a mão.**"

**Estar em posição ≠ estar pronto**, e essa é a razão de o gesto existir separado do gate da
SPEC-004. Entre séries a pessoa já está de pé no lugar certo há dez segundos — e ainda está
recuperando o fôlego. O gate por pose diria "pode ir" cedo demais; o gesto é a pessoa dizendo.

- **Gesto**: os dois pulsos acima dos ombros, mantidos por 1 s. Reusa landmarks que a
  normalização já entrega; nenhuma feature nova.
- **Onde roda**: no **cliente**, porque durante o descanso não existe sessão nem worker. Isso
  tem uma consequência que precisa estar declarada: **o gesto só existe em modo edge.** No modo
  cloud o cliente não extrai pose, então o gesto não é oferecido.
- **Fallback universal**: o descanso sempre termina por temporizador ou por toque. O gesto
  **acelera**, nunca é a única saída — quem não conseguir fazê-lo (ou estiver em cloud) toca na
  tela. Trava única de acessibilidade seria trocar um problema por outro.

A fronteira com a SPEC-004: ela decide *se o corpo está na postura do exercício* e é dela o
`ready.progress`; esta spec decide *se a pessoa quer começar*. Quando a T-030 existir, as duas
se compõem — gesto libera, pose confirma — e nenhuma precisa mudar.

## 6. O número que mede evolução passa a ser cadência

Com duração variável, "fiz 15 reps" perde sentido comparativo: 15 em 40 s e 15 em 3 min são
treinos diferentes. O áudio já tinha chegado nisso:

> "A pessoa demorou 20 segundos pra fazer 10 polichinelos. Com o tempo ela vai se aperfeiçoando…
> tu fazia 10 em 30 segundos, agora tu faz 15. A sua média de polichinelo na semana ficou tanto."

- **Relatório da série**: cadência (reps/min) sempre; no modo contado, também o **tempo até a
  meta**. Nenhuma coluna nova — `rep_count` e a duração real já estão no `SessionResult`.
- **Comparação semana a semana**: derivação pura sobre `SessionResult` (mesma filosofia do
  `engagement.py`), por exercício, últimas 4 semanas. Sem tabela, sem contador, recomputável.

## Fase Inicial

### Escopo / Comportamento

- `set_mode`, `target_reps`, `set_index`, `set_total` no contrato (`workers/shared/events.py`
  primeiro — AGENTS.md); `SessionEndReason.TARGET_REACHED`.
- Modo contado no analysis-worker: a meta é do **servidor**, e é ele que encerra a série no
  frame da N-ésima repetição.
- Resolução do modo na admissão (`POST /api/sessions`), junto de quota, duração, countdown e
  cloud (T-073): o modo contado exige plano com `session_max_s` generoso, e o teto da série é
  esse número. **Sem coluna nova** (§4).
- Cliente: montador de plano de exercício único (N séries × meta × descanso), tela de descanso
  com contador e próximo item, gesto de prontidão (edge) com toque como saída universal.
- HUD do modo contado: anel conta **para cima** e mostra `7/15`; o anel de tempo restante some
  (não há janela) e dá lugar ao tempo decorrido.
- Relatório: cadência sempre; tempo até a meta no contado; "série 2 de 3" quando houver
  carimbo.
- Comparação de cadência por exercício nas últimas 4 semanas (derivada).

### Fora de escopo (vai para Evolução)

- **Circuito na UI** (itens com exercícios diferentes). O *formato* aceita; a tela da Fase
  Inicial só monta exercício único — quem vai preencher circuito é a SPEC-022, e construir a
  tela antes do gerador é construir para ninguém.
- **"Quanto tempo você tem?"** → SPEC-022 (§2 desta spec).
- **Desafio X1 / comparação entre pessoas** (`docs/IDEIAS…` §2.3) — depende do modo livre ter
  nome, que é o que esta spec entrega, mas é produto social e tem custo próprio.
- **Voz no descanso e modo assistido** (`docs/IDEIAS…` §2.6) — depende de T-035 (TTS).
- **Meta de hold** ("segure 60 s") — a SPEC-021 já a colocou fora de escopo; entra quando as
  duas modalidades tiverem meta, para não haver duas gramáticas de meta.
- Séries com peso/carga, progressão automática de meta entre treinos, histórico de treino como
  objeto.

### Critérios de aceite

1. Fixture de 15 repetições com `target_reps=15` → série termina com `reason: "target_reached"`
   no frame da 15ª rep, **não** no teto, e `rep_count == 15`.
2. Fixture que faz 10 e para, `target_reps=15`, teto = `session_max_s` → termina no teto com
   `reason: "completed"` e `rep_count == 10`. Nenhum erro, nenhuma sessão pendurada.
2b. Plano com `session_max_s = 30` (o Free de hoje) não admite modo contado — a série é
   recusada na admissão com motivo legível, não cortada no meio.
3. **Regressão do modo livre**: o corpus de polichinelo (`evalctl`) produz exatamente a mesma
   contagem de antes desta spec. Modo livre é byte-a-byte o comportamento de hoje.
4. Forjar `target_reps` ou o teto no cliente não muda nada: a meta e o teto que valem são os
   que o servidor resolveu na admissão (mesma prova da quota, SPEC-016 §4).
5. Descanso não segura slot: com os 3 slots de cloud ocupados por sessões que **terminaram** e
   cujos clientes estão em descanso, uma 4ª série é admitida.
6. Repetição executada durante o descanso não aparece em `SessionResult` nenhum.
7. Gesto: fixture com os dois pulsos acima dos ombros por 1 s dispara o início; 0,5 s não
   dispara. Em modo cloud o gesto não é oferecido e o toque/temporizador inicia a série.
8. Relatório de série contada mostra tempo até a meta; de série livre mostra reps na janela;
   nenhuma tela mostra "tempo até a meta" para série livre (honestidade de UI).
9. `session.started` sem `set_index`/`set_total`/`target_reps` (evento anterior a esta spec, ou
   replay do stream gravado) abre a sessão nos defaults — não recusa.
10. Replay do stream reproduz o mesmo `SessionResult` (promessa da SPEC-010 intacta).
11. Cadência semanal é derivação pura: apagar o cache e recomputar dá o mesmo número.

## Fase Evolução

- Circuito na UI + integração com o gerador da SPEC-022 (incluindo "quanto tempo você tem").
- Desafio assíncrono no modo livre (mandar a marca, o outro tenta bater).
- Progressão automática: se a pessoa bate a meta com folga duas vezes, sugerir subir.
- Voz no descanso ("faltam 10 segundos"), modo assistido.
- Descanso adaptativo por frequência cardíaca declarada ou por queda de cadência dentro da série.
- Meta de hold, unificando a gramática de meta entre as duas modalidades.

## Eventos (consome / produz)

**Nenhum evento novo.** Campos aditivos em `session.started` (`set_mode`, `target_reps`,
`set_index`, `set_total`, todos com default que reproduz o comportamento de hoje) e um valor
novo em `SessionEndReason`. Consome `pose.frame`, `rep.detected`; produz `session.completed`
com a razão nova.

`PROTOCOL_VERSION` **não sobe**, seguindo o precedente e o teste da SPEC-021 (nenhum produtor
ou consumidor existente precisa mudar para continuar correto). Uma ressalva honesta, porque o
caso não é idêntico ao da 021: lá o aditivo era um **tipo** de evento, que consumidor antigo
ignora; aqui é um **valor novo num enum existente**, e um `_as_enum` estrito o recusaria. A
direção do risco é que salva — `target_reached` só passa a ser *produzido* depois do deploy, e
replay de stream antigo jamais o contém. Cliente e report-builder sobem juntos. Se algum dia um
consumidor for versionado separadamente, esta linha vira dívida e precisa ser revisitada.

## Notas técnicas

- **Quem conta é o worker, sempre.** O cliente desenha `7/15` a partir de `rep.detected`, mas
  quem decide que a série acabou é o analysis-worker — mesma razão pela qual o timer dos 30 s é
  autoridade do servidor (SPEC-009) e pela qual o countdown segura a contagem no worker e não
  na animação (T-049).
- **O teto conta por `ts` de frame**, não por relógio de parede nem por contagem de frames
  (lição da T-084, e mesma regra do relógio de hold da SPEC-021).
- A baseline (SPEC-004) é medida **por série**, porque cada série é uma sessão. Isso é
  desejável: a pessoa se reposiciona no descanso, e reaproveitar a baseline anterior seria
  medir o corpo onde ele não está mais.
- O `duration_ms` do relatório já mistura dois relógios (Descoberta `[A/T-078]`). Com duração
  variável esse defeito deixa de ser cosmético — **T-078 vira pré-requisito do modo contado**,
  porque o "tempo até a meta" é justamente o número que ele erra.
- Custo na VPS: modo contado alonga a sessão média, o que reduz a vazão de sessões cloud por
  hora. Em edge (o padrão, sem limite na Fase Inicial) o custo é zero. O teto de plano é
  também a alavanca de capacidade, e é por isso que ele mora no `Plan`.
