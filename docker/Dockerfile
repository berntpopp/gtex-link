# Multi-stage build for GTEx-Link
FROM python:3.11-slim as builder

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

# Copy project files
COPY pyproject.toml uv.lock ./

# Install dependencies with uv and verify venv
RUN uv sync --frozen \
    && ls -la /app/.venv/bin/python \
    && /app/.venv/bin/python --version

# Production stage
FROM python:3.11-slim as production

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

# Ensure new entry points are executable and verify venv
RUN chmod +x mcp_http_server.py mcp_server.py server.py \
    && ls -la /app/.venv/bin/python \
    && /app/.venv/bin/python --version

# Switch to non-root user
USER gtex

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:${GTEX_LINK_PORT}/api/health/ || exit 1

# Expose port
EXPOSE 8000

# Default command - HTTP server
CMD ["/app/.venv/bin/python", "server.py"]
