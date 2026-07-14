# GTEx-Link Data & Provenance

## Upstream

All data are served live from the **GTEx Portal v2 API**,
`https://gtexportal.org/api/v2/` — a public endpoint that requires **no
authentication, no API key, and no registration**.

The default dataset is **`gtex_v8`** (`GTEX_DATA_RELEASE` in
`gtex_link/mcp/resources.py`), and it is stamped into the provenance `_meta` of
every response and into `get_server_capabilities`.

## Refresh model: none needed

GTEx-Link ships **no data bundle, no SQLite mirror, and no ingest step**. There
is no `make data`, nothing to build before first run, and no volume to persist.
Every tool call proxies the live GTEx Portal API, fronted by an in-process
TTL + LRU cache (`GTEX_LINK_CACHE_TTL`, default 3600s;
`GTEX_LINK_CACHE_SIZE`, default 1000 items).

Freshness therefore tracks the GTEx Portal directly: when GTEx publishes, the
server serves it as soon as cached entries expire.

## Upstream rate limit

The client applies a **token-bucket limiter defaulting to 5 requests/second**
with a burst of 10 (`GTEX_LINK_API_RATE_LIMIT_PER_SECOND`,
`GTEX_LINK_API_BURST_SIZE`), plus up to 3 retries with exponential backoff.

This is **courtesy to a free public service, not a local throttle**. Do not
raise it casually. Upstream 429s surface as the `rate_limited` error code with
a `retry_backoff` recovery action.

## Licence

- **Code**: MIT — see [`LICENSE`](../LICENSE).
- **Data**: GTEx Portal data are governed by the GTEx Portal's own terms —
  <https://gtexportal.org/home/license>. GTEx-Link touches **only open-access
  GTEx data** (the v2 API needs no credentials). Protected, individual-level
  GTEx genotype data are dbGaP-controlled and are **not** reachable through this
  server or its upstream API.

## Required citation

Every successful response carries this string verbatim in
`_meta.recommended_citation`, and it is also served at the `gtex://citations`
MCP resource. Paste it verbatim; do not paraphrase it.

> GTEx Consortium. The GTEx Consortium atlas of genetic regulatory effects
> across human tissues. Science. 2020;369(6509):1318-1330.
> doi:10.1126/science.aaz1776

## Response conventions

- **Identifiers**: gene symbols and versioned GENCODE IDs are both accepted;
  symbols are auto-resolved to GENCODE IDs.
- **`response_mode`**: `compact` (default) or `full`. Start compact; widen only
  when needed to control token cost. Spread statistics
  (min/max/quartiles/IQR) are opt-in via `include_spread`.
- **Pagination**: fleet-canonical `offset` / `limit` on the MCP surface. (The
  upstream GTEx API itself paginates with `page` / `itemsPerPage`; see
  [conventions.md](conventions.md).)
- **`numSamples`** is the per-tissue RNA-seq sample denominator, and is
  **gene-independent** — it does not vary with the gene you queried.
- **`_meta.next_commands`** carries ready-to-run follow-up calls so a client can
  chain without guessing the next tool.
- **Error codes**: `not_found`, `invalid_input`, `validation_failed`,
  `rate_limited`, `upstream_unavailable`, `internal_error`. Errors carry
  `retryable` and a `recovery_action` (`retry_backoff` | `reformulate_input` |
  `switch_tool`), and validation failures add `field_errors`.

## MCP resources

Alongside the tools, the server exposes a `gtex://` resource family:
`gtex://capabilities`, `gtex://usage`, `gtex://reference`,
`gtex://research-use`, and `gtex://citations`.

## Upstream endpoint reference

The full GTEx Portal v2 endpoint catalogue — generated from the upstream
OpenAPI specification — lives in [`README.md`](README.md) and the
`api_v2_*.md` files in this directory.
