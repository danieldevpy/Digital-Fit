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
