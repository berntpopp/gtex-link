# Multi-stage build for GTEx-Link
FROM python:3.12-slim AS builder

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy

# Install system dependencies and uv
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && curl -LsSf https://astral.sh/uv/install.sh | sh

# Add uv to PATH
ENV PATH="/root/.local/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy project files (README required by hatchling at build time)
COPY pyproject.toml uv.lock README.md ./
COPY gtex_link ./gtex_link

# Install dependencies with uv and verify venv
RUN uv sync --frozen \
    && ls -la /app/.venv/bin/python \
    && /app/.venv/bin/python --version

# Production stage
FROM python:3.12-slim AS production

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    GTEX_LINK_HOST=0.0.0.0 \
    GTEX_LINK_PORT=8000 \
    PATH="/app/.venv/bin:$PATH" \
    UV_CACHE_DIR=/tmp/uv-cache \
    UV_LINK_MODE=copy

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create app user
RUN groupadd -r gtex && useradd --no-log-init -r -g gtex gtex

# Set work directory
WORKDIR /app

# Copy virtual environment and code from builder
COPY --from=builder /app/.venv .venv
COPY --chown=gtex:gtex . .

# Ensure entry points are executable and verify venv
RUN chmod +x mcp_server.py server.py \
    && ls -la /app/.venv/bin/python \
    && /app/.venv/bin/python --version

# Switch to non-root user
USER gtex

# Healthcheck is defined per-service in compose, not here.
# The unified server exposes FastAPI (and MCP at /mcp) on a single port; the compose
# service-level healthcheck probes /api/health/ over HTTP.

# Expose port
EXPOSE 8000

# Default command - HTTP server
CMD ["/app/.venv/bin/python", "server.py"]
