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

RUN npm run build


FROM nginx:1.27-alpine AS runtime

COPY docker/web-nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -qO- http://127.0.0.1/ >/dev/null || exit 1
