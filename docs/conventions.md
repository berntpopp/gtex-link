# GTEx-Link Conventions

## Code Style

- Line length: 100 characters
- String quotes: double quotes (`"`)
- Imports: ruff `I` (isort)
- Docstring style: Google
- Strict mypy; no untyped defs

## Test Data Standards

Tests use a consistent set of genomic identifiers and tissues so fixtures
are interchangeable across files.

- **Genes**: `BRCA1`, `BRCA2`, `TP53`, `CFH`, `APOE`
- **Tissues**: `Muscle_Skeletal`, `Whole_Blood`, `Brain_Cortex`, `Liver`
- **Dataset**: `gtex_v8`

## Test Organization

- `tests/unit/` - unit tests for individual components
- `tests/test_api/` - FastAPI route tests
- `tests/test_models/` - Pydantic model tests
- `tests/test_services/` - service-layer tests
- `tests/test_client/` - HTTP client tests
- `tests/integration/` - end-to-end integration tests
- `tests/fixtures/` - shared GTEx response fixtures
- `tests/conftest.py` - shared pytest fixtures

## Test Markers

- `unit` - unit tests
- `integration` - integration tests
- `slow` - long-running tests
- `api` - tests that exercise FastAPI surface
- `mcp` - tests that exercise MCP surface

## Mocking

- Outbound HTTP calls are mocked with `respx`.
- Internal collaborators are mocked with `pytest-mock`'s `mocker` where appropriate.
- Avoid monkeypatching httpx internals; respx intercepts at the transport layer.

## GTEx API Response Conventions

- Responses include pagination metadata: `page`, `itemsPerPage`,
  `totalItems`, `totalPages`.
- Field names: snake_case in the upstream API; matched by Pydantic models.
- Null values appear for missing expression data — handle as `Optional`.

## Pagination

Most endpoints accept `page` and `itemsPerPage`. Defaults vary; consult the
per-endpoint docs in `docs/api_v2_*.md`.
