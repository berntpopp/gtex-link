# GTEx-Link Deployment

How to run, containerize, and expose GTEx-Link. Configuration variables are
documented in [configuration.md](configuration.md); the Compose overlays are
documented in detail in [`docker/README.md`](../docker/README.md).

## Transports

GTEx-Link serves MCP over **Streamable HTTP only**. There is **no stdio
transport**, and no bare-serve: the server always boots through the
`gtex-link serve` subcommand.

| `--transport` | Surface |
|---------------|---------|
| `unified` (default) | FastAPI REST **and** MCP at `/mcp`, on one port. |
| `http` | REST API only — **no `/mcp` endpoint**. |

An MCP client pointed at a server started with `--transport http` will fail to
connect. Use `unified`.

```bash
# Development: verbose console logging, reload
make dev

# Unified REST + MCP
uv run gtex-link serve --transport unified --host 127.0.0.1 --port 8000

# REST only (no MCP)
uv run gtex-link serve --transport http --host 127.0.0.1 --port 8000
```

## CLI

GTEx-Link is a single `typer` CLI.

```bash
uv run gtex-link serve --dev            # start the server (see above)
uv run gtex-link config                 # show the resolved configuration
uv run gtex-link config --validate      # show and validate it
uv run gtex-link health --url http://127.0.0.1:8000   # probe a running server
uv run gtex-link cache stats            # in-process cache statistics
uv run gtex-link cache clear            # drop the in-process cache
uv run gtex-link version                # installed version
```

## MCP client configuration

Start the unified server and point an HTTP-capable MCP client at `/mcp`:

```bash
uv run gtex-link serve --transport unified --host 127.0.0.1 --port 8000
# MCP endpoint: http://127.0.0.1:8000/mcp
```

```json
{
  "mcpServers": {
    "gtex-link": {
      "url": "http://127.0.0.1:8000/mcp"
    }
  }
}
```

The `/mcp` endpoint is session-aware, so a naive `GET /mcp` probe can return a
protocol error even on a perfectly healthy server. Health-check `/api/health`
instead, and verify the protocol with a real MCP client.

## Docker

```bash
make docker-build
make docker-up
curl http://localhost:8765/api/health
make docker-down
```

Compose publishes GTEx-Link on host port **8765**, mapped to container port
`8000`. The non-standard host port is deliberate: it lets GTEx-Link run beside
sibling `-link` projects that commonly squat on `8000`/`8001`. The
container-internal port stays `8000` so reverse-proxy and container-to-container
routing remain predictable. Override the host port with `GTEX_LINK_HOST_PORT`.

The unified container serves both REST and MCP (`/mcp`) on that single port.

| Compose file | Purpose |
|--------------|---------|
| `docker/docker-compose.yml` | Base unified service, published on host port 8765. |
| `docker/docker-compose.dev.yml` | Development: bind mounts and reload. |
| `docker/docker-compose.prod.yml` | Production hardening overlay; **no published host ports**. |
| `docker/docker-compose.npm.yml` | Nginx Proxy Manager deployment; no host ports. |

Overlays are layered explicitly:

```bash
docker compose -f docker/docker-compose.yml -f docker/docker-compose.prod.yml config
```

The production overlay applies the GeneFoundry container-hardening baseline:
read-only root filesystem, writable tmpfs for `/tmp/gtex-link`,
`no-new-privileges`, all Linux capabilities dropped, a PID limit and init
process, resource limits, and JSON log rotation. Full details, including the
Nginx Proxy Manager walkthrough, image build notes, and troubleshooting, are in
[`docker/README.md`](../docker/README.md).

## Request boundary

Every HTTP route is protected by exact `Host` and browser `Origin` allowlists.
The defaults admit only `localhost`, `127.0.0.1`, and IPv6 loopback (`::1`).

**Deploying behind a proxy means adding the public hostname explicitly** to
`GTEX_LINK_ALLOWED_HOSTS` — no scheme, no port, and bare `::1` for IPv6.
Wildcard Host or Origin patterns (`*`, `?`, bracket expressions) are rejected at
configuration time. Production Compose overlays already add
`gtex-link.genefoundry.org`.

`GTEX_LINK_ALLOWED_ORIGINS` (request admission) and `GTEX_LINK_CORS_ORIGINS`
(browser response headers) are separate knobs — see
[configuration.md](configuration.md#request-boundary-host-and-origin-allowlists).

GTEx-Link is **unauthenticated by design**. Like every GeneFoundry `-link`
backend, it owns no edge auth and MUST be reached only through the
`genefoundry-router` / reverse proxy at the trust boundary — never published
directly. See [`SECURITY.md`](../SECURITY.md).

## Health and monitoring

| Endpoint | Purpose |
|----------|---------|
| `GET /api/health/` | Basic liveness check. |
| `GET /api/health/ready` | Readiness, including live GTEx Portal API connectivity. |
| `GET /api/health/stats` | Service performance statistics. |

Metrics cover request/response times, cache hit/miss rates, upstream API success
rates, and error counts by type. Set `GTEX_LINK_LOG_FORMAT=json` in production
so structured logs, including correlation IDs, are machine-parseable.
