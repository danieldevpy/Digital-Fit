# Imagem do dataset-writer (SPEC-010 / T-021).
#
# Separada de `server.Dockerfile` pela mesma razao do pose-worker: pyarrow pesa ~100 MB e o
# api, o gateway e o analysis-worker nao gravam Parquet. Um servico paga, os outros nao.
#
# Sem Django: este worker le eventos e escreve arquivos, nada de ORM. O extra instalado e so
# o `dataset`.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra dataset --no-dev

COPY workers/ ./workers/

ENV PYTHONPATH=/app \
    DATASET_DIR=/data/dataset

CMD ["python", "-m", "workers.dataset_writer.main"]
