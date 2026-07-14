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

Provenance names the release the data in front of you **actually came from**:

- **`_meta.gtex_release`** is the release that was queried — it **follows the
  `dataset_id` you passed**. Tools that take no `dataset_id` (`search`, `fetch`,
  `search_genes`, `get_gene_information`, `get_transcript_information`) report the
  server default instead (`GTEX_DATA_RELEASE` in `gtex_link/mcp/resources.py`,
  currently `gtex_v8`; also served as `default_dataset_id` in
  `get_server_capabilities`).
- **`_meta.gencode_version`** is the GENCODE release the gene IDs were resolved
  against, and is present on dataset-scoped calls only. It is the load-bearing
  fact: `PKD1` is `ENSG00000008710.19` under `v26` but `.20` under `v39`.
- **`_meta.dataset_id`** echoes the dataset argument back, and is likewise present
  on the expression tools only.

So a call with `dataset_id="gtex_v10"` returns `_meta = {..., "gtex_release":
"gtex_v10", "gencode_version": "v39", "dataset_id": "gtex_v10"}`.

**Security note.** `dataset_id` is caller-supplied, so `gtex_release` is derived
**only** from a dataset that is a known key of `DATASET_GENCODE_VERSION` — never
echoed from the raw argument. An unknown or invalid `dataset_id` fails request
validation, and its error envelope (which carries `_meta` too) keeps the server
default release. See `_provenance_meta` in `gtex_link/mcp/envelope.py`.

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
