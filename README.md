# GTEx-Link

High-performance MCP/API server for the GTEx Portal genetic expression database.

## Overview

GTEx-Link is a production-ready server that provides both REST API and Model Context Protocol (MCP) interfaces to the GTEx Portal v2 API. It offers:

- **Dual Protocol Support**: Both HTTP REST API and MCP protocol
- **High Performance**: Built with FastAPI and async/await patterns
- **Robust Caching**: Intelligent caching with configurable TTL and size limits
- **Rate Limiting**: Token bucket rate limiting to be respectful to GTEx Portal
- **Type Safety**: Full type hints and Pydantic models based on OpenAPI spec
- **Production Ready**: Docker support, structured logging, health checks
- **Comprehensive Coverage**: Support for genes, expression, eQTL/sQTL associations

## Quick Start

### Installation

```bash
# Install uv if needed
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and install
git clone https://github.com/gtex-link/gtex-link.git
cd gtex-link
make install

# Run local CI-equivalent checks
make ci-local
```

### Basic Usage

#### Server (Streamable HTTP)

GTEx-Link is a single `typer` CLI. The server always boots via
`gtex-link serve` — there is no bare-serve and no stdio transport.

```bash
# Start the unified server (FastAPI REST + MCP at /mcp) — development
make dev

# Unified transport with custom options
uv run gtex-link serve --transport unified --host 127.0.0.1 --port 8000

# REST API only (no MCP)
uv run gtex-link serve --transport http --host 127.0.0.1 --port 8000

# Development mode (verbose console logging)
uv run gtex-link serve --dev
```

#### Other commands

```bash
# Show (and optionally validate) the resolved configuration
uv run gtex-link config
uv run gtex-link config --validate

# Probe a running server's /api/health endpoint
uv run gtex-link health --url http://127.0.0.1:8000

# Inspect or clear the in-process service cache
uv run gtex-link cache stats
uv run gtex-link cache clear

# Print the installed version
uv run gtex-link version
```

### Docker Usage

```bash
# Local unified server (REST + MCP at /mcp) on non-standard host port 8765
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8765/api/health
curl http://localhost:8765/mcp

# Development with hot reload on host port 8765
docker compose -f docker/docker-compose.dev.yml up --build
```

Docker publishes GTEx-Link on `8765` (mapped to container port `8000`) by
default so it can run beside sibling projects that commonly use `8000`/`8001`.
The unified server exposes both REST and MCP (`/mcp`) on that single port.
Override the host port with `GTEX_LINK_HOST_PORT`.

Every HTTP route is protected by exact Host and browser Origin allowlists. The
defaults admit only `localhost`, `127.0.0.1`, and IPv6 loopback (`::1`). Add the
public proxy hostname explicitly for deployment; do not include a scheme or
port, and write IPv6 as bare `::1`, not `[::1]`. Wildcard Host or Origin
patterns (`*`, `?`, or bracket expressions) are rejected at configuration time.

## API Endpoints

### Reference Data
- `GET /api/reference/genes/search` - Search genes by symbol or ID
- `GET /api/reference/genes` - Get gene information with filtering
- `GET /api/reference/transcripts` - Get transcript information

### Expression Data
- `GET /api/expression/median-gene-expression` - Median gene expression across tissues
- `GET /api/expression/gene-expression` - Individual sample expression data
- `GET /api/expression/top-expressed-genes` - Top expressed genes by tissue

### Association Data
- `GET /api/association/single-tissue-eqtl` - Expression QTL associations
- `GET /api/association/single-tissue-sqtl` - Splicing QTL associations
- `GET /api/association/egenes` - Genes with significant eQTLs
- `GET /api/association/sgenes` - Genes with significant sQTLs

### Health & Monitoring
- `GET /api/health/` - Basic health check
- `GET /api/health/ready` - Readiness check with GTEx API connectivity
- `GET /api/health/stats` - Service performance statistics

## MCP Integration

GTEx-Link provides MCP tools for seamless integration with AI assistants:

### Gateway namespace token

GTEx-Link is designed to federate behind the
[`genefoundry-router`](https://github.com/berntpopp/genefoundry-router) MCP
gateway, which applies the namespace at mount time. The canonical gateway
**namespace token** for this server is **`gtex`**: the gateway mounts this
server with `mount(namespace="gtex")`, so leaf tool `get_gene_information`
surfaces as `gtex_get_gene_information`. Leaf tool names are therefore kept
**unprefixed** here (the gateway adds the prefix); a leaf-level `gtex_` prefix
would double-prefix to `gtex_gtex_...`. Tool names follow the GeneFoundry
Tool-Naming Standard v1 (`verb_noun`, canonical verbs, ≤ 50 chars).

### Available Tools
- `search` - ChatGPT deep-research entry point: natural-language gene search
  (returns result documents with `id`/`title`/`url`)
- `fetch` - ChatGPT deep-research companion: full gene detail for a `search` `id`
- `search_genes` - Search the GTEx Portal gene catalog by symbol or partial match
- `get_gene_information` - Get detailed gene information for GENCODE IDs or symbols
- `get_transcript_information` - Get transcript annotations for a GENCODE ID
- `get_median_expression_levels` - Get median expression (TPM) per tissue
- `get_individual_expression_data` - Get individual-sample expression (TPM)
- `get_top_expressed_genes_by_tissue` - Get top expressed genes for a tissue
- `get_server_capabilities` - Discover tools, datasets, tissues, limits, and workflows

The `search` / `fetch` pair is the OpenAI deep-research / Apps SDK contract and
is retained verbatim (a documented exception to the canonical-verb rule).
Pagination arguments use the fleet-canonical `offset` / `limit`.

### MCP Client Configuration (Streamable HTTP)

GTEx-Link serves MCP over Streamable HTTP only (there is no stdio transport).
Start the unified server and point an HTTP-capable MCP client at the `/mcp`
endpoint:

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

## Configuration

GTEx-Link can be configured via environment variables or `.env` file:

### API Configuration
- `GTEX_LINK_API_BASE_URL` - GTEx Portal API base URL (default: https://gtexportal.org/api/v2/)
- `GTEX_LINK_API_TIMEOUT` - Request timeout in seconds (default: 30)
- `GTEX_LINK_API_RATE_LIMIT_PER_SECOND` - Rate limit (default: 5.0)
- `GTEX_LINK_API_BURST_SIZE` - Burst size for rate limiting (default: 10)
- `GTEX_LINK_API_MAX_RETRIES` - Maximum retry attempts (default: 3)

### Server Configuration
- `GTEX_LINK_HOST` - Server host (default: 127.0.0.1)
- `GTEX_LINK_PORT` - Server port (default: 8000)
- `GTEX_LINK_TRANSPORT` - Transport mode: unified/http (default: unified)
- `GTEX_LINK_MCP_PROFILE` - MCP tool profile: full/lite (default: full)
- `GTEX_LINK_MCP_PATH` - MCP endpoint path (default: /mcp)
- `GTEX_LINK_ALLOWED_HOSTS` - Exact JSON Host list (default: `["localhost","127.0.0.1","::1"]`)
- `GTEX_LINK_ALLOWED_ORIGINS` - Exact JSON browser Origin list (default: `[]`)

`GTEX_LINK_ALLOWED_ORIGINS` is the request-boundary policy;
`GTEX_LINK_CORS_ORIGINS` controls browser response headers. Keep both lists in
sync for browser clients. Requests without an `Origin` header, such as normal
router-to-backend MCP traffic, remain allowed when their Host is trusted.

### Caching Configuration
- `GTEX_LINK_CACHE_SIZE` - Maximum cached items (default: 1000)
- `GTEX_LINK_CACHE_TTL` - Cache TTL in seconds (default: 3600)

### Logging Configuration
- `GTEX_LINK_LOG_LEVEL` - Logging level (default: INFO)
- `GTEX_LINK_LOG_FORMAT` - Log format: console/json (default: console)

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/gtex-link/gtex-link.git
cd gtex-link

# Install project and development dependencies
make install

# Install pre-commit hooks
uv run pre-commit install
```

### Run Tests

```bash
# Run tests
make test

# Run fast parallel tests
make test-fast

# Run with coverage
make test-cov

# Run specific test categories
uv run pytest -m "not integration"
uv run pytest -m "unit"
```

### Code Quality

```bash
# Format code
make format

# Lint code
make lint

# Type check
make typecheck

# Full local CI-equivalent check
make ci-local
```

## Architecture

GTEx-Link follows clean architecture principles:

```
gtex_link/
├── api/                 # API layer (FastAPI routes)
│   ├── client.py       # GTEx Portal API client
│   └── routes/         # HTTP route handlers
├── services/           # Business logic layer
│   └── gtex_service.py # Core GTEx service
├── models/             # Data models (Pydantic)
│   ├── gtex.py        # GTEx-specific enums
│   ├── requests.py    # Request models
│   └── responses.py   # Response models
├── utils/              # Utilities
│   └── caching.py     # Caching utilities
├── config.py          # Configuration management
├── exceptions.py      # Custom exceptions
└── logging_config.py  # Logging configuration
```

### Key Components

- **GTExClient**: HTTP client with rate limiting and retry logic
- **GTExService**: Business logic layer with caching
- **Pydantic Models**: Type-safe data models from OpenAPI spec
- **FastAPI Routes**: RESTful API endpoints
- **FastMCP Integration**: MCP protocol support

## Performance

GTEx-Link is optimized for performance:

- **Async/Await**: Non-blocking I/O operations
- **Connection Pooling**: Efficient HTTP connection reuse
- **Intelligent Caching**: Multi-level caching with LRU eviction
- **Rate Limiting**: Token bucket algorithm prevents API overload
- **Lazy Loading**: Resources loaded only when needed

### Benchmarks

Typical performance characteristics:
- Cold start: ~50ms for gene search
- Warm cache: ~5ms for cached responses
- Memory usage: ~50MB base + cache size
- Concurrent requests: 100+ req/sec sustained

## Error Handling

GTEx-Link provides comprehensive error handling:

- **Validation Errors**: 400 Bad Request with field details
- **Rate Limiting**: 429 Too Many Requests with retry hints
- **API Errors**: 502 Bad Gateway for upstream issues
- **Service Errors**: 503 Service Unavailable for health failures

## Monitoring

### Health Checks
- Basic health: `GET /api/health/`
- Readiness: `GET /api/health/ready`
- Statistics: `GET /api/health/stats`

### Metrics
- Request/response times
- Cache hit/miss rates
- API success rates
- Error counts by type

### Logging

Structured logging with configurable output:
- JSON format for production
- Console format for development
- Correlation IDs for request tracing
- Performance metrics

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Add tests for your changes
5. Ensure all tests pass (`pytest`)
6. Commit your changes (`git commit -m 'Add amazing feature'`)
7. Push to the branch (`git push origin feature/amazing-feature`)
8. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- GTEx Portal team for providing the public API
- FastMCP team for MCP protocol implementation
- FastAPI team for the excellent web framework

## Support

- **Documentation**: [Full documentation](https://gtex-link.readthedocs.io)
- **Issues**: [GitHub Issues](https://github.com/gtex-link/gtex-link/issues)
- **Discussions**: [GitHub Discussions](https://github.com/gtex-link/gtex-link/discussions)

## Roadmap

- [ ] GraphQL endpoint support
- [ ] WebSocket real-time updates
- [ ] Advanced query optimization
- [ ] Multi-tenant support
- [ ] Prometheus metrics export
- [ ] Kubernetes deployment guides
