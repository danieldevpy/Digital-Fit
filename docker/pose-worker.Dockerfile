# Imagem do pose-worker (modo cloud, SPEC-005 / T-016).
#
# Separada de `server.Dockerfile` porque MediaPipe + OpenCV pesam ~250 MB, e o api, o gateway
# e o analysis-worker nao tem o que fazer com eles. Um servico paga, os outros nao.
#
# O modelo `.task` (5,5 MB) NAO entra na imagem: ele e o mesmo arquivo que a bancada e o
# cliente usam, e vem por volume (`DIGITALFIT_POSE_MODEL`). Assar o modelo aqui abriria a
# porta para as tres pontas divergirem sem ninguem perceber.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

# `libGL` e `libglib` sao exigidos pelo OpenCV mesmo na variante headless (o pacote e
# headless quanto a JANELAS, nao quanto a bibliotecas de imagem).
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra pose --no-dev

COPY workers/ ./workers/

ENV PYTHONPATH=/app \
    DIGITALFIT_POSE_MODEL=/models/pose_landmarker_lite.task

CMD ["python", "-m", "workers.pose_worker.main"]
