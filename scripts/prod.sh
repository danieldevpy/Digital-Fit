#!/usr/bin/env bash
#
# Digital Fit — sobe a stack de producao na VPS e expoe as portas para o seu nginx.
#
#   ./scripts/prod.sh secrets   # preenche os segredos vazios do .env.prod
#   ./scripts/prod.sh up        # build + migrate + start
#   ./scripts/prod.sh nginx     # imprime o server block de referencia
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

# Preenche apenas chaves com valor VAZIO. Nunca sobrescreve um segredo existente: rotacionar
# SESSION_TOKEN_SECRET sem querer derrubaria toda sessao em voo.
cmd_secrets() {
  [[ -f "$ENV_FILE" ]] || morre "$ENV_FILE nao existe. Rode: cp .env.prod.example .env.prod"

  local mudou=0
  for chave in DJANGO_SECRET_KEY SESSION_TOKEN_SECRET POSTGRES_PASSWORD; do
    if grep -qE "^${chave}=$" "$ENV_FILE"; then
      local valor
      valor="$(gera_segredo)"
      # `|` como separador: base64 nao produz `|`, entao nao ha o que escapar.
      sed -i "s|^${chave}=$|${chave}=${valor}|" "$ENV_FILE"
      verde "  $chave gerado"
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
    return 0
  fi

  : "${DOMAIN:?DOMAIN nao definido em .env.prod}"

  [[ "$DOMAIN" == "treino.seudominio.com.br" ]] &&
    morre "DOMAIN ainda e o exemplo. Ponha o seu dominio em $ENV_FILE"
  [[ "$DOMAIN" == *"://"* ]] &&
    morre "DOMAIN vai sem esquema: use 'treino.exemplo.com', nao 'https://treino.exemplo.com'"
  [[ "$DOMAIN" == */* ]] &&
    morre "DOMAIN vai sem barra nem caminho: use apenas o host"

  for chave in DJANGO_SECRET_KEY SESSION_TOKEN_SECRET POSTGRES_PASSWORD; do
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
# Comandos
# --------------------------------------------------------------------------------------

cmd_up() {
  carrega_ambiente
  verifica_portas

  verde "==> build (o web e reconstruido sempre: VITE_API_URL entra no bundle)"
  compose build

  # `run` respeita o `depends_on: service_healthy` do api, entao redis e postgres sobem e
  # ficam saudaveis antes da migration comecar — nao ha o que esperar na mao aqui.
  verde "==> migrations"
  compose run --rm api python manage.py migrate --noinput

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

cmd_down()    { carrega_ambiente --tolerante; compose down; }
cmd_ps()      { carrega_ambiente --tolerante; compose ps; }
cmd_logs()    { carrega_ambiente --tolerante; shift || true; compose logs -f --tail 100 "$@"; }
cmd_restart() { carrega_ambiente --tolerante; shift || true; compose restart "$@"; }

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
}

cmd_ajuda() {
  cat <<'AJUDA'
Digital Fit — producao

  ./scripts/prod.sh secrets          preenche os segredos vazios do .env.prod
  ./scripts/prod.sh up               build + migrate + start
  ./scripts/prod.sh nginx            server block de referencia
  ./scripts/prod.sh ps               estado dos servicos
  ./scripts/prod.sh logs [servico]   segue os logs
  ./scripts/prod.sh restart [svc]    reinicia
  ./scripts/prod.sh down             derruba (o volume do postgres fica)

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
  ps)      cmd_ps ;;
  logs)    cmd_logs "$@" ;;
  restart) cmd_restart "$@" ;;
  nginx)   cmd_nginx ;;
  ajuda|help|-h|--help) cmd_ajuda ;;
  *) vermelho "comando desconhecido: $1"; echo; cmd_ajuda; exit 1 ;;
esac
