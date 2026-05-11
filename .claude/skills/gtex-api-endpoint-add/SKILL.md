---
name: gtex-api-endpoint-add
description: Use when wiring a new upstream GTEx Portal endpoint into gtex-link. Walks through the spec, models, service, route, tests, and MCP exposure decision.
---

# Add a new GTEx Portal endpoint

## Locate the endpoint spec

1. Open `docs/gtex-openapi-spec-formatted.json` and find the path you want.
2. Cross-reference the per-endpoint markdown under `docs/api_v2_<category>_<endpoint>_<method>.md`.

## Wire the models

1. Add the request model to `gtex_link/models/requests.py`. Map field aliases to GTEx Portal query parameter names (camelCase).
2. Add the response model to `gtex_link/models/responses.py`. Match upstream field names exactly.

## Wire the service

1. Open `gtex_link/services/gtex_service.py`.
2. Add an async method on `GTExService` that:
   - Builds the URL from `settings.api.endpoints[<key>]`.
   - Calls `self._client.get(...)` or `.post(...)`.
   - Wraps the response in the response model.
   - Uses `async_lru` caching where idempotent.

## Wire the route

1. Add a handler under `gtex_link/api/routes/<category>.py` (create the file if missing and register the router in `gtex_link/api/routes/__init__.py` and `gtex_link/app.py`).
2. Use `Depends(GTExService)`.

## Tests

1. **Route test** under `tests/test_api/test_<category>_routes.py`:
   - Use `respx` to mock `https://gtexportal.org/api/v2/<path>`.
   - Hit the route via the FastAPI test client.
   - Assert response shape.
2. **Service test** under `tests/test_services/`.
3. **Model tests** under `tests/test_models/`.

## MCP exposure

Decide:
- Should this be an MCP tool? If yes, run the `mcp-tool-change` skill.
- Add to `full` profile, and to `lite` only if it's a common-path tool.

## Update docs

- Add a section in `docs/README.md` if this is a new category.
- Regenerate per-endpoint docs from the OpenAPI spec:
  ```bash
  cd docs && python generate_endpoint_docs.py
  ```

## CI

Run `make ci-local`.
