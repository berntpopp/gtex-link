# GTEx-Link Docker Deployment

Production-ready Docker setup for GTEx-Link with multi-stage builds, non-root
runtime containers, and Compose overlays for local, development, production, and
Nginx Proxy Manager deployments. The server runs a single **unified** process
that exposes the REST API on `/` and the MCP endpoint on `/mcp` over one port.

## Quick Start

```bash
make docker-build
make docker-up
curl http://localhost:8765/api/health
make docker-down
```

GTEx-Link intentionally publishes a non-standard host port for local development
so it can run beside sibling projects with similar stacks:

- Unified server (REST + MCP at `/mcp`): `8765:8000`

Override it when needed:

```bash
GTEX_LINK_HOST_PORT=8120 make docker-up
```

The container-internal port stays standard (`8000`), which keeps reverse-proxy
and container-to-container routing predictable.

The server enforces exact Host and browser Origin allowlists across REST and
MCP. Base Compose admits loopback only. Production overlays add
`gtex-link.genefoundry.org` and couple the permitted browser Origin to the CORS
list. Host entries omit schemes and ports; use bare `::1` for IPv6. Wildcards
are rejected in both request-boundary allowlists.

## Compose Files

- `docker-compose.yml` - base unified service, published on host port 8765.
- `docker-compose.dev.yml` - development service with bind mounts and reload.
- `docker-compose.prod.yml` - production hardening overlay with no host ports.
- `docker-compose.npm.yml` - Nginx Proxy Manager deployment with a single
  unified container and no host ports.

Layer overlays explicitly:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config
```

## Local Development

```bash
docker compose -f docker/docker-compose.dev.yml up --build
curl http://localhost:8765/api/health
```

The development compose file mounts `gtex_link/`, tests, and entrypoint scripts
into the container and starts the CLI server with reload enabled.

## Standalone Unified Server

```bash
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8765/api/health
curl http://localhost:8765/mcp
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
- unified Uvicorn server serving REST and MCP on a single port.

Publish a port for local production testing by using only `docker-compose.yml`,
or by adding a local override file that publishes the desired host port.

The MCP streamable HTTP endpoint at `/mcp` is session-aware, so simple
`GET /mcp` probes can return protocol errors. The Compose health check probes
`/api/health` over HTTP instead; use an MCP client for protocol-level
verification.

## Nginx Proxy Manager

1. Copy and edit the Docker environment file:

```bash
cp .env.docker.example .env.docker
```

2. Ensure the external NPM network exists. The default is `npm_default`; change
   `NPM_SHARED_NETWORK_NAME` in `.env.docker` if your deployment uses another
   network.

3. Start the unified container:

```bash
docker compose \
  --env-file .env.docker \
  -f docker/docker-compose.npm.yml \
  up -d --build
```

4. In Nginx Proxy Manager, proxy `/api`, `/docs`, `/openapi.json`, `/redoc`,
   `/metrics`, and `/mcp` to `gtex-link-npm:8000`. Enable Websockets Support,
   Block Common Exploits, and Force SSL after certificate issuance.

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

Set `GTEX_LINK_HOST_PORT` to another free port.

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

- Unified server: `curl http://localhost:8765/api/health`
- MCP endpoint: session-aware at `/mcp`; use an MCP client for protocol-level
  verification.
