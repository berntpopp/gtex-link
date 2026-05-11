---
name: fastapi-route-change
description: Use when adding or modifying a FastAPI route in gtex-link. Walks through request/response models, route handler, service wiring, and tests.
---

# FastAPI route change

Use this skill when adding or modifying a FastAPI route under `gtex_link/api/routes/`.

## Checklist

1. **Request model.** Define or extend a Pydantic model in `gtex_link/models/requests.py`. Field aliases map to GTEx Portal query parameters. Set sensible defaults and validators.
2. **Response model.** Define or extend the matching response model in `gtex_link/models/responses.py`. Match upstream field names.
3. **Service method.** Add or update a method on `GTExService` in `gtex_link/services/gtex_service.py`. Wrap upstream calls in the existing caching/rate-limiting paths. Do not bypass `GTExClient`.
4. **Route handler.** Add the route in the appropriate file under `gtex_link/api/routes/`. Reuse FastAPI `Depends` for `GTExService`. Return the Pydantic response model.
5. **Tests.**
   - Route test under `tests/test_api/test_<category>_routes.py` using `respx` to stub `https://gtexportal.org/api/v2/...`.
   - Service test under `tests/test_services/` for the new service method.
6. **Docs.** If the route exposes a new GTEx endpoint, update `docs/README.md` and add per-endpoint markdown via `python docs/generate_endpoint_docs.py` when the openapi spec is updated.
7. **MCP exposure.** Decide if this should be an MCP tool (see `mcp-tool-change` skill if yes).
8. **CI.** Run `make ci-local` before pushing.
