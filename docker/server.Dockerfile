# Imagem do lado Python: api (DRF), gateway (Channels) e workers.
# Um unico ambiente para todos — o que muda e o `command` no compose.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.11 /uv /usr/local/bin/uv

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/opt/venv \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Camada de dependencias (cacheada enquanto o lock nao muda).
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --extra server --no-dev

COPY server/ ./server/
COPY workers/ ./workers/

# `workers.*` importavel de qualquer WORKDIR; `core.*`/`api.*` a partir de server/.
ENV PYTHONPATH=/app

WORKDIR /app/server
EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
