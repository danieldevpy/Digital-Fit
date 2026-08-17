# Deploy — VPS única, atrás do seu nginx

Dois ambientes, dois arquivos, sem sobreposição:

| | dev (local) | produção (VPS) |
|---|---|---|
| arquivo | `docker-compose.yml` | `docker-compose.prod.yml` |
| comando | `docker compose up` | `./scripts/prod.sh up` |
| projeto docker | `digital-fit` | `digital-fit-prod` |
| `api` | `runserver` (autoreload) | `gunicorn`, 3 workers |
| `web` | dev server do Vite | build estático servido por nginx |
| código | bind mount do host | dentro da imagem |
| `redis` / `postgres` | publicados no host | só na rede interna |
| `DJANGO_DEBUG` | `true` | `false` |

O de produção é **autônomo**, não um override do de dev. Um override herdaria bind mounts
e `runserver` calados, e isso só apareceria em produção.

## Por que isso existe

`getUserMedia` só funciona em [contexto seguro][mdn]. `localhost` conta como seguro;
`http://192.168.0.10` não. Ou seja: **não dá para testar no celular pela rede local** — a
câmera nunca abre. Um domínio com HTTPS de verdade é o caminho mais curto para validar a
sessão em um telefone, que é o alvo da SPEC-013.

[mdn]: https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts

## Um domínio, três portas

Tudo sai pelo mesmo host. Isso não é preferência estética: same-origin elimina CORS
inteiramente e faz o `wss://` sair do mesmo domínio do `https://` — os dois lugares onde
esse tipo de deploy costuma quebrar.

```
                    ┌───────────────────────────────┐
  celular ──HTTPS──►│  nginx (seu)  treino.dominio  │
                    └───────────────────────────────┘
                        │            │            │
              /         │  /api/     │  /ws/      │
                        ▼            ▼            ▼
                  127.0.0.1:8080  :8000        :8001
                     web           api         gateway
                   (estático)   (gunicorn)    (uvicorn)
                                     │            │
                                     └──── redis ─┴──── analysis-worker
                                           postgres      (rede interna, sem porta no host)
```

As portas ficam em `127.0.0.1` por padrão: nada é alcançável de fora sem passar pelo seu
nginx. Na Fase 0 **a API não tem autenticação** — se mudar `BIND_ADDR` para `0.0.0.0`,
proteja com firewall.

## Passo a passo

Na VPS, com Docker e o repositório já clonados:

```bash
cp .env.prod.example .env.prod
nano .env.prod              # só o DOMAIN é obrigatório decidir
./scripts/prod.sh secrets   # gera os três segredos nos campos vazios
./scripts/prod.sh up        # build + migrate + start
```

O `DOMAIN` é a única fonte de verdade. O script deriva dele:

| derivada | valor |
|---|---|
| `VITE_API_URL` | `https://<DOMAIN>` |
| `GATEWAY_WS_URL` | `wss://<DOMAIN>` |
| `DJANGO_ALLOWED_HOSTS` | `<DOMAIN>` |
| `CORS_ALLOWED_ORIGINS` | `https://<DOMAIN>` |

Quatro variáveis derivadas de uma. Mantidas à mão, elas divergem em silêncio — e um cliente
falando com um host enquanto o WebSocket fala com outro é um bug que só aparece no celular,
longe do log.

Depois, o nginx:

```bash
./scripts/prod.sh nginx     # server block de referência, já com o seu domínio
```

Cole, ajuste, recarregue, rode o certbot. O trecho que **não** pode ser simplificado é o
`/ws/`: sem os headers de `Upgrade`/`Connection`, o WebSocket vira um GET comum, o handshake
falha, e o cliente mostra só "sem conexão" sem nenhuma pista.

## Compressão dos assets de pose

O primeiro acesso baixa o runtime de visão computacional, e ele é grande. O `web-nginx.conf`
comprime o `.wasm` (T-070) — medido na própria imagem `nginx:1.27-alpine`:

| asset | sem gzip | com gzip |
|---|---|---|
| `vision_wasm_internal.wasm` | 11,0 MB | **3,2 MB** |
| `pose_landmarker_lite.task` | 5,5 MB | fica fora (5,5 → 4,7 não paga a CPU) |
| **total do primeiro acesso** | 17,3 MB | **8,7 MB** |

Duas diretivas, nesta ordem: `gzip_static on` serve `arquivo.gz` pronto quando ele existe (zero
CPU por requisição) e `gzip on` comprime na hora quando não existe. Hoje não há passo de build
gerando os `.gz`, então vale o segundo caminho — que funciona, só custa CPU. Gerar os `.gz` no
`npm run setup` é a otimização seguinte e não exige mexer no nginx de novo.

### A armadilha: `gzip_http_version` × `proxy_pass`

Duas linhas do `web-nginx.conf` existem só por causa do seu nginx na frente, e **sem elas a
compressão simplesmente não acontece em produção**, mesmo com `gzip on` e o tipo certo em
`gzip_types`:

```nginx
gzip_http_version 1.0;
gzip_proxied any;
```

Por quê: `gzip_http_version` vale **1.1** por padrão, e `proxy_pass` conversa com o upstream em
**HTTP/1.0** por padrão. O nginx do container então recusa comprimir tudo que chega pelo proxy —
não só o `.wasm`, também o CSS e o JS. Medido, com o mesmo arquivo e a mesma config:

| requisição ao container | resposta |
|---|---|
| HTTP/1.1 direto | `Content-Encoding: gzip`, 3,2 MB |
| HTTP/1.0 (o que o proxy faz) | sem compressão, 11.532.084 bytes |

Esse número é exatamente o que aparecia no waterfall do celular — foi assim que o problema foi
encontrado. `gzip_proxied any` cobre o caso vizinho: com o padrão `off`, nginx não comprime
requisição que traz o cabeçalho `Via`, que é o que surge quando um CDN entra na frente.

Alternativa equivalente, do seu lado: `proxy_http_version 1.1;` no `location /`. Vale a pena de
todo modo (habilita keepalive com o upstream), mas **não é necessária** — o conserto no container
cobre qualquer proxy.

Se preferir comprimir no **seu** nginx em vez do do container, aí lembre de `gzip_proxied any;`
lá: por padrão o nginx não comprime resposta que veio de `proxy_pass`, e `gzip on` sozinho no
server block não faz nada para conteúdo proxiado.

### Por quanto tempo o cache vale

Quatro políticas diferentes, medidas nos cabeçalhos que o container devolve:

| caminho | `Cache-Control` | duração |
|---|---|---|
| `/wasm/`, `/models/` | `max-age=3600, public` | 1 hora |
| `/assets/` (JS/CSS do bundle) | `max-age=31536000, public, immutable` | 1 ano, sem revalidar |
| `index.html`, `/app/index.html` | `no-cache` | revalida sempre |
| `/pose-assets.json` | nenhum | heurística do navegador |

**"1 hora" não significa "baixa de novo em 1 hora".** Passado o prazo, o navegador manda uma
requisição condicional com o `ETag` e recebe `304` com **0 bytes** (verificado, com gzip ligado):
o arquivo no aparelho continua valendo e o custo é um round trip. Na prática os 16,5 MB são
baixados **uma vez por aparelho**.

O que faz baixar tudo de novo, de verdade: aba anônima (não persiste, por design), despejo do
cache de disco (LRU, sob pressão), limpar dados de navegação ou `Ctrl+Shift+R`, e um deploy que
troque o arquivo — este último sendo o comportamento correto, não desperdício.

**Por que 1 hora e não 1 ano:** o `.wasm` e o `.task` não têm hash de conteúdo no nome. Com
`immutable` de um ano, atualizar o `@mediapipe/tasks-vision` deixaria aparelhos com o binário
velho por um ano, sem forma de invalidar. O `/assets/` pode ser `immutable` justamente porque o
Vite põe o hash no nome do arquivo, e build novo gera nome novo.

### Por que a compressão também conserta o cache

Sintoma relatado: recarregar a página baixava o WASM de novo. Não era header de cache — o
servidor está certo, e a revalidação condicional devolve `304` com 0 bytes (verificado).

A causa é o tamanho. O cache de disco do Chromium recusa entradas acima de uma fração do tamanho
total do cache, e 11,5 MB passa desse limite. A prova está no próprio waterfall: com **as mesmas
diretivas de cache** (é o mesmo bloco `location`) e na mesma visita, o modelo de 5,5 MB voltava
de `disk cache` em 15 ms enquanto o WASM de 11,5 MB era baixado inteiro toda vez.

Comprimido, o WASM vira 3,2 MB, cabe no limite e passa a ser guardado. É por isso que ligar o
gzip não é só "primeiro acesso mais rápido": é o que faz existir um segundo acesso barato.

Conferir em produção:

```bash
curl -s -H 'Accept-Encoding: gzip' -o /dev/null -D - \
  https://SEU-DOMINIO/wasm/vision_wasm_internal.wasm | grep -i 'content-encoding\|content-length'
```

Esperado: `content-encoding: gzip`. Se não aparecer, a imagem do `web` não foi reconstruída —
a config entra no container em build time, então precisa de `./scripts/prod.sh up`, não restart.

## SITE e APP: um artefato, duas fronteiras

Desde a T-067 o cliente são **dois** SPAs no mesmo build:

| bundle | conteúdo | onde responde |
|---|---|---|
| site | landing e Sobre | `/` |
| app | escolha, guia, pré-config, treino, progresso, analytics, conta | `/app/` |

No deploy padrão isso já funciona sem configurar nada: quem separa é o nginx **de dentro** do
container (`docker/web-nginx.conf`), e os links de um lado para o outro usam caminho relativo.

Para separar por subdomínio (`site.dominio` | `app.dominio`), preencha no `.env.prod`:

```bash
SITE_DOMAIN=site.seudominio.com.br
APP_DOMAIN=app.seudominio.com.br
```

e rode `./scripts/prod.sh up` (o bundle **precisa** ser reconstruído: as origens são `VITE_*`,
gravadas em build time) seguido de `./scripts/prod.sh nginx`, que passa a imprimir os dois
server blocks novos. Três coisas que essa mudança arrasta, e que o script resolve por você:

1. **`ALLOWED_HOSTS` e CORS** ganham os dois hosts. Sem isso o app num host novo bate numa API
   que recusa o `Host` — e o sintoma no celular é só "sem conexão".
2. **A raiz do host do app** é mapeada para `/app/index.html`, e só ela. Mapear o host inteiro
   para `/app/` faria o navegador pedir `/app/assets/…` (o HTML referencia `/assets/…` em
   caminho absoluto) e tomar 404.
3. **API e WebSocket continuam no host principal** — é o que está gravado no bundle como
   `VITE_API_URL`. Não duplique `/api` e `/ws` no server block do app.

A conta fica no app, não no site: o token vive no `localStorage`, que é por origem, então
"Entrar" no site é um link para `app.dominio/#/entrar`. Um login no host errado não valeria
no outro — e um "Entrar" que às vezes funciona é pior que um que só encaminha.

### Se alguma porta já estiver ocupada

Comum numa VPS que já roda outras coisas — `8000` costuma estar tomada. O `up` detecta isso
antes de buildar e mostra quem está segurando:

```
porta(s) ja em uso em 127.0.0.1:
  api quer a porta 8000
```

Escolha outras em `.env.prod` (`WEB_PORT`, `API_PORT`, `GATEWAY_PORT`) e rode de novo. Não há
o que pesar na escolha: essas portas só existem entre o seu nginx e o Docker, nunca aparecem
para o usuário, e o `./scripts/prod.sh nginx` já imprime o `proxy_pass` com os valores novos.

## Verificando o deploy

```bash
curl https://SEU-DOMINIO/healthz    # {"status":"ok"}
curl https://SEU-DOMINIO/readyz     # postgres e redis "ok"
```

E o teste de fumaça de verdade, que exercita admissão + WebSocket + contagem de reps contra
o ambiente real (envia polichinelos sintéticos e confere o que o servidor conta):

```bash
cd web && DIGITALFIT_E2E=1 VITE_API_URL=https://SEU-DOMINIO npm run e2e
```

> Esse E2E **não** roda contra a stack de produção por `127.0.0.1`: `ALLOWED_HOSTS` só aceita
> o domínio, e a resposta é `400`. Isso é o controle funcionando, não um defeito.

Por fim, o que motivou tudo isto: abra `https://SEU-DOMINIO` no celular e faça 30 segundos de
polichinelo (T-014).

## Operação

```bash
./scripts/prod.sh ps
./scripts/prod.sh logs                   # tudo
./scripts/prod.sh logs analysis-worker   # um serviço
./scripts/prod.sh stop                   # para sem remover
./scripts/prod.sh start                  # religa
./scripts/prod.sh restart gateway
./scripts/prod.sh down                   # remove containers e rede; o volume do postgres fica
```

Use sempre o script, **não** `docker compose -f docker-compose.prod.yml` direto. As quatro
URLs públicas são derivadas do `DOMAIN` dentro dele, e o compose se recusa a interpolar sem
elas:

```
required variable CORS_ALLOWED_ORIGINS is missing a value:
derivado do DOMAIN — use ./scripts/prod.sh em vez de docker compose direto
```

Isso é deliberado. A alternativa seria dar um default vazio a essas variáveis, e aí um erro de
configuração viraria um deploy silenciosamente errado — `ALLOWED_HOSTS` vazio, bundle apontando
para `localhost`. Falhar alto é melhor.

`ps`, `logs`, `stop`, `start`, `restart` e `down` funcionam mesmo com o `.env.prod` incompleto —
a hora em que mais se precisa derrubar uma stack é justamente quando a configuração está
quebrada.

Atualizar depois de um `git pull`: `./scripts/prod.sh up` de novo. Ele sempre reconstrói,
porque `VITE_API_URL` é gravada no bundle em build time e não dá para trocar por environment.

## Painel de operação (SPEC-018)

**Vem desligado.** Ligar é um comando:

```bash
./scripts/prod.sh painel on
```

Ele escreve `DJANGO_ENABLE_ADMIN=1` no `.env.prod`, **recria o container da api** e confere que
a rota respondeu. Os três passos são um só de propósito — separados, o do meio é o que cai.

> **`restart` não recarrega o `.env.prod`.** `docker compose restart` reinicia o processo com o
> ambiente que o container já tinha: editar o arquivo e dar `restart` não muda nada, e não há
> erro nenhum para perceber. Foi essa a armadilha que fez o painel parecer um problema de
> nginx. Só `up` — ou o `painel on` acima, que recria só a api e não rebuilda o bundle — leva o
> valor novo ao processo.

Para trocar o caminho, edite o `.env.prod` e rode `./scripts/prod.sh painel on` de novo:

```bash
DJANGO_ADMIN_PATH=um-caminho-so-seu/      # troque: /admin e /painel são os dois primeiros
```

### Quando ele não abre, `./scripts/prod.sh painel` diz por quê

Sem argumento, o comando é só diagnóstico. Ele imprime o que está escrito no `.env.prod`, o que
o **container está de fato rodando** (é aqui que a divergência acima aparece) e os dois códigos
HTTP que separam os dois modos de falha — `404` do próprio Django (rota desmontada) contra `200`
do container do web (a landing, por falta do `location`):

```
no .env.prod     DJANGO_ENABLE_ADMIN=1
no container     DJANGO_ENABLE_ADMIN=0
o arquivo e o container DISCORDAM
'restart' nao recarrega ambiente — recria com: ./scripts/prod.sh painel on
```

`./scripts/prod.sh painel off` desliga pelo mesmo caminho.

`CSRF_TRUSTED_ORIGINS` **é derivado do `DOMAIN`** e só precisa ser preenchido se o painel for
responder em outro host. Deixado a mão, era a variável que ninguém descobria ter esquecido até
o POST do login voltar `403` — atrás do proxy que termina TLS o Django compara o header
`Origin` com essa lista.

### O nginx precisa de dois `location` — e é aqui que isso costuma falhar

Rode `./scripts/prod.sh nginx` de novo depois de ligar o painel: o bloco impresso passou a
trazer os dois. Sem eles, tudo que não é `/api/`, `/healthz`, `/readyz` e `/ws/` cai no
`location /` — ou seja, no **container do web**, que devolve o `index.html` do SPA para
qualquer caminho desconhecido. Os dois sintomas:

| falta | o que acontece |
|---|---|
| `location /um-caminho-so-seu/` | o painel "não existe": a URL abre a **landing do produto**, com status `200`. Não é 404, então não parece erro de rota |
| `location /static/` | o painel abre inteiro, funcional e **sem estilo nenhum** — o navegador pediu CSS e recebeu `text/html`, e recusa aplicá-lo. É o sintoma que mais se confunde com "o tema não instalou" |

`/static/` não colide com o cliente: o build do Vite publica em `/assets/`.

Depois, a primeira conta de operador — não há painel onde criá-la:

```bash
./scripts/prod.sh exec api python manage.py createsuperuser
```

Ela nasce com as duas flags: painel (`is_staff`) e ferramentas de diagnóstico do cliente
(`is_admin`). Para as próximas contas, o painel concede a segunda, mas **não** a primeira:

```bash
./scripts/prod.sh exec api python manage.py admin_tools alguem@exemplo.com --panel-on
```

Conceder acesso ao painel é a única escalada que o painel não faz sozinho — quem entra por lá
lê conta e sessão de todo mundo, e um operador comprometido não deve conseguir criar outro.

Três coisas que valem saber:

- **O gateway (`:8001`) nunca serve o painel**, mesmo que a variável vaze para ele: a trava é
  no processo (`server/core/admin_gate.py`), não na configuração.
- **O CSS sai do próprio container** (whitenoise + `collectstatic` no build da imagem). Você
  não precisa servir arquivo nenhum, mas *precisa* rotear `/static/` até a api — é o bloco da
  tabela acima. O `./scripts/prod.sh nginx` já o imprime.
- **Exponha-o com cuidado.** Restringir por IP é barato e vale a pena — as duas linhas já vêm
  comentadas no `location` do painel que o script imprime:

  ```nginx
  allow 203.0.113.10;   # seu IP
  deny all;
  ```

### Conferindo depois do deploy

`./scripts/prod.sh painel` já faz as duas conferências abaixo e interpreta o resultado. A mão,
quando você estiver fora da VPS:

```bash
curl -s -o /dev/null -w '%{http_code}\n' https://SEU-DOMINIO/um-caminho-so-seu/
# 302 (manda para o login) — o painel está no ar
# 200 → você está vendo a landing: falta o `location` no nginx
# 404 → o nginx está certo e quem respondeu foi o Django: o painel está DESLIGADO no
#       container. Confirme pelo cabeçalho — só o Django manda `X-Frame-Options: DENY`
#       junto de um 404 aqui; o do nginx vem sem ele:
#       curl -sI https://SEU-DOMINIO/um-caminho-so-seu/ | grep -i x-frame-options

curl -s -o /dev/null -w '%{http_code} %{content_type}\n' \
  https://SEU-DOMINIO/static/painel/digitalfit.css
# 200 text/css — se vier text/html, falta o location /static/ e o painel abrirá sem estilo
```

### O tema

O painel usa **django-jazzmin** (AdminLTE 4 / Bootstrap 5) repintado com os tokens da SPEC-014
— a mesma paleta, as mesmas fontes e o mesmo raio de canto do cliente. O que é dado
(rótulos, ícones, ordem do menu) fica em `server/core/admin_theme.py`; o que é folha de estilo
fica em `server/api/static/painel/digitalfit.css`. Trocar de tema não exige tocar em
`api/admin.py`, e mexer no `api/admin.py` não exige tocar no tema.

Para abrir o painel **na sua máquina**, sem Postgres e sem Docker:

```bash
cd server && env PYTHONPATH=.. DJANGO_ENABLE_ADMIN=1 DJANGO_DB_SQLITE=1 \
  DJANGO_DB_SQLITE_PATH=../.painel-dev.sqlite3 DJANGO_CACHE_LOCMEM=1 \
  CHANNEL_LAYER_IN_MEMORY=1 ../.venv/bin/python manage.py migrate
```

Depois `createsuperuser` com as mesmas variáveis e `runserver 8010` — é exatamente o que o
alvo `painel` do `.claude/launch.json` faz.

## Limites conhecidos desta configuração

- **`analysis-worker` não escala.** A FSM guarda estado por sessão em memória, e o consumer
  group do Redis distribuiria frames da mesma sessão entre réplicas — a contagem quebraria de
  um jeito que só aparece sob carga. `replicas: 1` está fixo no compose de propósito.
- **Reiniciar o worker perde as sessões em voo.** Sem snapshot de estado (T-031), quem estava
  treinando naquele instante perde a contagem.
- **Sem backup do Postgres.** É a T-026. Hoje o volume `postgres-data` é tudo que existe.
- **Sem quotas, sem auth, sem fila** (T-017/T-022/T-025). Qualquer um que alcance a URL abre
  sessão. Enquanto for um domínio que só você conhece, tudo bem; público, não.
- **Fase 0 é edge only.** Pedido de modo cloud volta `denied_cloud` — o `pose-worker` é a
  T-016. Aparelho fraco não tem para onde cair.
