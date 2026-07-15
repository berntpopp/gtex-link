# Changelog

All notable changes to GTEx-Link are documented here. The format is based on
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this project
adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Re-vendored the behaviour conformance gate from genefoundry-router `56db958`
  (`docs/conformance/behaviour.py` blob `c69801687`) so live MCP contract checks
  treat not-found example probes as inconclusive and keep empty auxiliary objects from hiding counted rows.

## [3.1.0] - 2026-07-15
### Fixed

- **The median headline stated the opposite of the data for `sort=asc`/`sort=none`.**
  `median_headline` hardcoded "highest median in …" regardless of sort order, so
  `get_median_expression_levels {"gencode_id":["UMOD"],"sort":"asc","top_n":3}`
  reported *"UMOD: highest median in Adipose_Subcutaneous (0.00 TPM)"* — the
  least-expressed tissue, for a kidney gene whose true peak is Kidney_Medulla at
  2116 TPM. The headline now follows the sort: "highest" for `desc`, "lowest" for
  `asc`, and an unsorted phrasing (no superlative) for `none`. (issue #76 D1)
- **`search` dropped the gene the query actually named.** Recall tokenised the query
  positionally and capped at `MAX_QUERY_TOKENS`, so a gene named late in a clinical
  sentence was evicted by earlier English words that prefix-match gene symbols
  (`met` → METTL\*, `six` → SIX\*): *"…is SCN1A expressed in brain cortex?"* returned
  20 methyltransferases and no SCN1A, with `success:true`. Recall now orders
  gene-shaped tokens (digit-bearing or all-caps) first, so the queried gene survives
  the cap and its exact-symbol match ranks first. An empty result now carries a
  `note` explaining no gene-like term matched, and the result set is bounded.
  (issue #76 D2/D6)
- **A negative `top_n` silently deleted real tissues.** `top_n` had no lower bound,
  so a negative value negative-sliced the tissue list and returned `success:true`
  with rows removed — with `sort=asc` it deleted the *highest*-expressed tissues
  (both kidney rows for a UMOD query). `top_n` now carries a minimum of 1 and is
  rejected as `invalid_input`; `group_median` also guards `top_n > 0`. (issue #76 D3)
- **Tool-execution error envelopes were returned with MCP `isError:false`.** Domain
  errors (`not_found`, `invalid_input`, …) came back as `success:false` in the body
  but `isError:false` at the protocol level, so a client branching on `isError` saw
  a successful call. The dispatch middleware now promotes every error envelope to
  `isError:true`. (issue #76 D9; Response-Envelope Standard v1)
- **Argument-validation errors named no parameter.** A bad or unknown argument
  produced a generic *"Invalid arguments for this tool…"* the model could not act
  on. The error now names the SPECIFIC failing parameter and reason (e.g.
  `` `top_n`: Input should be greater than or equal to 1``) in `field_errors`,
  plus the tool's own parameters (`allowed_values`) and any unexpected argument
  key(s); no caller *value* is ever echoed. (issue #76 D4/#4/#2)
- **`get_top_expressed_genes_by_tissue` silently returned `data:[]` for a valid
  tissue in a dataset that does not measure it** (e.g. any tissue against the
  snRNA-seq pilot, whose served tissue set is empty). That silent-empty is now a
  loud `invalid_input` naming `tissue_site_detail_id`, instead of a confident empty
  answer. (issue #76 #1)

### Changed

- **Every tool input parameter is now documented (0% → 100%).** Each property
  carries a `description`; every required/array parameter carries `examples`; and
  the four closed vocabularies — `tissue_site_detail_id`, `dataset_id`,
  `gencode_version`, `genome_build` — are declared as schema enums, so a model reads
  valid values from the schema instead of learning them from a failed call. The
  advertised tissue enum excludes the internal `""` all-tissues sentinel AND the
  spec's one legacy name `Cells_Transformed_fibroblasts` (renamed to
  `Cells_Cultured_fibroblasts` in v8; the live API serves 54 tissues and no data
  under the old name), so the schema is never wider than the runtime. (issue #76
  D4/#5/#3; Tool-Schema Documentation v1)
- **`_meta.pagination.{total_count, has_more}`** is now emitted on every paginated
  result, derived from GTEx's `pagingInfo`. `total_count` is the whole-result size
  (invariant under `limit`), so a client — and the fleet behaviour gate — can read
  gtex's collections without knowing GTEx's own camelCase shape. (Response-Envelope v1)
- **`error_code` is now the fleet's closed enum.** `internal_error` → `internal`
  and `output_limit_exceeded` → `invalid_input`, so every emitted and advertised
  code is one of `invalid_input · not_found · ambiguous_query · upstream_unavailable
  · rate_limited · internal`. (Response-Envelope Standard v1)
- **Tool surface trimmed.** `outputSchema` (52% of the advertised surface, unread by
  models and optional in MCP) is suppressed on every tool via `output_schema=None`
  (`structuredContent` is still emitted for the dict envelopes), and
  `dereference_schemas=False` keeps input schemas inline. Surface ~4,072t → ~3.7k;
  no tool over 1,200t (the median tool's scalar-or-list tissue parameter uses a
  `$ref`-shared enum so the 54-value vocabulary is not inlined twice).
  (Tool-Surface Budget Standard v1)

### Added

- Vendored the **Behaviour Conformance v1** gate (`tests/conformance/behaviour.py`
  + `test_behaviour_v1.py`) and wired its probe into the `mcp-conformance` workflow.
- A real per-tool **tool-surface budget** test asserting the live `tools/list`
  schema stays within B1 (≤1,200t/tool) and B2 (<10,000t total).
- Drift guards pinning the schema enums to their source of truth — the tissue
  vocabulary against the vendored OpenAPI spec (minus documented deprecations).

## [3.0.6] - 2026-07-14
### Fixed

- **`_meta.gtex_release` lied about which GTEx release the data came from.** It was
  a hardcoded constant (`gtex_v8`) stamped on every envelope, so a
  `dataset_id="gtex_v10"` call returned v10 rows while reporting
  `gtex_release: "gtex_v8"`. Because each dataset is annotated against a different
  GENCODE release (`gtex_v8`/`gtex_snrnaseq_pilot` -> `v26`, `gtex_v10` -> `v39`),
  that stamp re-introduced the release/GENCODE-mismatch hazard this server exists to
  remove. `gtex_release` now **follows `dataset_id`** on the three expression tools;
  tools that take no `dataset_id` still report the server default. `dataset_id` is
  caller-supplied, so the release fields are **never caller-controlled**: they are
  derived only from a known dataset (a key of `DATASET_GENCODE_VERSION`) and only
  ever take values from that map. (`_meta.dataset_id` continues to echo the
  *sanitized* caller value, as before.) An unknown dataset's error envelope keeps
  the server default release.
- **An unknown `dataset_id` did upstream work before it was rejected.** The
  expression tools resolved gene IDs *before* validating the request, and
  `gencode_version_for_dataset` silently defaulted an unknown dataset to `v26` — so
  `dataset_id="not_a_dataset"` resolved genes against the wrong GENCODE annotation
  upstream and only then failed validation. Unknown datasets are now rejected with
  `invalid_input` at the top of each dataset-scoped tool, before any upstream call,
  and `gencode_version_for_dataset` raises instead of guessing. The valid-value list
  is single-sourced from `DATASET_GENCODE_VERSION`; the caller's `dataset_id` is not
  echoed into the error message.

- **Nested settings never bound from the environment.** `ServerSettings` set no
  `env_nested_delimiter`, so every per-field name in the `api` and `cache` groups
  — `GTEX_LINK_CACHE_TTL`, `GTEX_LINK_CACHE_SIZE`,
  `GTEX_LINK_API_RATE_LIMIT_PER_SECOND`, `GTEX_LINK_API_TIMEOUT` and the rest —
  was silently discarded by `extra="ignore"`, despite being documented and passed
  by both Compose overlays. They now bind under the fleet-canonical
  `GTEX_LINK_<GROUP>__<FIELD>` spelling (**double underscore**), e.g.
  `GTEX_LINK_CACHE__TTL`. `.env.example`, `docker-compose.prod.yml` and
  `docker-compose.npm.yml` are updated.
  **Operator action**: rename any `GTEX_LINK_API_*` / `GTEX_LINK_CACHE_*`
  overrides to the `__` form. On the next redeploy the prod overlay's cache
  tuning (size `2000`, TTL `7200`) takes effect for the first time; it was inert
  before.
- **The advertised error taxonomy did not match the one the server emits.**
  `output_limit_exceeded` is reachable (a fenced over-cap response) but was
  absent from `get_server_capabilities` and `gtex://reference`, so clients wrote
  no branch for a recoverable failure; `validation_failed` was advertised but is
  never produced by the error envelope. The advertised set now equals the
  emittable set, pinned by a test.

- **Prose across the repo overclaimed the `_meta` provenance frame.** Two tools carry
  no `_meta` at all — `fetch` (the flat Apps-SDK document: `id`/`title`/`text`/`url`/
  `metadata`) and `get_server_capabilities` (its own document) — but the README, the
  `docs/`, and the strings the server itself ships said or implied otherwise:
  - `GTEX_SERVER_INSTRUCTIONS`, the first thing every connecting client reads, said
    GTEx-Link "exposes GTEx Portal **v8** expression data" (it serves three datasets)
    and promised every tool result carries a `success` flag and `_meta`.
  - The README claimed "every response" carries provenance, the citation, and
    `_meta.next_commands` (only `search_genes`, `get_median_expression_levels` and
    `get_top_expressed_genes_by_tissue` emit `next_commands`), then — on the first
    attempt to fix it — that `_meta` was on "all but `fetch`", still dropping
    `get_server_capabilities`. `get_server_capabilities.response_fields` had the same
    off-by-one omission.
  - `docs/data.md` said "every successful response" carries `_meta.recommended_citation`
    and that "every tool call" proxies the live API (`get_server_capabilities` is a
    static document and makes no upstream call).

  All are corrected, and the claims are now **machine-owned** by
  `tests/test_mcp/test_provenance_meta.py`, which classifies every registered tool by
  calling it through the real MCP facade and uses that as the oracle. It:
  - parses `docs/data.md`'s per-tool `_meta` table and checks each row against live tool
    behaviour; and
  - lints prose for `_meta` claims — failing CI if any claims `_meta` universality
    without scoping it, or names only *some* of the tools that lack `_meta`.

  The lint corpus is **globbed, not hand-listed** (a hand-listed corpus is what let these
  claims survive: the first version opened 5 of the repo's 61 markdown files). It covers
  `README.md`, every `docs/**/*.md`, and the client-facing strings the server ships
  (`gtex_link/mcp/resources.py`, `gtex_link/mcp/metadata.py`). It deliberately excludes,
  and a test enforces that nothing else is skipped:
  - `docs/superpowers/**` — dated design records. They state intent as of their date and
    rewriting them to match today's code would falsify the record, so they are *fenced*
    instead: each must carry a "Historical design record" banner, and CI fails if one
    does not. The archive cannot quietly become a source of false current claims.
  - `CHANGELOG.md` — this file narrates past behaviour by design.
  - Python `#` comments (internal notes, not claims shipped to a client) and the per-tool
    table rows (owned by the table check above).

### Added

- **`_meta.gencode_version`** on dataset-scoped calls: the GENCODE release the gene
  IDs were resolved against (additive, non-breaking).
- **`get_server_capabilities.default_dataset_id`** disambiguates the top-level
  `gtex_release` (the server default) from the new per-call provenance semantics,
  which `response_fields` now describes.

### Documentation

- README and `docs/data.md` said the server served a single dataset (`gtex_v8`)
  and stamped it into every response. Both halves were wrong: the expression
  tools take a `dataset_id` over three datasets (`gtex_v8`, `gtex_v10`,
  `gtex_snrnaseq_pilot`), each annotated against a different GENCODE release
  (`v26`, `v39`, `v26`). All three datasets, the GENCODE mapping, and the real
  provenance semantics (see Fixed, above) are now documented and machine-checked.
- `docs/configuration.md` is now exhaustive over `gtex_link/config.py`, with the
  flat-vs-nested env naming rule stated explicitly.

### Changed

- **The NPM deployment pulls the released image instead of building from source.**
  `docker/docker-compose.npm.yml` carried `build:`, so a deploy rebuilt the image on the
  server even though CI had already published an attested, digest-addressable image to
  GHCR. It now requires `GTEX_LINK_IMAGE` pinned to a digest and fails closed when it is
  unset. Nothing else in the overlay changed: `container_name`, the Compose project name,
  the healthcheck, networks and `command` are all preserved, so the deployed topology and
  its named volumes are untouched.

## [3.0.5] - 2026-07-13

### Fixed

- Re-pin the reusable container CI and container release workflows to the
  corrected GeneFoundry container release standard revision
  (`58d011d9c72efe90337244342fdec703f2b5b4b9`). The previously pinned revision
  carried latent release-pipeline defects that were fixed centrally, including
  GHCR authentication before the version alias push. Research use only.

## [3.0.4] - 2026-07-13

### Build

- Adopt the GeneFoundry container-release standard: add SHA-pinned central
  container CI/release callers, typed `container-release.json`, digest-only
  production Compose, complete OCI image labels, and normalized Docker context
  exclusions. Research use only; not for clinical decision support.

## [3.0.3] - 2026-07-12

### Fixed

- Release the HTTP policy v1 remediation, including bounded retries, redirect
  handling, and upstream request safety controls. Research use only; not for
  clinical decision support.

## [3.0.2] - 2026-07-11

### Security (defense in depth)

- **FastMCP-core not-found reflection guarded.** FastMCP core reflected the
  caller's own requested tool name / resource URI back to the caller (and to
  logs) before gtex-link middleware ran: an unknown tool surfaced as
  `Unknown tool: '<name>'` (raised on the direct path, returned as an isError
  `TextContent` via the client) and an unknown resource URI surfaced as
  `Unknown resource: '<uri>'`. A layered guard now closes this — a registry
  preflight in `on_call_tool` returns a fixed, name-free `not_found` envelope
  (no `_meta.tool` echo); `on_read_resource` re-raises a fixed, URI-free
  `ResourceError`; and an outermost protocol backstop wraps the raw
  tool/resource/prompt request handlers. A validation-log scrub filter also
  neutralizes the framework log records that reflected the raw name/URI (with its
  control/zero-width/bidi/NUL code points) into a log sink at every level — the
  FastMCP pre-middleware DEBUG traces (`Handler called`, `Tool cache miss`), the
  arg-validation WARNING, and the MCP SDK session's root-logger
  `Failed to validate request` / `Message that failed validation` records for a
  malformed or forbidden-code-point resource URI (rejected in request
  deserialization before any handler runs). Fixed messages are built from
  constants only (never the requested name/URI/`str(exc)`/request). No success
  schema or error-envelope shape changed. Research use only; not for clinical
  decision support.

## [3.0.1] - 2026-07-11

### Security (defense in depth)

- Caller-visible error messages and error `_meta` (incl. the caller-supplied
  `dataset_id`) are sanitized of control/zero-width/bidi/NUL code points;
  argument-validation returns a fixed `invalid_input` frame (no echoed input)
  with the raw validation log suppressed; the upstream GTEx Portal 4xx body and
  transport error text are no longer echoed or logged. Research use only.

## [3.0.0] - 2026-07-11

### Security (BREAKING)

- **Upstream GENCODE `description` now fenced as a typed `untrusted_text`
  object (Response-Envelope Standard v1.1).** `search_genes` and
  `get_gene_information` (`/data/*/description`) no longer emit a bare string;
  the field is now `{kind: "untrusted_text", text, provenance: {source,
  record_id, retrieved_at}, raw_sha256}` — NFC-normalized with control,
  zero-width, and bidi-override code points stripped, digested over the
  pre-normalization raw bytes. `record_id` is the gene's GENCODE ID. This types
  externally sourced prose as data at the MCP boundary (defense in depth; the
  router already treats a `kind: untrusted_text` subtree opaque) so a host
  cannot confuse a GENCODE descriptor with instructions. The internal `Gene`
  model and REST API (`/api/v1/reference/genes*`) are unchanged — only the MCP
  tool output reshapes. `search_genes`' `limit` param is now bounded
  (`ge=1, le=1000`) so its untrusted-object ceiling (1000, == the `limit`
  maximum) is real and coherent — one search page never returns more genes than
  `limit`; `get_gene_information` is capped by `GeneRequest.gene_id`
  (`max_length=50`), well inside the 128 default. When a fenced response
  exceeds a v1.1 size ceiling the MCP envelope returns an explicit
  `error_code: "output_limit_exceeded"` (`recovery_action:
  "reformulate_input"`), not a generic `internal_error`.
  Research use only; not clinical decision support.
- **`search`/`fetch` (ChatGPT/deep-research contract) no longer embed the
  upstream `description`.** These two tools return an OpenAI Apps-SDK-shaped
  flat text document (`title`, `text`) that cannot carry the typed
  `untrusted_text` envelope. Rather than emit the descriptor as a bare (even
  sanitized) string — still unfenced upstream prose on a flat surface — the
  free-text GENCODE descriptor is dropped from `search`'s `results[].title`
  and `fetch`'s `title`/`text`, which now carry only curated identifiers (gene
  symbol, GENCODE ID, chromosome/coordinates/enums, numeric expression). The
  fenced typed descriptor remains available via `get_gene_information`.

## [2.0.5] - 2026-07-11

### Security

- **Re-enabled FastMCP 3.4.4 strict Host/Origin protection with configurable
  allowlists.** Every REST and MCP route is now guarded by exact Host and
  browser Origin allowlists (`GTEX_LINK_ALLOWED_HOSTS` /
  `GTEX_LINK_ALLOWED_ORIGINS`), defaulting to loopback only and rejecting
  wildcard patterns at configuration time. Bumped `fastmcp` 3.4.3 → 3.4.4 for
  the `host_origin_protection` / `allowed_hosts` / `allowed_origins` guard API.
  DEPLOY PREREQUISITE: set the proxied public host or router federation 421s.

## [2.0.4] - 2026-07-07

### Changed (dependencies)

- Integrated the consolidated Dependabot sweep (`fastapi` 0.138.1 → 0.139.0,
  `fastmcp` / `fastmcp-slim` 3.4.2 → 3.4.3, `uvicorn` 0.50.2) on top of the
  2.0.3 PII-in-logs security fixes. This release carries both the dependency
  bumps and the security remediation; no functional change beyond the merge.

## [2.0.3] - 2026-07-07

### Security (PII in logs)

- **Variant coordinates and gene/transcript identifiers no longer logged.**
  Closed the remaining PII-in-logs leak (GDPR Art. 9) that the 2.0.2 pass scoped
  out: the service-layer variant lookups (`_get_variants_impl`,
  `_get_variants_by_location_impl`) and the gene/transcript/expression request
  diagnostics spread the raw request into logs via `**params.model_dump()`,
  emitting variant coordinates (chrom/pos/ref/alt) and gene/GENCODE identifiers.
  These sites now emit only non-identifying metadata (dataset/tissue enums, sort
  fields, page counts, and identifier-list counts) at both the service and route
  layers. Added sentinel guards for each anchor.

## [2.0.2] - 2026-07-07

### Security (inbound-boundary hardening)

- **CORS credentials off by default.** `cors_allow_credentials` now defaults to
  `False` (the backend is unauthenticated and holds no cookies/session), and a
  startup guard rejects the insecure `allow_credentials=True` + wildcard `*`
  origin combination rather than silently misconfiguring. The dev compose no
  longer sets credentials on.
- **Base `docker-compose.yml` loopback-bound.** The base compose publishes the
  host port on `127.0.0.1` only, so copying it to a server never exposes the
  unauthenticated backend on the public IP (Docker otherwise binds `0.0.0.0` and
  bypasses the host firewall). Production reaches the backend only via the
  router / reverse proxy.
- **No PII in logs.** Stopped logging free-text gene-search queries, subject and
  sample identifiers, and the full upstream URL (scheme + host). Request
  diagnostics now retain only the request path plus non-identifying metadata.
  Added route-, service-, and client-level sentinel guards.

## [2.0.1] - 2026-06-29

### Security (Container & Deployment Hardening Standard v1)

- Pinned the `python:3.14-slim` base image by digest, added a `container-security`
  CI workflow (Trivy scan + CycloneDX SBOM), and brought the base
  `docker-compose.yml` to hardening parity with the prod/npm overlays
  (`read_only`, tmpfs, `cap_drop: ALL`, `no-new-privileges`, `init`, pids/mem/cpu);
  the prod overlay now inherits those controls from the base.

## [2.0.0] - 2026-06-16

### Changed (BREAKING — GeneFoundry Logging & CLI Standard v1)

GTEx-Link now conforms to the fleet-wide **GeneFoundry Logging & CLI Standard
v1**. This is a CLI/transport front-end change only: the **MCP tool surface,
services, and `/api/health` / `/mcp` endpoints are unchanged**, so the
`genefoundry-router` gateway is unaffected.

- **CLI migrated from `argparse` to `typer`.** `gtex_link/cli.py` is now a
  single `typer.Typer(no_args_is_help=True)` app with `rich` output exposing
  the standard commands: `serve`, `config [--validate]`, `health [--url]`,
  `cache stats|clear`, and `version`. The server always boots via
  `gtex-link serve` — there is **no bare-serve**.
- `serve` options: `--transport {unified,http}` (default `unified`), `--host`,
  `--port`, `--mcp-path`, `--log-level`, `--disable-docs`, `--dev`.
- **Single console script.** `pyproject.toml` now declares only
  `gtex-link = "gtex_link.cli:app"`. The previous `gtex-link` (argparse `main`),
  `gtex-link-mcp`, and `gtex-mcp` entry points are **removed** with no aliases.
- **Root entry scripts deleted.** `server.py` and `mcp_server.py` are gone;
  `python -m gtex_link` now delegates to the typer app.
- **stdio transport removed.** The `stdio` transport value, the
  `UnifiedServerManager.start_stdio_server` / `_configure_stdio_environment`
  methods, and all stdio references in config, Docker, Makefile, and docs are
  removed. Streamable HTTP only.
- Docker `CMD`, all `docker-compose*.yml` commands, and the `make dev` / new
  `make serve` targets invoke `gtex-link serve …`.

### Fixed

- Version reporting is now sourced from `gtex_link.__version__` in `app.py`,
  the FastAPI app version, and the `/api/health` / `/api/version` responses
  (previously hardcoded `1.0.0`).

### Confirmed

- `gtex_link/logging_config.py` remains on the structlog canon (contextvars +
  log level + ISO timestamp + stack-info + exc-info + static fields, JSON in
  prod / console in dev, `asgi-correlation-id` binding). No regression.

## [1.0.0] - 2026-06-15

### Changed (BREAKING — GeneFoundry Tool-Naming Standard v1)

GTEx-Link now conforms to the GeneFoundry Tool-Naming & Normalization Standard
v1 so it composes cleanly behind the `genefoundry-router` MCP gateway, which
mounts this server under the **`gtex`** namespace (leaf tool `get_gene_information`
surfaces at the gateway as `gtex_get_gene_information`). There are **no
deprecation aliases** — update callers directly.

**Renamed tools:**

- `search_gtex_genes` → `search_genes`. The embedded `gtex` source token was
  redundant under the gateway namespace (it produced the double-prefixed
  `gtex_search_gtex_genes`). Payload and behaviour are unchanged.

The `search` / `fetch` deep-research pair (OpenAI deep-research / Apps SDK
contract) is **kept verbatim** as a documented exception to the canonical-verb
rule.

**Renamed arguments (fleet canon — applies to all paginated tools):**

- `page` → `offset`, `page_size` → `limit` on `search_genes`,
  `get_transcript_information`, `get_median_expression_levels`,
  `get_individual_expression_data`, and `get_top_expressed_genes_by_tissue`.
  `offset` is a zero-based row offset (`page = offset // limit`); `limit` is the
  page size. Defaults are unchanged.

### Added

- README documents the canonical gateway **namespace token** `gtex` and the
  full, refreshed MCP tool list (the previous list named a non-existent
  `get_expression_qtl_associations` and omitted five real tools).
- Domain `tags` on `get_server_capabilities` (`meta`, `discovery`).
- CI guard `tests/unit/test_tool_names.py`: every registered tool matches
  `^[a-z0-9_]{1,50}$`, starts with a canonical verb (with the `search`/`fetch`
  deep-research allowlist), and does not self-prefix the `gtex` namespace token.

### Fixed

- Reconciled version drift: the FastAPI app, `/api/health`, and `/api/version`
  previously reported stale `0.2.0` / `0.1.0` strings; all now report the
  package version (`1.0.0`).

## [Unreleased]

### Fixed (MCP surface hardening)

- `get_gene_information` now returns a structured `not_found` error for unknown
  genes instead of a silent `success: true` with an empty `data` list.
- `get_median_expression_levels` returns `not_found` (with a GENCODE-version
  hint for non-`gtex_v8` datasets) instead of silently succeeding with no rows,
  closing the `gtex_v10` silent-empty trap.
- `get_transcript_information` and `get_individual_expression_data` now return
  `not_found` (with the offending GENCODE ID and a resolution hint) instead of
  a silent `success: true` empty `data` list, extending the no-silent-false-
  negative contract across the whole tool surface.
- Invalid tissue filters on `get_median_expression_levels` and
  `get_individual_expression_data` now raise the same short `invalid_input`
  message as `get_top_expressed_genes_by_tissue` instead of dumping the full
  54-tissue enum twice (shared `ensure_valid_tissue` helper).
- Compact median output no longer emits always-null `ontologyId`/`spread` keys
  (honoring the documented "tissue/median/n only" contract).
- Median and spread `min`/`max` values are rounded to 4 decimals, removing
  floating-point noise like `484.38300000000004`.

### Added (MCP surface hardening)

- `get_median_expression_levels` `tissue_site_detail_id` accepts a list of
  tissues for a compact multi-tissue comparison (filtered client-side).
- `get_individual_expression_data` rows now carry `n` (sample count); the
  per-sample vector is documented as unlabeled and in upstream order.
- `get_top_expressed_genes_by_tissue` emits `_meta.next_commands` pointing at
  `get_median_expression_levels` for the top gene.
- `not_found` now maps to the `reformulate_input` recovery action.

### Changed (Dependency maintenance)

- Consolidated the open Dependabot updates into a single change set:
  - Runtime: `uvicorn[standard]` 0.48 → 0.49, `structlog` 25.5 → 26.1,
    `typer` 0.25.1 → 0.26.7, `mcp[cli]` 1.27.1 → 1.27.2,
    `fastmcp` 3.3.1 → 3.4.2, `asgi-correlation-id` 4.3 → 5.0.
  - Dev/tooling: `pytest-asyncio` 1.3 → 1.4, `ruff` 0.15.14 → 0.15.16.
  - CI actions: `actions/checkout` 6.0.2 → 6.0.3,
    `astral-sh/setup-uv` 7.6.0 → 8.2.0.
  - Validated against `make ci-local` (format, lint, file-size, mypy strict,
    360 tests) and app/MCP boot smoke checks after the `structlog` 26 and
    `asgi-correlation-id` 5 major bumps.

### Added (Phase 1 — Foundation)

- `AGENTS.md` as shared source of truth for agentic tools.
- `GEMINI.md` and slimmed `CLAUDE.md` as thin pointers.
- `docs/architecture.md` and `docs/conventions.md` absorbing former CLAUDE.md content.
- `.github/workflows/ci.yml` running `make ci-local` and coverage.
- `.github/workflows/security.yml` with CodeQL and dependency review.
- `.github/workflows/docker.yml` validating compose configs and building images.
- `.github/workflows/release.yml` for tag-triggered validation.
- `.github/dependabot.yml` weekly updates for uv/actions/docker.
- `.github/pull_request_template.md`.
- Five `.claude/skills/` workflows: `fastapi-route-change`, `mcp-tool-change`, `ci-failure-triage`, `release-readiness`, `gtex-api-endpoint-add`.
- `Makefile` `ci-local`, `typecheck-fast`, `format-check`, `lint-ci`, `test-fast`, `test-cov` targets.
- Dev deps: `pytest-xdist`, `respx`.
- Runtime deps: `asgi-correlation-id`, `prometheus-client` (wired up in Phase 2).

### Changed

- Build backend: setuptools → hatchling.
- Python minimum version: 3.10 → 3.12.
- Dependency floors raised to current stable:
  - fastapi 0.110 → 0.115+
  - fastmcp 0.2 → 3.2+
  - pydantic 2.7 → 2.11+
  - pytest 8 → 9+
  - ruff 0.4 → 0.8+
  - mypy 1.10 → 1.14+
  - pre-commit 3.7 → 4.0+
  - structlog 24.1 → 24.4+
  - rich 13 → 15+
  - typer 0.12 → 0.25+
  - mcp 1.0 → 1.27+
  - gunicorn 22 → 25+
- `CLAUDE.md` shrunk from 16K to a thin pointer at `AGENTS.md`.
- `Makefile` rewritten; consolidated docker targets to a canonical set.

### Removed

- Dev/runtime deps: `bandit`, `python-multipart`, `mkdocs`, `mkdocs-material`, `mkdocstrings`, `opentelemetry-*`.
- Tracked `.env` file (replaced by `.env.example`).
- Generated artifacts in repo (`coverage.xml`, `htmlcov/`, `gtex_link.egg-info/`).
- Root-level stale `PLAN.md` (relocated to `docs/superpowers/plans/archive/`).

### Added (Phase 2 — Observability & tests)

- `gtex_link/observability/` package: correlation IDs (asgi-correlation-id), Prometheus collectors, `/metrics` endpoint.
- ASGI middleware: `CorrelationIdMiddleware`, `MetricsMiddleware`.
- Structlog processors: `bind_correlation_id_processor` and `_add_static_fields` injecting `correlation_id`, `service=gtex-link`, `version` into every log event.
- Outbound `X-Request-ID` propagation in `GTExClient` (inbound correlation ID echoed on upstream calls).
- Prometheus collectors: HTTP request count/duration, upstream request count/duration, cache hits/misses, rate-limit waits, MCP tool calls (populated in Phase 3).
- `respx_mock` fixture and `GTEX_BASE` constant in `tests/conftest.py`.
- `tests/test_observability/` covering correlation echo, generated ID, `/metrics` endpoint, request counter, upstream call helper, cache hit/miss helper.
- `.gitattributes` pins `.py`/`.toml`/`.yml`/`.md`/`.json`/`.sh`/`Makefile`/`Dockerfile` to LF in the working tree so `ruff format --check` is stable on Windows checkouts.

### Changed (Phase 2)

- Package and FastAPI version bumped to `0.2.0` (matches pyproject.toml).
- Route, client, and edge-case HTTP-mocking tests migrated from `unittest.mock.patch("httpx.AsyncClient.request", ...)` to `respx` route registrations.
- `make test-fast` runs the suite under `pytest-xdist -n auto`; coverage gate stays at 90%.
- Cache hit/miss metrics emitted at the `CacheManager` decorator layer rather than per-service wrapping, so every cached service method automatically gets a Prometheus label derived from its `key_pattern`.

### Notes

- No external API or MCP tool contract changes. The MCP tool counter is wired but only populated by Phase 3.

### Added (Phase 3 -- MCP facade & transport unification)

- `gtex_link/mcp/` package with explicit tool registration: `facade.py`, `profiles.py`, `resources.py`, `errors.py`, `output_validation.py`, `service_adapters.py`, and per-category tool modules under `tools/` (reference, expression, search/fetch).
- `gtex_link/mcp/profiles.py` with `full` (all tools) and `lite` (read-only research subset) profiles.
- `GTEX_LINK_MCP_PROFILE` env var (default `full`).
- `gtex_link/__main__.py` so `python -m gtex_link` aliases the unified server.
- `UnifiedServerManager` (`gtex_link/server_manager.py`) with `start_unified_server`, `start_http_only_server`, `start_stdio_server`, and graceful shutdown.
- `server.py --transport {unified,http,stdio}` single entry point.

### Changed (Phase 3)

- MCP layer: replaced `FastMCP.from_fastapi` auto-generation with an explicit facade. Tool names preserved 1:1; tool descriptions hand-tuned for AI clients.
- `mcp_server.py` is now a thin stdio entry that delegates to `UnifiedServerManager`.
- `gtex_link/app.py` is a pure FastAPI factory -- MCP code moved out into `gtex_link/mcp/`.
- Docker: `docker/docker-compose.yml` collapsed the `api` + `mcp` services into a single `gtex-link` service. `docker/docker-compose.npm.yml` collapsed to a single `gtex_link` upstream. `docker/docker-compose.dev.yml` no longer mounts the deleted `mcp_http_server.py`.
- `GTEX_LINK_TRANSPORT_MODE` env var renamed to `GTEX_LINK_TRANSPORT` (values: `unified`, `http`, `stdio`).
- `make dev` and `make mcp-serve-http` now invoke `server.py --transport unified` (was: bare `server.py`).

### Removed (Phase 3 -- BREAKING)

- `mcp_http_server.py` deleted. Use `server.py --transport unified` or `--transport http` instead.
- `gtex-mcp-http` console script removed at the architecture level (the script entry was already absent from `pyproject.toml`; the `mcp_http_server.py` entry point it pointed at is now gone too). Use `gtex-mcp` for stdio or `server.py --transport unified` for HTTP.
- `GTEX_LINK_MCP_PORT` env var removed. Unified mode runs on a single port (`GTEX_LINK_PORT`).
- Two-service Docker compose split (api/mcp) removed.
- `docker/docker-compose.mcp.yml` deleted (it only existed to run `mcp_http_server.py`).
- `GTEX_MCP_MEMORY_LIMIT` / `GTEX_MCP_CPU_LIMIT` env vars dropped from `.env.docker.example` (no separate MCP container).
- MCP tool `version_info_api_version_get` removed. This was auto-generated by `FastMCP.from_fastapi` for the `GET /api/version` route and was never explicitly intended as an MCP tool. The version endpoint remains available as a regular HTTP route at `/api/version`. (See `docs/superpowers/plans/archive/2026-05-11-mcp-tool-audit.md` for the full pre-migration tool audit.)
- Obsolete `tests/unit/test_app.py` MCP coverage replaced by dedicated suites under `tests/test_mcp/`.

### Migration notes (Phase 3)

- Anyone running `mcp_http_server.py` or `gtex-mcp-http`: switch to `gtex-mcp` (stdio) or `python server.py --transport unified` (FastAPI + MCP on one port).
- Anyone setting `GTEX_LINK_TRANSPORT_MODE`: rename the env var to `GTEX_LINK_TRANSPORT`.
- Anyone setting `GTEX_LINK_MCP_PORT`: remove the env var; the MCP endpoint is now served on `GTEX_LINK_PORT` at the `GTEX_LINK_MCP_PATH` path (default `/mcp`).
- Deployments using the two-service compose split: redeploy with the new single-service compose; update reverse-proxy upstream from two pools to one.
- Anyone calling the auto-generated `version_info_api_version_get` MCP tool: switch to `GET /api/version` over HTTP, or read version metadata from any other tool response that already includes it.
