# GTEx-Link Architecture

GTEx-Link follows clean-architecture layering: a rate-limited HTTP client to the
GTEx Portal, a caching service layer holding the business logic, and two
independent presentation surfaces (REST and MCP) over the same service.

```
gtex_link/
├── api/                 # API layer (FastAPI)
│   ├── client.py        # GTEx Portal API client
│   └── routes/          # HTTP route handlers
├── mcp/                 # MCP facade: tools, envelope, resources, profiles
├── services/            # Business logic layer
│   └── gtex_service.py  # Core GTEx service
├── models/              # Data models (Pydantic)
│   ├── gtex.py          # GTEx-specific enums
│   ├── requests.py      # Request models
│   └── responses.py     # Response models
├── utils/               # Utilities
│   └── caching.py       # Caching utilities
├── config.py            # Configuration management
├── exceptions.py        # Custom exceptions
└── logging_config.py    # Logging configuration
```

## Core Components

1. **API Layer** (`gtex_link/api/`)
   - `client.py` — HTTP client with token-bucket rate limiting (5 req/sec
     default), retry logic, connection pooling
   - `routes/` — FastAPI route handlers organized by GTEx data category

2. **MCP Facade** (`gtex_link/mcp/`)
   - `facade.py` — `create_gtex_mcp(profile=...)` builds the FastMCP server and
     registers the tool surface
   - `profiles.py` — the `full` / `lite` tool profiles
   - `envelope.py`, `metadata.py`, `next_commands.py` — the response envelope,
     provenance `_meta`, and chaining hints
   - `resources.py`, `capabilities_resources.py` — the `gtex://` resource family

3. **Models Layer** (`gtex_link/models/`)
   - `requests.py` — Pydantic request models
   - `responses.py` — Pydantic response models matching the GTEx v2 schema
   - `gtex.py` — GTEx-specific enums (tissues, datasets)

4. **Services Layer** (`gtex_link/services/`)
   - `gtex_service.py` — business logic, async LRU caching, validation

5. **Utilities Layer** (`gtex_link/utils/`)
   - `caching.py` — centralized async caching with configurable TTL/size

6. **Configuration** (`gtex_link/config.py`)
   - Pydantic settings with the `GTEX_LINK_` env prefix; nested models for API,
     cache, CORS, logging. Every variable: [configuration.md](configuration.md).

7. **Application Factory** (`gtex_link/app.py`)
   - Creates the FastAPI app, configures CORS, includes routers

8. **Server Management** (`gtex_link/server_manager.py`)
   - Unified entry point for the `http` and `unified` (HTTP + MCP) transports
     (Streamable HTTP only — there is no stdio transport)

9. **CLI** (`gtex_link/cli.py`)
   - `typer` app (`gtex-link`) with `serve` / `config` / `health` / `cache` /
     `version` commands; the server always boots via `gtex-link serve`

## Key Features

- Dual protocol (HTTP REST + MCP) over the same FastAPI app
- Async/await with connection pooling
- Token-bucket rate limiting respecting upstream limits
- Strict typing (Pydantic models, mypy strict)
- Structured logging (structlog) with JSON/console formats

## The two surfaces are not symmetric

REST and MCP are served from one process in `unified` mode, but they do **not**
expose the same functionality. **The REST API covers association data
(eQTL/sQTL) that has no corresponding MCP tool.** A model talking to this server
over MCP cannot reach the `/api/association/*` routes; an HTTP client can.

This is deliberate — the MCP surface is scoped to the expression and reference
questions an assistant can usefully chain — but it is a real asymmetry to keep
in mind when comparing the two surfaces or planning new tools.

### REST endpoints

**Reference data**

- `GET /api/reference/genes/search` — search genes by symbol or ID
- `GET /api/reference/genes` — gene information with filtering
- `GET /api/reference/transcripts` — transcript information

**Expression data**

- `GET /api/expression/median-gene-expression` — median gene expression across tissues
- `GET /api/expression/gene-expression` — individual-sample expression data
- `GET /api/expression/top-expressed-genes` — top expressed genes by tissue

**Association data** (REST only — no MCP tool)

- `GET /api/association/single-tissue-eqtl` — expression QTL associations
- `GET /api/association/single-tissue-sqtl` — splicing QTL associations
- `GET /api/association/egenes` — genes with significant eQTLs
- `GET /api/association/sgenes` — genes with significant sQTLs

**Health & monitoring**

- `GET /api/health/` — basic health check
- `GET /api/health/ready` — readiness check, including GTEx API connectivity
- `GET /api/health/stats` — service performance statistics

### MCP surface

The registered MCP tools are enumerated in the [README](../README.md#tools) —
that table is machine-verified against the server by
`tests/unit/test_readme_tools.py`. Leaf tool names are unprefixed per the
GeneFoundry Tool-Naming Standard v1; the `genefoundry-router` gateway mounts
this server with `mount(namespace="gtex")`, so `get_gene_information` surfaces
as `gtex_get_gene_information`. Response conventions (`response_mode`,
`offset`/`limit`, `_meta.next_commands`, error codes) are documented in
[data.md](data.md).

## Caching

Multi-level:

- Service-level async LRU cache for processed results
- Client-level HTTP response caching with TTL

Tunable via `GTEX_LINK_CACHE_SIZE` and `GTEX_LINK_CACHE_TTL`.

## Rate limiting

Token-bucket algorithm:

- Default 5 req/s, burst 10
- Exponential backoff for retries

## Error hierarchy

- `GTExAPIError` — base
- `RateLimitError` — 429 from upstream
- `ServiceUnavailableError` — upstream 503
- `ValidationError` — input validation
- `ConfigurationError`, `CacheError` — misc

### HTTP mapping

- **Validation errors** → `400 Bad Request`, with field details
- **Rate limiting** → `429 Too Many Requests`, with retry hints
- **Upstream API errors** → `502 Bad Gateway`
- **Service errors** → `503 Service Unavailable`

On the MCP surface the same conditions surface as structured `error_code`
values — see [data.md](data.md#response-conventions).

## Observability

Metrics: request/response times, cache hit/miss rates, upstream API success
rates, error counts by type.

Logging: structlog, JSON in production and console in development, with
correlation IDs for request tracing.

## Performance characteristics

Indicative only — these are design targets from the original build, not a
maintained benchmark:

- Cold start: ~50 ms for a gene search
- Warm cache: ~5 ms for cached responses
- Memory: ~50 MB base, plus the cache
- Throughput: 100+ req/sec sustained, concurrent

The levers behind them: non-blocking async I/O, HTTP connection pooling,
multi-level caching with LRU eviction, token-bucket rate limiting to prevent
upstream overload, and lazy resource loading.
