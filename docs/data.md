# GTEx-Link Data & Provenance

## Upstream

All data are served live from the **GTEx Portal v2 API**,
`https://gtexportal.org/api/v2/` — a public endpoint that requires **no
authentication, no API key, and no registration**.

## Datasets

The upstream API exposes three datasets, and the expression tools
(`get_median_expression_levels`, `get_individual_expression_data`,
`get_top_expressed_genes_by_tissue`) take a **`dataset_id` argument** to choose
between them. Each is annotated against a different **GENCODE release**, so the
gene identifiers differ per dataset — GTEx-Link resolves symbols to the
requested dataset's release for you (`DATASET_GENCODE_VERSION` in
`gtex_link/models/gtex.py`).

| `dataset_id` | GENCODE | Notes |
|---|---|---|
| `gtex_v8` | `v26` | **Default** for every tool that takes `dataset_id`. |
| `gtex_v10` | `v39` | Newer release; a gene absent from v39 simply returns no rows. |
| `gtex_snrnaseq_pilot` | `v26` | Single-nucleus RNA-seq pilot. |

`get_server_capabilities` serves this same table live (`datasets`,
`dataset_gencode_versions`), which is the authoritative copy.

### What the provenance `_meta` actually says

Read the two provenance keys carefully — they are not the same thing:

- **`_meta.gtex_release`** is a **server constant** (`GTEX_DATA_RELEASE` in
  `gtex_link/mcp/resources.py`, currently `gtex_v8`). It reports the server's
  default release and is stamped on **every** response unconditionally. It does
  **not** follow the `dataset_id` you passed.
- **`_meta.dataset_id`** is echoed back **only** by the expression tools, and it
  *is* the dataset that was actually queried.

So a call with `dataset_id="gtex_v10"` returns
`_meta = {..., "gtex_release": "gtex_v8", "dataset_id": "gtex_v10"}`. When the
two disagree, **`dataset_id` is the one that describes the data in front of
you**. (The unconditional `gtex_release` stamp is a known wart; see
`gtex_link/mcp/envelope.py`.)

## Refresh model: none needed

GTEx-Link ships **no data bundle, no SQLite mirror, and no ingest step**. There
is no `make data`, nothing to build before first run, and no volume to persist.
Every tool call proxies the live GTEx Portal API, fronted by an in-process
TTL + LRU cache (`GTEX_LINK_CACHE__TTL`, default 3600s;
`GTEX_LINK_CACHE__SIZE`, default 1000 items).

Freshness therefore tracks the GTEx Portal directly: when GTEx publishes, the
server serves it as soon as cached entries expire.

## Upstream rate limit

The client applies a **token-bucket limiter defaulting to 5 requests/second**
with a burst of 10 (`GTEX_LINK_API__RATE_LIMIT_PER_SECOND`,
`GTEX_LINK_API__BURST_SIZE`), plus up to 3 retries with exponential backoff.

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
- **Error codes**: `not_found`, `invalid_input`, `rate_limited`,
  `upstream_unavailable`, `output_limit_exceeded`, `internal_error` — the same
  six that `get_server_capabilities` advertises, pinned to the set the error
  envelope can actually emit. Errors carry `retryable` and a `recovery_action`
  (`retry_backoff` | `reformulate_input` | `switch_tool`), and validation
  failures add `field_errors`.

## MCP resources

Alongside the tools, the server exposes a `gtex://` resource family:
`gtex://capabilities`, `gtex://usage`, `gtex://reference`,
`gtex://research-use`, and `gtex://citations`.

## Upstream endpoint reference

The full GTEx Portal v2 endpoint catalogue — generated from the upstream
OpenAPI specification — lives in [`README.md`](README.md) and the
`api_v2_*.md` files in this directory.
