# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for GTEx-Link.

FROM python:3.14-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV VIRTUAL_ENV="/opt/venv" \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /home/app/web
COPY uv.lock pyproject.toml README.md ./

RUN pip install --upgrade pip uv && \
    uv sync --frozen --no-dev --active --no-install-project


FROM python:3.14-slim AS production

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH" \
    PYTHONPATH="/home/app/web" \
    GTEX_LINK_HOST=0.0.0.0 \
    GTEX_LINK_PORT=8000 \
    TMPDIR=/tmp/gtex-link

RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd --system app && \
    useradd --system --gid app --home /home/app --create-home app && \
    mkdir -p /tmp/gtex-link /var/cache/gtex-link && \
    chown -R app:app /tmp/gtex-link /var/cache/gtex-link /home/app

COPY --from=builder /opt/venv /opt/venv

WORKDIR /home/app/web

COPY --chown=app:app ./gtex_link ./gtex_link
COPY --chown=app:app ./pyproject.toml ./README.md ./
COPY --chown=app:app ./docker/gunicorn_conf.py ./

RUN /opt/venv/bin/pip install . --no-deps

USER app

EXPOSE 8000

# Unified transport: FastAPI on / and MCP on /mcp via a single port.
CMD ["gtex-link", "serve", "--transport", "unified", "--host", "0.0.0.0", "--port", "8000"]
