# Cliente web em producao: build estatico do Vite servido por nginx.
#
# Este nginx e INTERNO ao container e so serve arquivos. O nginx da VPS (o seu) fica na
# frente, termina TLS e roteia /api, /ws e / — ver docs/DEPLOY.md.
#
# O build precisa de internet: `npm run build` dispara o `prebuild` (setup-mediapipe), que
# baixa o modelo de 5,5 MB quando nao o encontra localmente. Dentro do container nao ha
# `../eval/models`, entao o caminho normal aqui e o download mesmo.

FROM node:22-alpine AS build

WORKDIR /app

# Camada de dependencias: so muda quando o lock muda.
COPY web/package.json web/package-lock.json ./
RUN npm ci

COPY web/ ./

# `VITE_*` e resolvida em BUILD TIME e fica gravada no bundle — nao adianta passar por
# environment no compose de producao. Por isso e ARG, e por isso trocar de dominio exige
# rebuild da imagem do web (o script de producao faz isso).
ARG VITE_API_URL=""
ENV VITE_API_URL=${VITE_API_URL}

# Fronteira SITE|APP (T-067). Vazias = deploy num dominio so, e o cliente usa os defaults de
# caminho (`/` e `/app/`). Com subdominio, o `scripts/prod.sh` passa as origens completas
# aqui — e como sao `VITE_*`, ficam gravadas no bundle: trocar de host exige rebuild.
ARG VITE_SITE_URL=""
ARG VITE_APP_URL=""
ENV VITE_SITE_URL=${VITE_SITE_URL}
ENV VITE_APP_URL=${VITE_APP_URL}

# A origem PUBLICA do site, absoluta (T-160). Nao confundir com VITE_SITE_URL: aquela responde
# "qual a base para um link de um bundle para o outro" e fica vazia no deploy de dominio unico
# (o site mora em `/`, o relativo basta). Esta responde "em que origem esta pagina vai ser
# servida", que e o que `canonical` e `hreflang` exigem — e tem resposta nos dois deploys.
# Sem ela o passo de pre-render PARA o build, de proposito: `hreflang` relativo e ignorado em
# silencio pelo Google, e foi assim que o da T-147 sobreviveu meses.
ARG VITE_SITE_ORIGIN=""
ENV VITE_SITE_ORIGIN=${VITE_SITE_ORIGIN}

RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY docker/web-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
