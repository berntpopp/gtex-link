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
  `dataset_id` you passed**.
- **`_meta.gencode_version`** is the GENCODE release the gene IDs were resolved
  against. It is the load-bearing fact: `PKD1` is `ENSG00000008710.19` under `v26`
  but `.20` under `v39`.
- **`_meta.dataset_id`** echoes the dataset argument back.

So a call with `dataset_id="gtex_v10"` returns `_meta = {..., "gtex_release":
"gtex_v10", "gencode_version": "v39", "dataset_id": "gtex_v10"}`.

#### Which tools carry `_meta`

Not every tool has a `_meta` frame. This table is **machine-owned**:
`tests/test_mcp/test_provenance_meta.py` parses it and calls every tool through
the real MCP facade, so a wrong `yes`/`no` here fails CI.

| Tool | `_meta` | `gtex_release` reports |
|---|---|---|
| `get_median_expression_levels` | yes | the `dataset_id` you passed (+ `gencode_version`, `dataset_id`) |
| `get_individual_expression_data` | yes | the `dataset_id` you passed (+ `gencode_version`, `dataset_id`) |
| `get_top_expressed_genes_by_tissue` | yes | the `dataset_id` you passed (+ `gencode_version`, `dataset_id`) |
| `search` | yes | the server default (takes no `dataset_id`; no `gencode_version`) |
| `search_genes` | yes | the server default (takes no `dataset_id`; no `gencode_version`) |
| `get_gene_information` | yes | the server default (takes no `dataset_id`; no `gencode_version`) |
| `get_transcript_information` | yes | the server default (takes no `dataset_id`; no `gencode_version`) |
| `fetch` | no | nothing — it returns the flat OpenAI Apps-SDK / deep-research document (`id`, `title`, `text`, `url`, `metadata`), a contractual shape with no `_meta` slot. Its `metadata.source` is a static label, **not** provenance |
| `get_server_capabilities` | no | nothing — it *is* the provenance document: `gtex_release` and `default_dataset_id` there are the server **default**, and `dataset_gencode_versions` is the full map |

The server default is `GTEX_DATA_RELEASE` in `gtex_link/mcp/resources.py`
(currently `gtex_v8`), served as `default_dataset_id` by `get_server_capabilities`.

**Security note.** `dataset_id` is caller-supplied. The sanitized value is echoed
back in `_meta.dataset_id`, but `gtex_release` and `gencode_version` are **never**
caller-controlled: they are derived **only** from a dataset that is a known key of
`DATASET_GENCODE_VERSION`, and only ever take values from that map. An unknown
`dataset_id` is rejected with `invalid_input` before any upstream call, and its
error envelope keeps the server default release — so on an *error* envelope
`_meta.dataset_id` and `_meta.gtex_release` can legitimately disagree (the release
is matched on the raw argument, never on a sanitized one the validator rejected).
An error envelope carries no rows, so nothing is mislabelled. See
`_provenance_meta` in `gtex_link/mcp/envelope.py`.

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

Every response that carries a `_meta` frame (see the table above — every tool
except `fetch` and `get_server_capabilities`) stamps this string verbatim in
`_meta.recommended_citation`. It is also served at the `gtex://citations` MCP
resource and as `citation` in `get_server_capabilities`. Paste it verbatim; do
not paraphrase it.

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
  chain without guessing the next tool. It is emitted by `search_genes`,
  `get_median_expression_levels`, and `get_top_expressed_genes_by_tissue` (the
  tools that have an obvious next step), not by every tool.
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
