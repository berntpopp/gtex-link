# GTEx-Link Docker Deployment

Production-ready Docker setup for GTEx-Link with multi-stage builds, non-root
runtime containers, and Compose overlays for local, production, MCP-only, and
Nginx Proxy Manager deployments.

## Quick Start

```bash
make docker-build
make docker-up
curl http://localhost:8020/api/health/
make docker-down
```

GTEx-Link intentionally publishes non-standard host ports for local development
so it can run beside sibling projects with similar stacks:

- REST API: `8020:8000`
- MCP HTTP: `8021:8001`

Override them when needed:

```bash
GTEX_LINK_HOST_PORT=8120 make docker-up
GTEX_LINK_MCP_HOST_PORT=8121 docker compose -f docker/docker-compose.mcp.yml up -d
```

Container-internal ports stay standard (`8000` for REST, `8001` for MCP), which
keeps reverse-proxy and container-to-container routing predictable.

## Compose Files

- `docker-compose.yml` - base REST API service, published on host port 8020.
- `docker-compose.dev.yml` - development service with bind mounts and reload.
- `docker-compose.prod.yml` - production hardening overlay with no host ports.
- `docker-compose.mcp.yml` - MCP HTTP-only service, published on host port 8021.
- `docker-compose.npm.yml` - Nginx Proxy Manager deployment with separate API
  and MCP containers and no host ports.

Layer overlays explicitly:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config
```

## Local Development

```bash
docker compose -f docker/docker-compose.dev.yml up --build
curl http://localhost:8020/api/health/
```

The development compose file mounts `gtex_link/`, tests, and entrypoint scripts
into the container and starts the CLI server with reload enabled.

## Standalone REST API

```bash
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8020/api/health/
docker compose -f docker/docker-compose.yml logs -f
```

## Production Overlay

```bash
docker compose \
  -f docker/docker-compose.yml \
  -f docker/docker-compose.prod.yml \
  up -d --build
```

The production overlay follows the sibling repository pattern:

- no published host ports by default,
- read-only root filesystem,
- writable tmpfs for `/tmp/gtex-link`,
- `no-new-privileges`,
- Linux capabilities dropped,
- PID limit and init process,
- resource limits and JSON log rotation,
- Gunicorn with Uvicorn workers for the REST API service.

Publish a port for local production testing by using only `docker-compose.yml`,
or by adding a local override file that publishes the desired host port.

## MCP HTTP-Only

```bash
docker compose -f docker/docker-compose.mcp.yml up -d --build
curl -v http://localhost:8021/mcp
```

The MCP streamable HTTP endpoint is session-aware, so simple `GET /mcp` probes
can return protocol errors. Compose health checks probe the TCP listener instead.

## Nginx Proxy Manager

1. Copy and edit the Docker environment file:

```bash
cp .env.docker.example .env.docker
```

2. Ensure the external NPM network exists. The default is `npm_default`; change
   `NPM_SHARED_NETWORK_NAME` in `.env.docker` if your deployment uses another
   network.

3. Start the API and MCP containers:

```bash
docker compose \
  --env-file .env.docker \
  -f docker/docker-compose.npm.yml \
  up -d --build
```

4. In Nginx Proxy Manager:

- Proxy `/api`, `/docs`, `/openapi.json`, `/redoc`, and `/metrics` to
  `gtex-link-api-npm:8000`.
- Proxy `/mcp` to `gtex-link-mcp-npm:8001`.
- Enable Websockets Support, Block Common Exploits, and Force SSL after
  certificate issuance.

## Image Build Notes

The Dockerfile uses a multi-stage `uv` build:

- builder stage installs production dependencies into `/opt/venv`,
- runtime stage copies only the virtual environment and required application
  files,
- runtime user is non-root (`app`),
- package installs use the checked-in `uv.lock`.

No secrets are copied into the image. Pass environment-specific settings through
Compose `env_file` or environment variables at runtime.

## Troubleshooting

**Port conflicts**

Set `GTEX_LINK_HOST_PORT` or `GTEX_LINK_MCP_HOST_PORT` to another free port.

**NPM network missing**

```bash
docker network ls
docker network create npm_default
```

**Build cache issues**

```bash
docker compose -f docker/docker-compose.yml build --no-cache
```

**Health checks**

- REST API: `curl http://localhost:8020/api/health/`
- MCP HTTP: TCP listener probe in Compose; use an MCP client for protocol-level
  verification.
