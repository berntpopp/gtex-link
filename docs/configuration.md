# GTEx-Link Configuration

Every setting is read from the environment or a `.env` file, using the
`GTEX_LINK_` prefix. `.env.example` is the copy-paste starting point.

Two spellings, and the difference matters:

- **Flat settings** are `GTEX_LINK_<FIELD>` — e.g. `GTEX_LINK_PORT`.
- **Nested groups** (`api`, `cache`) are `GTEX_LINK_<GROUP>__<FIELD>`, with a
  **double underscore** — e.g. `GTEX_LINK_CACHE__TTL`.

An unrecognised `GTEX_LINK_*` name is **silently ignored** (`extra="ignore"`), so
a single-underscore `GTEX_LINK_CACHE_TTL` does nothing at all. The tables below
are exhaustive over `gtex_link/config.py`, and
`tests/unit/test_config_env_contract.py` fails the build if a setting is added,
renamed, or documented under a name that does not bind.

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
| `GTEX_LINK_RELOAD` | `false` | Auto-reload on code change. Development only. |
| `GTEX_LINK_DISABLE_DOCS` | `false` | Disable the REST docs endpoints (`/docs`, `/redoc`, `/openapi.json`). |

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
| `GTEX_LINK_CORS_ALLOW_METHODS` | `["GET","POST","PUT","DELETE","OPTIONS"]` | Methods echoed in CORS response headers. |
| `GTEX_LINK_CORS_ALLOW_HEADERS` | `["*"]` | Headers echoed in CORS response headers. Wide by default; the request guard above, not CORS, is the trust boundary. |

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
Nested group — note the **double underscore**.

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_API__BASE_URL` | `https://gtexportal.org/api/v2/` | Public, **no authentication required**. A trailing `/` is added if absent. |
| `GTEX_LINK_API__TIMEOUT` | `30` | Request timeout, seconds (1–300). |
| `GTEX_LINK_API__RATE_LIMIT_PER_SECOND` | `5.0` | Token-bucket rate limit (0–20). Do not raise it casually — it is upstream courtesy, not a local throttle. |
| `GTEX_LINK_API__BURST_SIZE` | `10` | Token-bucket burst (1–50). |
| `GTEX_LINK_API__MAX_RETRIES` | `3` | Retry attempts, with exponential backoff (0–10). |
| `GTEX_LINK_API__RETRY_DELAY` | `1.0` | Base delay between retries, seconds (0.1–10). |
| `GTEX_LINK_API__USER_AGENT` | `GTEx-Link/2.0.0` | `User-Agent` sent upstream. |
| `GTEX_LINK_API__ENDPOINTS` | see `config.py` | JSON map of upstream endpoint paths. Overriding it is rarely useful. |

## Caching

| Variable | Default | Notes |
|----------|---------|-------|
Nested group — note the **double underscore**.

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_CACHE__SIZE` | `1000` | Maximum cached items, LRU eviction (10–10000). |
| `GTEX_LINK_CACHE__TTL` | `3600` | Cache TTL, seconds (60–86400). |
| `GTEX_LINK_CACHE__STATS_ENABLED` | `true` | Track cache hit/miss statistics. |
| `GTEX_LINK_CACHE__CLEANUP_INTERVAL` | `300` | Expired-entry sweep interval, seconds (60–3600). |

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
| `GTEX_LINK_LOG_SHOW_CALLER` | `false` | Add caller module/line to each log record. |

Logging is structured (structlog) and carries correlation IDs for request
tracing. See [architecture.md](architecture.md) for what is emitted.

## Docker

| Variable | Default | Notes |
|----------|---------|-------|
| `GTEX_LINK_HOST_PORT` | `8765` | Host port published by Compose, mapped to container port `8000`. |
| `NPM_SHARED_NETWORK_NAME` | `npm_default` | External Nginx Proxy Manager network, for the NPM overlay. |

See [deployment.md](deployment.md).
