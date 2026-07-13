# syntax=docker/dockerfile:1
# Multi-stage Dockerfile for GTEx-Link.

FROM python:3.14-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1 AS builder

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

# Pin uv by digest (fleet-shared anchor) instead of a floating pip/uv upgrade so
# the build bootstrap is byte-reproducible and supply-chain fixed (F-19).
COPY --from=ghcr.io/astral-sh/uv:0.8.7@sha256:1e26f9a868360eeb32500a35e05787ffff3402f01a8dc8168ef6aee44aef0aab /uv /usr/local/bin/uv

RUN uv sync --frozen --no-dev --active --no-install-project


FROM python:3.14-slim@sha256:b877e50bd90de10af8d82c57a022fc2e0dc731c5320d762a27986facfc3355c1 AS production


ARG APP_VERSION=0.0.0
ARG VCS_REF=unknown
ARG BUILD_DATE=1970-01-01T00:00:00Z
LABEL org.opencontainers.image.title="GTEx-Link" \
      org.opencontainers.image.description="Research-use MCP/API server for GTEx Portal expression data." \
      org.opencontainers.image.source="https://github.com/berntpopp/gtex-link" \
      org.opencontainers.image.url="https://github.com/berntpopp/gtex-link" \
      org.opencontainers.image.documentation="https://github.com/berntpopp/gtex-link#readme" \
      org.opencontainers.image.version="${APP_VERSION}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="GeneFoundry"
ENV APP_VERSION="${APP_VERSION}" \
    VCS_REF="${VCS_REF}"

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

RUN groupadd --gid 10001 app && \
    useradd --uid 10001 --gid app --home /home/app --create-home --shell /usr/sbin/nologin app && \
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

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f -H 'Host: localhost' http://localhost:8000/health || exit 1

# Unified transport: FastAPI on / and MCP on /mcp via a single port.
CMD ["gtex-link", "serve", "--transport", "unified", "--host", "0.0.0.0", "--port", "8000"]
