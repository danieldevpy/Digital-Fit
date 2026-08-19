#!/usr/bin/env bash
#
# Digital Fit — sobe a stack de producao na VPS e expoe as portas para o seu nginx.
#
#   ./scripts/prod.sh secrets   # preenche os segredos vazios do .env.prod
#   ./scripts/prod.sh up        # build + migrate + start
#   ./scripts/prod.sh nginx     # imprime o server block de referencia
#   ./scripts/prod.sh painel    # diz por que o painel nao abre; `painel on` liga e recria
#   ./scripts/prod.sh modelo    # baixa o modelo de pose e religa o pose-worker
#   ./scripts/prod.sh ps | logs | down | restart
#
# TLS, dominio e o nginx da frente sao seus. Este script cuida do que roda atras deles.
set -euo pipefail

RAIZ="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$RAIZ/docker-compose.prod.yml"
ENV_FILE="$RAIZ/.env.prod"

vermelho() { printf '\033[31m%s\033[0m\n' "$*" >&2; }
verde()    { printf '\033[32m%s\033[0m\n' "$*"; }
amarelo()  { printf '\033[33m%s\033[0m\n' "$*"; }

morre() { vermelho "erro: $*"; exit 1; }

compose() { docker compose -f "$COMPOSE_FILE" "$@"; }

# --------------------------------------------------------------------------------------
# Segredos
# --------------------------------------------------------------------------------------

gera_segredo() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -base64 48 | tr -d '\n=+/' | cut -c1-50
  else
    head -c 48 /dev/urandom | base64 | tr -d '\n=+/' | cut -c1-50
  fi
}

# Le uma chave do .env.prod SEM sourcear o arquivo. Serve para comparar o que esta ESCRITO
# com o que o container esta rodando — os dois divergem com facilidade (ver `cmd_painel`), e
# quem ja sourceou perdeu justamente essa diferenca.
valor_no_arquivo() {
  [[ -f "$ENV_FILE" ]] || return 0
  sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1
}

# Escreve chave=valor no .env.prod, trocando a linha existente ou acrescentando. Diferente do
# `cmd_secrets`, que so preenche vazio: aqui o objetivo e mudar um valor ja escrito.
define_no_arquivo() {
  local chave="$1" valor="$2"
  [[ -f "$ENV_FILE" ]] || morre "$ENV_FILE nao existe. Rode: cp .env.prod.example .env.prod"
  if grep -qE "^${chave}=" "$ENV_FILE"; then
    # `|` como separador: nenhum valor escrito por aqui contem `|`.
    sed -i "s|^${chave}=.*|${chave}=${valor}|" "$ENV_FILE"
  else
    printf '\n%s=%s\n' "$chave" "$valor" >> "$ENV_FILE"
  fi
}

# Preenche apenas chaves com valor VAZIO. Nunca sobrescreve um segredo existente: rotacionar
# SESSION_TOKEN_SECRET sem querer derrubaria toda sessao em voo.
cmd_secrets() {
  [[ -f "$ENV_FILE" ]] || morre "$ENV_FILE nao existe. Rode: cp .env.prod.example .env.prod"

  local mudou=0
  for chave in DJANGO_SECRET_KEY SESSION_TOKEN_SECRET JWT_SIGNING_KEY POSTGRES_PASSWORD; do
    local valor
    if grep -qE "^${chave}=$" "$ENV_FILE"; then
      valor="$(gera_segredo)"
      # `|` como separador: base64 nao produz `|`, entao nao ha o que escapar.
      sed -i "s|^${chave}=$|${chave}=${valor}|" "$ENV_FILE"
      verde "  $chave gerado"
      mudou=1
    elif ! grep -qE "^${chave}=" "$ENV_FILE"; then
      # A chave nasceu depois deste .env.prod (caso do JWT_SIGNING_KEY, SPEC-011). Acrescentar
      # e o certo: mandar o operador editar a mao so cria a chance de ele nao editar.
      valor="$(gera_segredo)"
      printf '\n%s=%s\n' "$chave" "$valor" >> "$ENV_FILE"
      verde "  $chave acrescentado"
      mudou=1
    else
      amarelo "  $chave ja tem valor — mantido"
    fi
  done

  [[ $mudou -eq 1 ]] && chmod 600 "$ENV_FILE"
  verde "pronto. Confira o DOMAIN em $ENV_FILE antes do 'up'."
}

# --------------------------------------------------------------------------------------
# Ambiente: carrega o .env.prod e DERIVA as URLs publicas a partir do DOMAIN
# --------------------------------------------------------------------------------------

# `--tolerante`: para down/ps/logs/restart, que agem sobre o nome do projeto e nao precisam
# de configuracao correta. Exigir validacao ali impediria de DERRUBAR uma stack cujo
# .env.prod ficou quebrado — exatamente a hora em que se mais precisa derrubar.
carrega_ambiente() {
  local tolerante=0
  [[ "${1:-}" == "--tolerante" ]] && tolerante=1

  if [[ -f "$ENV_FILE" ]]; then
    set -a
    # shellcheck disable=SC1090
    source "$ENV_FILE"
    set +a
  elif [[ $tolerante -eq 0 ]]; then
    morre "$ENV_FILE nao existe. Rode: cp .env.prod.example .env.prod"
  fi

  if [[ $tolerante -eq 1 ]]; then
    # Placeholders so para o compose conseguir interpolar o arquivo.
    : "${DOMAIN:=indefinido}"
    export DOMAIN
    export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-indefinido}"
    export SESSION_TOKEN_SECRET="${SESSION_TOKEN_SECRET:-indefinido}"
    export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-indefinido}"
    export VITE_API_URL="https://${DOMAIN}"
    export GATEWAY_WS_URL="wss://${DOMAIN}"
    export DJANGO_ALLOWED_HOSTS="${DOMAIN}"
    export CORS_ALLOWED_ORIGINS="https://${DOMAIN}"
    export DJANGO_ADMIN_PATH="${DJANGO_ADMIN_PATH:-painel/}"
    export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-https://${DOMAIN}}"
    return 0
  fi

  : "${DOMAIN:?DOMAIN nao definido em .env.prod}"

  [[ "$DOMAIN" == "treino.seudominio.com.br" ]] &&
    morre "DOMAIN ainda e o exemplo. Ponha o seu dominio em $ENV_FILE"
  [[ "$DOMAIN" == *"://"* ]] &&
    morre "DOMAIN vai sem esquema: use 'treino.exemplo.com', nao 'https://treino.exemplo.com'"
  [[ "$DOMAIN" == */* ]] &&
    morre "DOMAIN vai sem barra nem caminho: use apenas o host"

  for chave in DJANGO_SECRET_KEY SESSION_TOKEN_SECRET JWT_SIGNING_KEY POSTGRES_PASSWORD; do
    [[ -n "${!chave:-}" ]] || morre "$chave vazio. Rode: ./scripts/prod.sh secrets"
  done

  # Defaults de dev que jamais podem chegar a uma maquina publica.
  [[ "$DJANGO_SECRET_KEY" == dev-* ]] && morre "DJANGO_SECRET_KEY e o valor de dev"
  [[ "$SESSION_TOKEN_SECRET" == dev-* ]] && morre "SESSION_TOKEN_SECRET e o valor de dev"

  # As quatro derivadas. Uma fonte de verdade (DOMAIN) em vez de quatro variaveis que
  # divergem em silencio — o cliente falando com um host e o WS com outro e um bug que
  # so aparece no celular, longe do log.
  export PUBLIC_ORIGIN="https://${DOMAIN}"
  export VITE_API_URL="https://${DOMAIN}"
  export GATEWAY_WS_URL="wss://${DOMAIN}"
  export DJANGO_ALLOWED_HOSTS="${DOMAIN}"
  export CORS_ALLOWED_ORIGINS="https://${DOMAIN}"

  # Fronteira SITE|APP (T-067). Por padrao os dois vivem no MESMO dominio, em caminhos
  # diferentes (`/` e `/app/`) — e ai nao ha nada a derivar: o cliente usa os proprios
  # defaults e as variaveis ficam vazias.
  #
  # Definir SITE_DOMAIN e/ou APP_DOMAIN no .env.prod (ex.: site.exemplo.com / app.exemplo.com)
  # liga o modo subdominio: as origens completas entram no bundle e os dois hosts entram no
  # ALLOWED_HOSTS e no CORS. Sem isso, o app num host novo bateria numa API que recusa o
  # `Host` — falha que aparece como "sem conexao" no celular, sem pista do motivo.
  export VITE_SITE_URL="" VITE_APP_URL=""

  # A origem publica do SITE, sempre absoluta (T-160). Diferente da VITE_SITE_URL acima: aquela
  # e a base dos links entre bundles e fica vazia quando o site mora em `/`; esta responde
  # "em que origem a pagina vai ser servida", que e o que `canonical` e `hreflang` exigem, e
  # existe nos dois modos de deploy. Derivada, nunca preenchida a mao.
  export VITE_SITE_ORIGIN="https://${SITE_DOMAIN:-$DOMAIN}"

  if [[ -n "${SITE_DOMAIN:-}" || -n "${APP_DOMAIN:-}" ]]; then
    local site_host="${SITE_DOMAIN:-$DOMAIN}"
    local app_host="${APP_DOMAIN:-$DOMAIN}"

    for par in "SITE_DOMAIN:$site_host" "APP_DOMAIN:$app_host"; do
      local nome="${par%%:*}" host="${par#*:}"
      [[ "$host" == *"://"* ]] && morre "$nome vai sem esquema: use 'app.exemplo.com'"
      [[ "$host" == */* ]] && morre "$nome vai sem barra nem caminho: use apenas o host"
    done

    export VITE_SITE_URL="https://${site_host}/"
    # No modo subdominio o app e a RAIZ do proprio host — quem mapeia essa raiz para
    # /app/index.html e o nginx da VPS (`./scripts/prod.sh nginx` imprime o bloco).
    export VITE_APP_URL="https://${app_host}/"

    local hosts="${DOMAIN}" origens="https://${DOMAIN}"
    for host in "$site_host" "$app_host"; do
      [[ "$host" == "$DOMAIN" ]] && continue
      [[ ",$hosts," == *",$host,"* ]] && continue
      hosts="${hosts},${host}"
      origens="${origens},https://${host}"
    done
    export DJANGO_ALLOWED_HOSTS="$hosts"
    export CORS_ALLOWED_ORIGINS="$origens"
  fi

  # Painel de operacao (SPEC-018). O caminho e normalizado aqui e nao no ponto de uso porque
  # ele e escrito a mao no .env.prod e vai parar em DOIS lugares que precisam concordar: a
  # rota do Django (`DJANGO_ADMIN_PATH`) e o `location` do nginx (`./scripts/prod.sh nginx`).
  # Uma barra a mais num deles e um 404 que ninguem consegue explicar.
  export DJANGO_ADMIN_PATH="${DJANGO_ADMIN_PATH:-painel/}"
  ADMIN_PATH="${DJANGO_ADMIN_PATH#/}"
  ADMIN_PATH="${ADMIN_PATH%/}/"
  export ADMIN_PATH

  # CSRF do painel: a QUINTA derivada do DOMAIN, pelo mesmo motivo das outras quatro.
  # Mantida a mao, ela e a unica variavel que o operador so descobre que esqueceu no momento
  # em que o POST do login volta 403 — atras do proxy que termina TLS, o Django compara o
  # header `Origin` com esta lista. Preenchida no .env.prod, o valor de la vence.
  export CSRF_TRUSTED_ORIGINS="${CSRF_TRUSTED_ORIGINS:-$CORS_ALLOWED_ORIGINS}"
}

# --------------------------------------------------------------------------------------
# Portas livres
# --------------------------------------------------------------------------------------

# Ha alguem escutando nesta porta, de um jeito que conflite com o nosso BIND_ADDR?
# Conflitam: o mesmo endereco, e os curingas (`*`, `0.0.0.0`, `[::]`) — que tomam a porta
# em todas as interfaces e portanto tambem na nossa.
porta_ocupada() {
  local porta="$1" bind="${BIND_ADDR:-127.0.0.1}"
  command -v ss >/dev/null 2>&1 || return 1  # sem `ss` nao da para checar; segue o jogo

  ss -ltnH 2>/dev/null | awk -v porta="$porta" -v bind="$bind" '
    {
      alvo = $4
      p = alvo; sub(/.*:/, "", p)              # porta = depois do ultimo ":"
      if (p != porta) next
      a = alvo; sub(/:[^:]*$/, "", a)          # endereco = antes do ultimo ":"
      if (a == bind || a == "*" || a == "0.0.0.0" || a == "[::]" || a == "::") { achou = 1 }
    }
    END { exit(achou ? 0 : 1) }
  '
}

esta_rodando() { [[ -n "$(compose ps -q --status running "$1" 2>/dev/null)" ]]; }

# Roda ANTES do build. O conflito de porta so estoura no `up`, que e o ultimo passo — sem
# isto o erro aparece depois de buildar as imagens e rodar as migrations, com a stack pela
# metade. Servico que JA esta rodando e pulado: ele e o dono legitimo da propria porta, e
# reclamar dele impediria de atualizar a stack.
verifica_portas() {
  local conflitos=()
  local pares=(
    "web:${WEB_PORT:-8080}"
    "api:${API_PORT:-8000}"
    "gateway:${GATEWAY_PORT:-8001}"
  )

  for par in "${pares[@]}"; do
    local servico="${par%%:*}" porta="${par##*:}"
    esta_rodando "$servico" && continue
    porta_ocupada "$porta" && conflitos+=("$servico:$porta")
  done

  [[ ${#conflitos[@]} -eq 0 ]] && return 0

  vermelho "porta(s) ja em uso em ${BIND_ADDR:-127.0.0.1}:"
  for c in "${conflitos[@]}"; do
    vermelho "  ${c%%:*} quer a porta ${c##*:}"
  done
  echo >&2
  echo "Quem esta segurando:" >&2
  for c in "${conflitos[@]}"; do
    ss -ltnp 2>/dev/null | grep -E "[:.]${c##*:}\b" >&2 || true
  done
  echo >&2
  amarelo "Saida: escolha portas livres em $ENV_FILE (WEB_PORT / API_PORT / GATEWAY_PORT)."
  amarelo "Elas so existem entre o nginx e o Docker, entao qualquer valor livre serve —"
  amarelo "o './scripts/prod.sh nginx' ja imprime o proxy_pass com as portas novas."
  exit 1
}

# --------------------------------------------------------------------------------------
# Modelo de pose
# --------------------------------------------------------------------------------------

MODELO="$RAIZ/eval/models/pose_landmarker_lite.task"

# O `.task` e gitignorado (5,5 MB de binario nao entram no repo) e o pose-worker o recebe
# por bind mount, nao assado na imagem. Logo: num clone novo na VPS o arquivo simplesmente
# nao existe, o Docker cria o diretorio vazio no lugar, e o pose-worker entra em crash loop.
#
# O sintoma engana. O `up` termina verde, api/gateway/web sobem, o modo edge funciona
# inteiro — so o celular que cai em cloud fica sem contagem, e a causa esta num container
# que reinicia calado fora do caminho de quem esta testando.
garante_modelo() {
  if [[ -f "$MODELO" ]] && [[ "$(stat -c%s "$MODELO" 2>/dev/null || echo 0)" -gt 1000000 ]]; then
    return 0
  fi

  [[ -e "$MODELO" ]] && amarelo "modelo de pose truncado — baixando de novo"

  command -v python3 >/dev/null 2>&1 ||
    morre "modelo de pose ausente e nao ha python3 para baixar.
Copie um pose_landmarker_lite.task para $MODELO"

  verde "==> baixando o modelo de pose (5,5 MB, so na primeira vez)"
  # Reusa o `download_model` do contrato de proposito: a URL do modelo tem UMA fonte de
  # verdade (workers/shared/pose_model.py), e edge, cloud e bancada dependem de ser o mesmo
  # arquivo. So stdlib la dentro, entao o python3 do sistema basta — sem uv, sem venv.
  PYTHONPATH="$RAIZ" python3 -c \
    'from workers.shared.pose_model import download_model; print(download_model())' ||
    morre "download do modelo falhou. Baixe manualmente para $MODELO"

  [[ "$(stat -c%s "$MODELO" 2>/dev/null || echo 0)" -gt 1000000 ]] ||
    morre "o modelo baixado saiu truncado: $MODELO"
}

# --------------------------------------------------------------------------------------
# Catalogo publico do site (T-165)
# --------------------------------------------------------------------------------------

# Escreve `web/src/site/exercicios.json` a partir do banco JA migrado, para o build do web
# pre-renderizar as paginas por exercicio.
#
# Sai pela SAIDA PADRAO e nao direto no arquivo porque, em producao, o codigo esta DENTRO da
# imagem — o repositorio do host nao esta montado no container, entao um `--out <caminho>` la
# dentro escreveria num arquivo que ninguem le. `-T` desliga o TTY para a saida nao vir com
# controle de terminal no meio do JSON.
#
# Grava em temporario e so entao move: um comando que falhe no meio nao pode deixar o arquivo
# versionado truncado, que produziria um build verde com o site sem exercicio nenhum.
exporta_catalogo_do_site() {
  local destino="${RAIZ}/web/src/site/exercicios.json"
  local temporario
  temporario="$(mktemp)"

  verde "==> catalogo do site (paginas por exercicio)"
  if compose run --rm -T api python manage.py export_site_catalog --out - > "$temporario"; then
    mv "$temporario" "$destino"
  else
    rm -f "$temporario"
    vermelho "falhou ao exportar o catalogo do site; o build usaria o retrato anterior"
    return 1
  fi
}

# --------------------------------------------------------------------------------------
# Comandos
# --------------------------------------------------------------------------------------

cmd_up() {
  carrega_ambiente
  verifica_portas
  garante_modelo

  # A ORDEM aqui mudou na T-165, e a razao e o catalogo do site.
  #
  # Antes era build de tudo -> migrate -> up. Agora o bundle do web depende de um dado que so
  # existe DEPOIS da migration: as paginas publicas por exercicio (`/exercicios/agachamento/`)
  # sao pre-renderizadas em tempo de build a partir de `web/src/site/exercicios.json`, e esse
  # arquivo e um retrato do Postgres. Buildar o web antes de migrar publicaria o catalogo do
  # deploy anterior — um exercicio novo ficaria sem pagina ate o proximo deploy, sem nada
  # acusar. Por isso: api primeiro (e a imagem que migra e exporta), depois o resto.
  verde "==> build da imagem do servidor"
  compose build api

  # `run` respeita o `depends_on: service_healthy` do api, entao redis e postgres sobem e
  # ficam saudaveis antes da migration comecar — nao ha o que esperar na mao aqui.
  verde "==> migrations"
  compose run --rm api python manage.py migrate --noinput

  exporta_catalogo_do_site

  verde "==> build (o web e reconstruido sempre: VITE_API_URL entra no bundle)"
  compose build

  verde "==> subindo tudo"
  compose up -d

  echo
  compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
  echo
  verde "no ar em ${PUBLIC_ORIGIN} (assim que o nginx apontar para as portas abaixo)"
  echo "  web      -> ${BIND_ADDR:-127.0.0.1}:${WEB_PORT:-8080}"
  echo "  api      -> ${BIND_ADDR:-127.0.0.1}:${API_PORT:-8000}"
  echo "  gateway  -> ${BIND_ADDR:-127.0.0.1}:${GATEWAY_PORT:-8001}  (WebSocket)"
  echo
  amarelo "server block de referencia: ./scripts/prod.sh nginx"
}

# Plano de uma conta, enquanto o checkout nao existe (T-036). A regra inteira mora no
# `manage.py plano`, que e testado; aqui em cima so ha o caminho ate o container certo.
#
# Sem argumento nenhum imprime a ajuda do proprio comando, entao quem esqueceu a sintaxe
# descobre no lugar onde esta, sem abrir arquivo.
cmd_plano() {
  carrega_ambiente --tolerante
  shift || true
  esta_rodando api || morre "a api nao esta de pe — rode './scripts/prod.sh up' antes"
  if [[ $# -eq 0 ]]; then
    compose exec -T api python manage.py plano --help
    return
  fi
  compose exec -T api python manage.py plano "$@"
}

# O `exec` que o README e o docs/DEPLOY.md prometem em seis lugares — inclusive o
# `createsuperuser`, que e o UNICO jeito de criar a primeira conta do painel. Ficou anos fora do
# `case` la embaixo, entao a instrucao documentada caia no "comando desconhecido".
#
# Sem `-T`, ao contrario do `cmd_plano`: o `createsuperuser` pergunta a senha, e sem TTY ele
# falha no meio. Quem precisa de pipe passa o `-T` como primeiro argumento; ele so atravessa.
cmd_exec() {
  carrega_ambiente --tolerante
  shift || true
  [[ $# -ge 2 ]] || morre "uso: ./scripts/prod.sh exec <servico> <comando...>
exemplo: ./scripts/prod.sh exec api python manage.py createsuperuser"
  compose exec "$@"
}

# --------------------------------------------------------------------------------------
# Painel de operacao (SPEC-018)
# --------------------------------------------------------------------------------------

# Status do painel na porta LOCAL da api, sem passar pelo nginx. O header `Host` e
# obrigatorio: ALLOWED_HOSTS em producao e so o DOMAIN, e sem ele a resposta e 400
# (DisallowedHost) para qualquer caminho — o mesmo motivo do healthcheck do compose.
codigo_painel_local() {
  local bind="${BIND_ADDR:-127.0.0.1}"
  # 0.0.0.0 nao e endereco de destino; quem escuta nele atende em 127.0.0.1.
  [[ "$bind" == "0.0.0.0" || "$bind" == "::" ]] && bind="127.0.0.1"
  curl -s -o /dev/null -w '%{http_code}' --max-time 5 \
    -H "Host: ${DOMAIN}" "http://${bind}:${API_PORT:-8000}/${ADMIN_PATH}" 2>/dev/null || echo 000
}

codigo_painel_publico() {
  curl -s -o /dev/null -w '%{http_code}' --max-time 10 \
    "https://${DOMAIN}/${ADMIN_PATH}" 2>/dev/null || echo 000
}

# O diagnostico que faltava. O painel some por DOIS motivos independentes, e os sintomas se
# parecem o bastante para trocar um pelo outro — foi assim que uma investigacao inteira foi
# gasta mexendo no nginx enquanto o problema estava do lado do Django:
#
#   - Django: a rota so existe com DJANGO_ENABLE_ADMIN ligado. Desligado, quem responde e o
#     404 do PROPRIO Django (`text/html; charset=utf-8`, com os headers do SecurityMiddleware).
#   - nginx: sem o `location`, a URL cai no container do web e volta a LANDING com 200.
#
# Comparar os dois codigos separa os casos sem adivinhacao. E a terceira coluna — o que o
# container esta REALMENTE rodando — pega a armadilha que nenhuma das duas explica sozinha.
cmd_painel_status() {
  local arquivo container local_ publico
  arquivo="$(valor_no_arquivo DJANGO_ENABLE_ADMIN)"
  container=""
  if esta_rodando api; then
    container="$(compose exec -T api printenv DJANGO_ENABLE_ADMIN 2>/dev/null | tr -d '\r\n')" || true
  fi

  echo "caminho          /${ADMIN_PATH}"
  echo "no .env.prod     DJANGO_ENABLE_ADMIN=${arquivo:-<ausente>}"
  if ! esta_rodando api; then
    echo "no container     (api parada)"
    amarelo "a api nao esta de pe — './scripts/prod.sh up'"
    return 0
  fi
  echo "no container     DJANGO_ENABLE_ADMIN=${container:-<ausente>}"

  # ESTA e a armadilha. `docker compose restart` reinicia o processo com o ambiente que o
  # container ja tinha: editar o .env.prod e dar `restart` nao muda nada, e nao ha erro
  # nenhum para perceber. So `up` (ou o `painel on` daqui) recria o container com o valor novo.
  if [[ "${arquivo:-}" != "${container:-}" ]]; then
    vermelho "o arquivo e o container DISCORDAM"
    amarelo "'restart' nao recarrega ambiente — recria com: ./scripts/prod.sh painel on"
  fi

  command -v curl >/dev/null 2>&1 || { amarelo "sem curl: pulando a verificacao HTTP"; return 0; }

  local_="$(codigo_painel_local)"
  publico="$(codigo_painel_publico)"
  echo "api local        $local_"
  echo "publico          $publico   (https://${DOMAIN}/${ADMIN_PATH})"
  echo

  case "$local_" in
    000) vermelho "a api nao respondeu em ${BIND_ADDR:-127.0.0.1}:${API_PORT:-8000}" ; return 0 ;;
    404) vermelho "o Django nao monta a rota: o painel esta DESLIGADO neste container"
         amarelo "  ./scripts/prod.sh painel on" ;;
    400) vermelho "400 na porta local: o DOMAIN do .env.prod nao bate com o ALLOWED_HOSTS" ;;
    *)   verde "o Django serve o painel na porta local ($local_)" ;;
  esac

  case "$publico" in
    000) vermelho "o dominio nao respondeu (DNS, TLS ou nginx fora do ar)" ;;
    200) vermelho "publico devolve 200: isso e a LANDING, nao o painel"
         amarelo "  falta o 'location /${ADMIN_PATH}' no nginx — ./scripts/prod.sh nginx" ;;
    404) [[ "$local_" == "404" ]] ||
           amarelo "publico 404 com a api local ok: confira o proxy_pass do location" ;;
    *)   [[ "$local_" == "404" ]] || verde "publico responde $publico — painel acessivel" ;;
  esac
}

# Liga (ou desliga) o painel e RECRIA a api. O `up -d --force-recreate --no-deps api` e o
# ponto inteiro: e o que faz o valor novo entrar no processo sem um `up` completo, que
# rebuildaria o bundle do Vite (minutos) so para trocar uma variavel de ambiente.
cmd_painel_liga() {
  local ligado="$1"

  esta_rodando api || morre "a api nao esta de pe — rode './scripts/prod.sh up' antes"

  define_no_arquivo DJANGO_ENABLE_ADMIN "$ligado"
  # Reflete no ambiente do processo: `carrega_ambiente` ja rodou e sourceou o valor ANTIGO.
  export DJANGO_ENABLE_ADMIN="$ligado"

  verde "==> DJANGO_ENABLE_ADMIN=${ligado} — recriando a api"
  compose up -d --force-recreate --no-deps api

  if [[ "$ligado" == "0" ]]; then
    verde "painel desligado."
    return 0
  fi

  command -v curl >/dev/null 2>&1 || {
    amarelo "sem curl: confira a mao em https://${DOMAIN}/${ADMIN_PATH}"
    return 0
  }

  # A api acabou de subir; o gunicorn leva um instante para aceitar conexao.
  local codigo="000"
  for _ in 1 2 3 4 5 6 7 8 9 10; do
    codigo="$(codigo_painel_local)"
    [[ "$codigo" != "000" ]] && break
    sleep 1
  done

  echo
  case "$codigo" in
    302|200) verde "painel no ar: https://${DOMAIN}/${ADMIN_PATH}" ;;
    404) vermelho "ainda 404 na porta local — a variavel nao chegou ao processo"
         amarelo "rode './scripts/prod.sh painel' para o diagnostico completo"; return 1 ;;
    *)   amarelo "a api respondeu $codigo na porta local; veja './scripts/prod.sh painel'" ;;
  esac

  echo
  amarelo "falta o 'location /${ADMIN_PATH}' e o 'location /static/' no seu nginx?"
  amarelo "  ./scripts/prod.sh nginx"
  amarelo "primeira conta de operador (nao ha painel onde cria-la):"
  amarelo "  ./scripts/prod.sh exec api python manage.py createsuperuser"
}

cmd_painel() {
  carrega_ambiente
  shift || true
  case "${1:-status}" in
    status|check|"") cmd_painel_status ;;
    on|liga)  cmd_painel_liga 1 ;;
    off|desliga) cmd_painel_liga 0 ;;
    *) morre "uso: ./scripts/prod.sh painel [status|on|off]" ;;
  esac
}

cmd_down()    { carrega_ambiente --tolerante; compose down; }
cmd_ps()      { carrega_ambiente --tolerante; compose ps; }
cmd_logs()    { carrega_ambiente --tolerante; shift || true; compose logs -f --tail 100 "$@"; }
cmd_restart() { carrega_ambiente --tolerante; shift || true; compose restart "$@"; }
# `stop` para os containers sem remover nada (o `down` remove containers e rede).
cmd_stop()    { carrega_ambiente --tolerante; shift || true; compose stop "$@"; }
cmd_start()   { carrega_ambiente --tolerante; shift || true; compose start "$@"; }

# Conserto de uma stack ja no ar que subiu sem o modelo: baixa e religa so o pose-worker.
# Sem isto o caminho seria um `up` inteiro — rebuild de tudo para trocar um arquivo montado.
cmd_modelo() {
  carrega_ambiente --tolerante
  garante_modelo
  verde "modelo em $MODELO"
  if esta_rodando pose-worker || [[ -n "$(compose ps -q pose-worker 2>/dev/null)" ]]; then
    verde "==> religando o pose-worker"
    compose restart pose-worker
  fi
}

cmd_nginx() {
  carrega_ambiente
  cat <<NGINX
# Referencia — adapte ao seu nginx. TLS fica por sua conta (certbot, etc).
#
# O ponto que costuma quebrar: /ws precisa dos headers de Upgrade. Sem eles o
# WebSocket vira um GET comum, o handshake falha, e o cliente so mostra "sem conexao"
# sem nenhuma pista do motivo.

server {
    listen 443 ssl http2;
    server_name ${DOMAIN};

    # ssl_certificate     /etc/letsencrypt/live/${DOMAIN}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/${DOMAIN}/privkey.pem;

    # O modelo do MediaPipe tem 5,5 MB; o buffer padrao do proxy nao atrapalha
    # arquivos estaticos, mas o timeout longo do WS abaixo e obrigatorio.

    location /ws/ {
        proxy_pass http://127.0.0.1:${GATEWAY_PORT:-8001};
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        # A sessao dura 30s, mas o default de 60s do nginx cortaria uma pausa entre series.
        proxy_read_timeout 300s;
        proxy_send_timeout 300s;
    }

    location ~ ^/(api/|healthz|readyz) {
        proxy_pass http://127.0.0.1:${API_PORT:-8000};
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # ------------------------------------------------------------------------------
    # Painel de operacao (SPEC-018) — os DOIS blocos abaixo, sempre juntos
    # ------------------------------------------------------------------------------
    # Sem eles o painel nao existe neste dominio: tudo que nao casa com os blocos acima cai
    # no \`location /\`, ou seja, no container do web — que devolve o index.html do SPA para
    # QUALQUER caminho desconhecido. O sintoma nao e um 404: e a landing do produto abrindo
    # em https://${DOMAIN}/${ADMIN_PATH}, com status 200.
    #
    # Com DJANGO_ENABLE_ADMIN=0 (o default) quem responde aqui e o proprio Django, com 404 —
    # que e o comportamento certo e nao custa nada deixar configurado desde ja.
    #
    # Restringir por IP e barato e vale a pena: quem entra no painel le conta e sessao de
    # todo mundo. Descomente as duas linhas e ponha o seu IP.
    location = /${ADMIN_PATH%/} {
        return 301 https://\$host/${ADMIN_PATH};
    }

    location /${ADMIN_PATH} {
        # allow 203.0.113.10;   # seu IP
        # deny all;
        proxy_pass http://127.0.0.1:${API_PORT:-8000};
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    }

    # O CSS e o JS do painel, servidos pelo whitenoise DENTRO do container da api (o
    # collectstatic roda no build da imagem). Este bloco e o que faz o whitenoise ser
    # alcancado: sem ele /static/... tambem cai no container do web e volta um text/html,
    # que o navegador recusa como folha de estilo. O painel abre inteiro, funcional e SEM
    # ESTILO NENHUM — o sintoma mais confundido com "o tema nao instalou".
    #
    # Nao conflita com o cliente: o build do Vite publica em /assets/, nunca em /static/.
    location /static/ {
        proxy_pass http://127.0.0.1:${API_PORT:-8000};
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
        # O whitenoise ja manda \`Cache-Control: max-age=60\` (sem hash no nome) ou um ano
        # (com hash). Nao sobrescreva aqui: o hash e ele quem sabe.
    }

    location / {
        proxy_pass http://127.0.0.1:${WEB_PORT:-8080};
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen 80;
    server_name ${DOMAIN};
    return 301 https://\$host\$request_uri;
}
NGINX

  if [[ -z "${SITE_DOMAIN:-}${APP_DOMAIN:-}" ]]; then
    cat <<'NGINX'

# SITE e APP no mesmo dominio: nada a acrescentar. O site responde em / e o app em /app/ —
# quem separa e o nginx DE DENTRO do container (docker/web-nginx.conf).
#
# Para separar por subdominio, preencha SITE_DOMAIN/APP_DOMAIN no .env.prod, rode
# `./scripts/prod.sh up` (o bundle precisa ser reconstruido) e rode este comando de novo.
NGINX
    return
  fi

  cat <<NGINX

# ---------------------------------------------------------------------------
# SITE | APP em subdominios (T-067)
# ---------------------------------------------------------------------------
# Um artefato so, dois hosts. O detalhe que quebra: o HTML do app referencia /assets/... em
# caminho ABSOLUTO. Mapear o host inteiro para /app/ (proxy_pass .../app/) faria o navegador
# pedir /app/assets/... e tomar 404. Por isso so a RAIZ e reescrita; o resto passa igual, e
# assets, /models, /wasm e /img continuam sendo os mesmos arquivos para os dois hosts.

server {
    listen 443 ssl http2;
    server_name ${APP_DOMAIN:-app.${DOMAIN}};

    # ssl_certificate     /etc/letsencrypt/live/${APP_DOMAIN:-app.${DOMAIN}}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/${APP_DOMAIN:-app.${DOMAIN}}/privkey.pem;

    # A API e o WS continuam no host principal (${DOMAIN}), que e o que esta gravado no
    # bundle como VITE_API_URL — nao duplique /api e /ws aqui.

    location = / {
        proxy_pass http://127.0.0.1:${WEB_PORT:-8080}/app/index.html;
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }

    location / {
        proxy_pass http://127.0.0.1:${WEB_PORT:-8080};
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen 443 ssl http2;
    server_name ${SITE_DOMAIN:-site.${DOMAIN}};

    # ssl_certificate     /etc/letsencrypt/live/${SITE_DOMAIN:-site.${DOMAIN}}/fullchain.pem;
    # ssl_certificate_key /etc/letsencrypt/live/${SITE_DOMAIN:-site.${DOMAIN}}/privkey.pem;

    location / {
        proxy_pass http://127.0.0.1:${WEB_PORT:-8080};
        proxy_set_header Host \$host;
        proxy_set_header X-Forwarded-Proto \$scheme;
    }
}

server {
    listen 80;
    server_name ${SITE_DOMAIN:-site.${DOMAIN}} ${APP_DOMAIN:-app.${DOMAIN}};
    return 301 https://\$host\$request_uri;
}
NGINX
}

cmd_ajuda() {
  cat <<'AJUDA'
Digital Fit — producao

  ./scripts/prod.sh secrets          preenche os segredos vazios do .env.prod
  ./scripts/prod.sh up               build + migrate + start
  ./scripts/prod.sh modelo           baixa o modelo de pose e religa o pose-worker
  ./scripts/prod.sh plano <email>    mostra o plano da conta
  ./scripts/prod.sh plano <email> --set subscriber [--dias N] [--sem-prazo]
  ./scripts/prod.sh plano <email> --clear     volta ao plano default
  ./scripts/prod.sh plano --list     planos que existem
  ./scripts/prod.sh painel           diagnostico do painel (por que ele nao abre)
  ./scripts/prod.sh painel on|off    liga/desliga e RECRIA a api
  ./scripts/prod.sh exec <svc> ...   roda um comando dentro do servico
  ./scripts/prod.sh nginx            server block de referencia
  ./scripts/prod.sh ps               estado dos servicos
  ./scripts/prod.sh logs [servico]   segue os logs
  ./scripts/prod.sh stop [servico]   para sem remover
  ./scripts/prod.sh start [servico]  religa o que foi parado
  ./scripts/prod.sh restart [svc]    reinicia (NAO recarrega o .env.prod)
  ./scripts/prod.sh down             derruba (o volume do postgres fica)

Use SEMPRE o script, nao `docker compose -f docker-compose.prod.yml` direto: as URLs
publicas sao derivadas do DOMAIN aqui dentro, e sem elas o compose recusa interpolar.

Primeira vez na VPS:
  cp .env.prod.example .env.prod && nano .env.prod   # ponha o DOMAIN
  ./scripts/prod.sh secrets
  ./scripts/prod.sh up
  ./scripts/prod.sh nginx            # cole no seu nginx, recarregue, rode o certbot
AJUDA
}

case "${1:-ajuda}" in
  secrets) cmd_secrets ;;
  up)      cmd_up ;;
  down)    cmd_down ;;
  stop)    cmd_stop "$@" ;;
  start)   cmd_start "$@" ;;
  ps)      cmd_ps ;;
  logs)    cmd_logs "$@" ;;
  restart) cmd_restart "$@" ;;
  modelo)  cmd_modelo ;;
  plano)   cmd_plano "$@" ;;
  painel)  cmd_painel "$@" ;;
  exec)    cmd_exec "$@" ;;
  nginx)   cmd_nginx ;;
  ajuda|help|-h|--help) cmd_ajuda ;;
  *) vermelho "comando desconhecido: $1"; echo; cmd_ajuda; exit 1 ;;
esac
