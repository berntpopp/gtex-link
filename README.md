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

#### HTTP Server

```bash
# Start the development HTTP server
make dev

# Start HTTP server with custom options
uv run gtex-link server --host 127.0.0.1 --port 8000

# With auto-reload for development
uv run gtex-link server --reload
```

#### MCP Server

```bash
# Start MCP stdio server
make mcp-serve

# Start hosted MCP endpoint with REST API
make mcp-serve-http

# Direct console scripts
uv run gtex-link-mcp
uv run gtex-mcp  # compatibility alias
```

#### Test Connection

```bash
# Test GTEx Portal API connectivity
uv run gtex-link test

# Search for genes
uv run gtex-link search BRCA1 --limit 5

# Show configuration
uv run gtex-link config
```

### Docker Usage

```bash
# Local REST API on non-standard host port 8020
docker compose -f docker/docker-compose.yml up -d --build
curl http://localhost:8020/api/health/

# MCP HTTP endpoint on non-standard host port 8021
docker compose -f docker/docker-compose.mcp.yml up -d --build

# Development with hot reload on host port 8020
docker compose -f docker/docker-compose.dev.yml up --build
```

Docker publishes GTEx-Link on `8020` for REST and `8021` for MCP by default so
it can run beside sibling projects that commonly use `8000` and `8001`.
Override with `GTEX_LINK_HOST_PORT` and `GTEX_LINK_MCP_HOST_PORT`.

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

### Available Tools
- `search_gtex_genes` - Search for genes in GTEx database
- `get_gene_information` - Get detailed gene information
- `get_median_expression_levels` - Get median expression data
- `get_expression_qtl_associations` - Get eQTL association data
- `get_top_expressed_genes_by_tissue` - Get top expressed genes

### Claude Desktop Configuration

Add to your Claude Desktop configuration:

```json
{
  "mcpServers": {
    "gtex-link": {
      "command": "gtex-link-mcp",
      "env": {
        "GTEX_LINK_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

Existing configurations that use `gtex-mcp` continue to work as a compatibility alias.

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
- `GTEX_LINK_TRANSPORT_MODE` - Transport mode: http/stdio (default: http)

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
