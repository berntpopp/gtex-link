# GTEx-Link Architecture

## Core Components

1. **API Layer** (`gtex_link/api/`)
   - `client.py` - HTTP client with token-bucket rate limiting (5 req/sec
     default), retry logic, connection pooling
   - `routes/` - FastAPI route handlers organized by GTEx data category

2. **Models Layer** (`gtex_link/models/`)
   - `requests.py` - Pydantic request models
   - `responses.py` - Pydantic response models matching GTEx v2 schema
   - `gtex.py` - GTEx-specific enums (tissues, datasets)

3. **Services Layer** (`gtex_link/services/`)
   - `gtex_service.py` - Business logic, async LRU caching, validation

4. **Utilities Layer** (`gtex_link/utils/`)
   - `caching.py` - Centralized async caching with configurable TTL/size

5. **Configuration** (`gtex_link/config.py`)
   - Pydantic settings with `GTEX_LINK_` env prefix
   - Nested models for API, cache, CORS, logging

6. **Application Factory** (`gtex_link/app.py`)
   - Creates FastAPI app, configures CORS, includes routers

7. **Server Management** (`gtex_link/server_manager.py`)
   - Unified entry point for the `http` and `unified` (HTTP + MCP) transports
     (Streamable HTTP only — there is no stdio transport)

8. **CLI** (`gtex_link/cli.py`)
   - `typer` app (`gtex-link`) with `serve` / `config` / `health` / `cache` /
     `version` commands; the server always boots via `gtex-link serve`

## Key Features

- Dual protocol (HTTP REST + MCP) over the same FastAPI app
- Async/await with connection pooling
- Token-bucket rate limiting respecting upstream limits
- Strict typing (Pydantic models, mypy strict)
- Structured logging (structlog) with JSON/console formats

## Environment Variables

All settings use the `GTEX_LINK_` prefix:

- `GTEX_LINK_HOST` (default `127.0.0.1`)
- `GTEX_LINK_PORT` (default `8000`)
- `GTEX_LINK_LOG_LEVEL` (default `INFO`)
- `GTEX_LINK_LOG_FORMAT` (`console` or `json`, default `console`)
- `GTEX_LINK_TRANSPORT` (`unified` | `http`, default `unified`)
- `GTEX_LINK_MCP_PATH` (default `/mcp`)
- `GTEX_LINK_MCP_PROFILE` (`full` | `lite`, default `full`)
- `GTEX_LINK_API_RATE_LIMIT_PER_SECOND` (default `5.0`)
- `GTEX_LINK_CACHE_SIZE` (default `1000`)
- `GTEX_LINK_CACHE_TTL` (default `3600`)

## Caching

Multi-level:
- Service-level async LRU cache for processed results
- Client-level HTTP response caching with TTL

## Error Hierarchy

- `GTExAPIError` - base
- `RateLimitError` - 429 from upstream
- `ServiceUnavailableError` - upstream 503
- `ValidationError` - input validation
- `ConfigurationError`, `CacheError` - misc

## Rate Limiting

Token-bucket algorithm:
- Default 5 req/s, burst 10
- Exponential backoff for retries
