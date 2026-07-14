# GTEx-Link Configuration

Every setting is read from the environment or a `.env` file, using the
`GTEX_LINK_` prefix. `.env.example` is the copy-paste starting point.

Inspect the resolved configuration at any time:

```bash
uv run gtex-link config              # print the effective settings
uv run gtex-link config --validate   # print and validate them
```

## Server

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_HOST` | `127.0.0.1` | Bind address. |
| `GTEX_LINK_PORT` | `8000` | Container-internal port; also the local dev port. |
| `GTEX_LINK_TRANSPORT` | `unified` | `unified` (REST + MCP at `/mcp`) or `http` (REST only, **no MCP**). |
| `GTEX_LINK_MCP_PATH` | `/mcp` | MCP endpoint path. |
| `GTEX_LINK_MCP_PROFILE` | `full` | MCP tool profile: `full` or `lite`. |

### MCP tool profiles

`GTEX_LINK_MCP_PROFILE=lite` narrows the registered MCP surface to the
common-path tools — `search`, `fetch`, `search_genes`, `get_gene_information`,
`get_median_expression_levels`, `get_server_capabilities` — and drops the rest.
`full` (the default) registers every tool. The profile is applied at
registration time, so it changes what a client sees in `tools/list`. The
authoritative set lives in `gtex_link/mcp/profiles.py` (`LITE_TOOLS`).

## Request boundary: Host and Origin allowlists

Every HTTP route (REST **and** MCP) is gated by **exact** Host and browser
Origin allowlists.

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_ALLOWED_HOSTS` | `["localhost","127.0.0.1","::1"]` | Exact JSON list of permitted `Host` values. |
| `GTEX_LINK_ALLOWED_ORIGINS` | `[]` | Exact JSON list of permitted browser `Origin` values. |
| `GTEX_LINK_CORS_ORIGINS` | `["http://localhost:3000","http://127.0.0.1:3000"]` | Origins echoed in CORS **response** headers. |
| `GTEX_LINK_CORS_ALLOW_CREDENTIALS` | `false` | Keep `false` unless you have a specific reason. |

Rules that are easy to get wrong:

- **Host entries carry no scheme and no port.** Write `gtex-link.genefoundry.org`,
  not `https://gtex-link.genefoundry.org:443`.
- **Write IPv6 loopback bare: `::1`, not `[::1]`.**
- **Wildcards are rejected at configuration time** — `*`, `?`, and bracket
  expressions in either allowlist fail startup rather than silently widening the
  boundary.
- Deploying behind a reverse proxy means adding the **public proxy hostname**
  explicitly to `GTEX_LINK_ALLOWED_HOSTS`.

`GTEX_LINK_ALLOWED_ORIGINS` and `GTEX_LINK_CORS_ORIGINS` are two different
knobs and both matter:

- `GTEX_LINK_ALLOWED_ORIGINS` is the **request-boundary policy** — it decides
  whether a request carrying an `Origin` header is admitted at all.
- `GTEX_LINK_CORS_ORIGINS` only controls the browser **response** headers.

Keep the two lists in sync for browser clients; an origin permitted by CORS but
absent from `ALLOWED_ORIGINS` is still rejected. Requests with **no** `Origin`
header — normal router-to-backend MCP traffic, `curl`, server-side clients —
remain allowed as long as their `Host` is trusted.

## Upstream GTEx Portal API

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_API_BASE_URL` | `https://gtexportal.org/api/v2/` | Public, **no authentication required**. |
| `GTEX_LINK_API_TIMEOUT` | `30` | Request timeout, seconds. |
| `GTEX_LINK_API_RATE_LIMIT_PER_SECOND` | `5.0` | Token-bucket rate limit. Do not raise it casually — it is upstream courtesy, not a local throttle. |
| `GTEX_LINK_API_BURST_SIZE` | `10` | Token-bucket burst. |
| `GTEX_LINK_API_MAX_RETRIES` | `3` | Retry attempts, with exponential backoff. |

## Caching

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_CACHE_SIZE` | `1000` | Maximum cached items (LRU eviction). |
| `GTEX_LINK_CACHE_TTL` | `3600` | Cache TTL, seconds. |

Inspect or clear the in-process cache:

```bash
uv run gtex-link cache stats
uv run gtex-link cache clear
```

## Logging

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_LOG_LEVEL` | `INFO` | Standard Python levels. |
| `GTEX_LINK_LOG_FORMAT` | `console` | `console` for development, `json` for production. |

Logging is structured (structlog) and carries correlation IDs for request
tracing. See [architecture.md](architecture.md) for what is emitted.

## Docker

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_HOST_PORT` | `8765` | Host port published by Compose, mapped to container port `8000`. |
| `NPM_SHARED_NETWORK_NAME` | `npm_default` | External Nginx Proxy Manager network, for the NPM overlay. |

See [deployment.md](deployment.md).
