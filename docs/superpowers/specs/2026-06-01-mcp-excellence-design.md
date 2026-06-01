# MCP Surface Excellence Design

## Context

An external LLM-agent reviewer drove the gtex-link MCP server end-to-end (a
PKD1/UMOD expression task plus a 17-call test matrix across all 8 tools) and
scored it on six dimensions. The headline finding: the data layer is accurate,
but the *MCP surface* yields wrong or misleading conclusions and wastes tokens.
The reviewer scored Correctness 4, Token efficiency 4, Observability 4,
Consistency 4, Discoverability 7, Speed 7 (overall ~5/10).

This spec defines the work to bring every dimension to **>=9/10** by fixing the
confirmed defects and bringing gtex-link to parity with the established house
conventions of the sibling `-link` MCP servers. The target is an **excellent
MCP surface**; the FastAPI/OpenAPI REST surface is explicitly not a priority.

All claims below were independently verified in this design pass:

- **Reproduced live** against the running MCP (double-encoding, empty NL search,
  alphabetical all-zeros `fetch`, silent empty on symbol input, `numSamples:
  null`).
- **Root-caused in source** at file:line (see Current Baseline).
- **Best practices** confirmed against the MCP spec (2025-06-18), Anthropic
  "Writing effective tools for AI agents", the OpenAI deep-research `search`/
  `fetch` contract, and Google Gemini function-calling guidance.
- **Sibling conventions** extracted from `../gnomad-link` (v2.0.0, reference),
  `../autopvs1-link` (v1.2.0, newest refinements), `../pubtator-link`, and
  `../genereviews-link`.
- **GTEx API capability** for sample counts and spread tested against the live
  `https://gtexportal.org/api/v2/` endpoints.

## Goals

- Raise all six review dimensions to >=9/10.
- Adopt the family house style: structured `dict` returns (no double-encoding),
  a shared `run_mcp_tool` envelope, `_meta` provenance + `next_commands`, a
  structured error taxonomy, tool annotations, `response_mode`, a capabilities
  tool + resources, and a one-line `headline`.
- Fix the two P0 correctness defects that break the advertised research path:
  natural-language `search` and magnitude-sorted `fetch`.
- Eliminate silent false negatives (symbol input -> empty data).
- Populate real per-tissue sample counts (`n`) cheaply; offer opt-in spread.
- Keep the default surface fast: cached constants, opt-in expensive data,
  concise-by-default payloads.
- Deliver as phased, independently shippable PRs (P0 -> P3), each gated by
  `make ci-local`.

## Non-Goals

- No REST/OpenAPI route polish. Shared service/model fixes land where they
  belong and incidentally benefit REST, but REST behavior parity is not pursued.
- No version-bump ceremony or deprecation windows. The project is pre-alpha;
  breaking the MCP response shapes is acceptable and expected.
- No new GTEx domain endpoints beyond what is needed for `n`/spread enrichment
  (which reuses the existing `tissue_site_detail` and `geneExpression`
  endpoints already wired in `client.py`).
- No embeddings/semantic search. NL `search` uses deterministic tokenization.
- No Family B (`envelope.py` `{ok,data,error,meta}`) rewrite; see Architecture.

## Current Baseline (confirmed root causes)

MCP layer (`gtex_link/mcp/`) is minimal vs the family:

```
mcp/: facade.py, errors.py, profiles.py, resources.py, output_validation.py,
      service_adapters.py, tools/{expression,reference,search_fetch}.py
```

Confirmed defects:

- **Double-encoding (all tools).** Every tool returns a JSON string, so FastMCP
  re-wraps it and emits no `structuredContent`. Live: `{"result":"{\"results\":
  []}"}`. Source: `tools/expression.py:57`, `tools/reference.py:48,85,124`,
  `tools/search_fetch.py:58,79,163` all `return json.dumps(...)`. Even `fetch`
  double-encodes; its `text` field merely looks clean.
- **`search` is symbol-only.** `search("UMOD kidney expression")` -> `[]`;
  `search("UMOD")` -> 3 hits. Query is passed straight as `geneId`
  (`api/client.py` `search_genes`); errors are swallowed to `{"results": []}`
  (`search_fetch.py:60`). Breaks the OpenAI deep-research contract, which
  REQUIRES `search` to accept natural-language queries.
- **`fetch` summary is magnitude-blind and truncated.** Hardcoded `[:10]` with
  no sort (`search_fetch.py:110-131`); upstream order is alphabetical, so UMOD
  shows 10 tissues all `0.00 TPM` and hides Kidney_Medulla (2116 TPM) behind
  "...and 40 more tissues". Actively misleading.
- **Silent empty on symbol input.** `MedianGeneExpressionRequest`
  (`models/requests.py:102`) requires GENCODE IDs but does not validate, so
  `get_median_expression_levels(["PKD1"])` returns `{"data": []}` with no error.
  Contrast `GeneRequest` which accepts symbols.
- **`numSamples` always null.** `MedianGeneExpression.num_samples`
  (`models/responses.py:367`) defaults `None` and is never populated. Confirmed
  via API probe: upstream `medianGeneExpression` has no `n` field at all.
- **Pagination flattens across genes.** One `page_size` over the combined
  multi-gene row set (`tools/expression.py:50`), so a gene can be split across a
  100-row page boundary (correctness/data-integrity risk).
- **`geneSymbolUpper` redundancy** (`models/responses.py:248`); **tissue enum
  includes `""`** as `ALL` (`models/gtex.py:91`), leaking into the public
  surface; **`fetch` requires a `gene:` prefix** no other tool emits
  (`search_fetch.py:78`).

Missing family infrastructure (present in 2+ siblings): `annotations.py`,
`next_commands.py`, `headline.py`, a shared `run_mcp_tool`/envelope, a
capabilities/`metadata.py` tool module, an error taxonomy, `_meta` provenance,
and a citation surface.

## Architecture Decision

Adopt the **gnomad-link "Family A" base plus two autopvs1-link refinements**:

- Tools return a plain `dict[str, Any]` (never `json.dumps`). FastMCP serializes
  once and emits `structuredContent`. (MCP spec: lead with `structuredContent` +
  `outputSchema`; also keep a serialized copy in a text block for legacy
  clients.)
- A shared `run_mcp_tool(name, call, context=...)` boundary injects
  `success`/`_meta`, classifies exceptions into the error taxonomy, and attaches
  `next_commands`. Mirrors `../gnomad-link/gnomad_link/mcp/errors.py:469`.
- Refinement 1 (from autopvs1): a `capabilities_version` sha256 content-hash so
  warm clients skip re-fetching capabilities.
- Refinement 2 (from autopvs1): an error -> `recovery`/`next_commands` registry
  so error envelopes carry actionable next steps.

Rejected alternatives: pure gnomad-link (no content-hash) is slightly less
discoverable; autopvs1 Family B (`envelope.py` `{ok,data,error,meta}`) is more
ceremony and diverges from the closest structural analog.

New `mcp/` modules to add: `envelope.py` (or `run_mcp_tool` in `errors.py`),
`annotations.py`, `next_commands.py`, `headline.py`, `metadata.py` (capabilities
tool), and an expanded `resources.py`. All cohesive and well under the 600-line
cap.

## Response Shape (target)

Un-double-encoded, gene-grouped, invariants hoisted, `n` populated, `headline`
first, `_meta.next_commands` for chaining. Example
`get_median_expression_levels(["ENSG00000169344.15"], top_n=3, sort="desc")`:

```json
{
  "headline": "UMOD: highest median in Kidney_Medulla (2116.02 TPM, n=4).",
  "genes": [
    {
      "gencodeId": "ENSG00000169344.15",
      "geneSymbol": "UMOD",
      "datasetId": "gtex_v8",
      "unit": "TPM",
      "tissues": [
        {"tissue": "Kidney_Medulla", "median": 2116.02, "n": 4},
        {"tissue": "Kidney_Cortex",  "median": 190.13,  "n": 85},
        {"tissue": "Bladder",        "median": 0.42,    "n": 21}
      ],
      "tissuesReturned": 3,
      "tissuesTotal": 54
    }
  ],
  "_meta": {
    "unsafe_for_clinical_use": true,
    "gtex_release": "gtex_v8",
    "next_commands": [
      {"tool": "get_top_expressed_genes_by_tissue",
       "arguments": {"tissue_site_detail_id": "Kidney_Medulla"}}
    ]
  },
  "success": true
}
```

`response_mode="full"` adds `ontologyId` and (if `include_spread=true`) per-tissue
`min/max/q1/q3/iqr`. `compact` (default) omits them and drops `geneSymbolUpper`
entirely.

## Phase Plan

Each phase is one independently shippable PR, gated by `make ci-local`. Skills
`mcp-tool-change` and `fastapi-route-change` apply where relevant.

### PR1 - Correctness P0

Goal: the advertised `search` -> `fetch` research path stops misleading agents,
and no tool returns a silent false negative.

- Introduce `run_mcp_tool` + envelope infra; convert every tool to return
  `dict[str, Any]` (drop all `json.dumps`). Add `structuredContent` via FastMCP;
  keep a serialized text copy for legacy clients.
- `fetch`: sort tissues by descending median; show top N (default ~10) plus
  "...N more at <=X TPM"; never alphabetical. Accept a bare GENCODE id as an
  alias for `gene:<id>`.
- `search`: port `../genereviews-link` `recall_terms` tokenizer (3+ char tokens,
  stop-words removed); match tokens against gene symbol + description; union and
  rank by `match_quality` (`exact_symbol` > `exact_ensembl_id` > `prefix` >
  `substring`, per `../gnomad-link/.../tools/search.py`). Stop swallowing errors
  to empty; return a structured error instead.
- `get_median_expression_levels` / `get_individual_expression_data`: auto-resolve
  gene symbols to GENCODE IDs (reuse the `get_gene_information` resolution path);
  if unresolved, return `invalid_input` with the offending token - never a silent
  `data:[]`.

Dimensions moved: Correctness 4->9, plus Token (un-double-encode) and Consistency
groundwork.

### PR2 - Observability + trust P1

Goal: every median carries the sample count behind it; failures are structured.

- Populate real `n`: fetch `dataset/tissueSiteDetail?datasetId=<id>` once per
  dataset, build a `{tissueSiteDetailId: rnaSeqSampleSummary.totalCount}` map,
  cache it (existing `get_tissue_site_details` at `client.py:462` + 1h
  `CacheConfig`). Populate `num_samples` at serialization. Zero per-query round
  trips. Verified gene-independent: `totalCount` == `len(geneExpression.data)`.
- Opt-in `include_spread` (default `false`): when true, pull
  `expression/geneExpression` per-sample arrays and derive `min/max/q1/median/q3/
  iqr`; use `len(data)` as an `n` cross-check. Off by default to protect latency;
  off on the hosted/lite profile.
- Error taxonomy + envelope: codes `not_found | invalid_input |
  validation_failed | rate_limited | upstream_unavailable |
  output_validation_failed | internal_error`; fields `error_code, message,
  retryable, recovery_action, field_errors`; echo valid values on invalid enums.
  Mirrors `../gnomad-link/.../mcp/errors.py`.
- Tool annotations on every tool: `READ_ONLY_OPEN_WORLD = ToolAnnotations(
  readOnlyHint=True, destructiveHint=False, idempotentHint=True,
  openWorldHint=True)`, plus `title`, `tags`, and `output_schema`. `_meta`
  provenance: `unsafe_for_clinical_use: true`, `gtex_release`.

Dimensions moved: Observability 4->9, Consistency partial.

### PR3 - Token efficiency + chaining P2

Goal: cut payload tokens ~50-60% and remove reasoning/round-trip hops.

- Gene-grouped shape with hoisted invariants (`datasetId/unit/geneSymbol/
  gencodeId` to the parent; per-tissue rows carry only `tissue/median/n`).
- Pagination by gene: never split a gene's tissues across a page boundary.
  Paginate the gene list (or return all tissues per requested gene atomically).
- `response_mode: compact|full` (default `compact`, per
  `../gnomad-link/.../tools/variants.py:93`); `compact` drops `geneSymbolUpper`,
  `ontologyId`, and spread.
- `top_n` + `sort` on `get_median_expression_levels` so "where is this expressed
  most?" is one small response instead of pulling all 54 tissues and ranking
  client-side.
- `next_commands.py` builders (`search_gtex_genes` -> `get_gene_information` ->
  `get_median_expression_levels` / `get_top_expressed_genes_by_tissue`) attached
  via `_meta` on success and error.
- `headline.py`: one-line plain-English answer placed first (top tissue + median
  + n).

Dimensions moved: Token 4->9, Speed partial, Discoverability partial.

### PR4 - Discoverability + parity polish P3

Goal: self-service discovery and full family parity.

- `get_server_capabilities` tool + `gtex://{capabilities,usage,reference,
  research-use,citations}` resources; include a `capabilities_version` sha256
  content-hash. Top-level keys mirror gnomad: `server, server_version,
  mcp_protocol_version, gtex_release, research_use_only, datasets, tissues,
  recommended_workflows, tools, token_cost_hints, limitations, error_codes,
  parameter_conventions, resources, response_fields, tool_categories`.
- Controlled-vocab hygiene: keep the tissue `Literal`/enum as the schema-level
  vocabulary; remove the bare `""` from the public surface and handle "all
  tissues" via an explicit absent/`null` filter rather than an empty-string enum
  member.
- Citation surface: `recommended_citation` (GTEx Consortium, Science 2020) and/or
  a `citations_ref` pointer, following `../autopvs1-link`/`../genereviews-link`.
- Speed/concurrency: document the 5 req/s token-bucket and batch guidance in
  capabilities; confirm tools parallelize cleanly.

Dimensions moved: Discoverability 7->9, Speed 7->9.

## Dimension Targets

| Dimension | Baseline | Target | Decisive levers (phase) |
|---|---|---|---|
| Correctness/reliability | 4 | 9+ | NL search, fetch sort, no silent empties, gene-safe pagination, output_schema (PR1, PR3) |
| Token efficiency | 4 | 9+ | un-double-encode, gene-grouping + hoist, response_mode, drop geneSymbolUpper, headline (PR1, PR3) |
| Observability | 4 | 9+ | real n, opt-in spread, error taxonomy, annotations, _meta provenance (PR2) |
| Consistency/ergonomics | 4 | 9+ | uniform envelope, symbol handling, id-contract unification, structured errors (PR1, PR2) |
| Discoverability | 7 | 9+ | capabilities tool+resources, content-hash, enum vocab, next_commands (PR3, PR4) |
| Speed | 7 | 9+ | removed wasted round-trips, cached n, opt-in spread, concise default (PR2, PR3, PR4) |

## Speed Rationale

The review's two "wasted round-trips" come from defects, not raw latency: NL
search returning empty forces a retry; the misleading `fetch` forces a re-query;
ranking "top tissue" forces pulling all 54 tissues. PR1/PR3 remove all three.
`n` is a cached constant (one cold call per dataset). Spread is opt-in.
`next_commands` removes the next-tool reasoning hop. Net: fewer calls and smaller
payloads, so wall-clock improves even though per-call upstream latency is
unchanged.

## File-Size Discipline

New modules are cohesive and small; no file should approach 600 lines. If
`tools/search_fetch.py` (currently 175) grows past ~450 with NL search +
envelope wiring, split the tokenizer/ranking helper into `mcp/search_match.py`.
`make lint-loc` (in `make ci-local`) enforces the cap; no `.loc-allowlist`
entries are anticipated.

## Testing

- Unit tests for the tokenizer/ranking, symbol resolution, `n` map building,
  spread derivation, gene-grouping/pagination, and the error classifier.
- Route/tool tests asserting: no double-encoding (result is structured, not a
  JSON string), `fetch` returns magnitude-sorted tissues, `search` returns hits
  for a natural-language query, symbol input yields data or a structured error
  (never silent empty), median rows carry `n`, and `_meta.next_commands` is
  present and directly callable.
- Use `respx` to mock outbound httpx calls (including the `tissueSiteDetail` and
  `geneExpression` enrichment calls).
- Maintain the 90% coverage gate (`make test-cov`).

## Verification

Run after each PR:

1. `uv lock`
2. `make format-check`
3. `make lint`
4. `make lint-loc`
5. `make typecheck`
6. `make test`
7. `make ci-local`

Plus a live MCP smoke check per PR (re-run the reviewer's failing calls:
`search("UMOD kidney expression")`, `fetch` on UMOD, `get_median_expression_
levels(["PKD1"])`) and confirm the defect is gone.

If any check fails due to pre-existing unrelated debt, the handoff must include
the exact command and failure.

## References

- MCP spec 2025-06-18: Tools (`structuredContent`/`outputSchema`), Pagination
  (opaque `cursor`/`nextCursor`), `_meta` (vendor-prefixed), ToolAnnotations.
- Anthropic, "Writing effective tools for AI agents" (response_format concise
  default ~1/3 tokens; high-signal fields; consolidate calls; default
  truncation with explicit signaling).
- OpenAI deep-research `search`/`fetch` contract (natural-language `search`;
  `fetch` returns `id/title/text/url/metadata`).
- Google Gemini function-calling (enums for controlled vocabularies).
- Sibling repos: `../gnomad-link` (errors.py `run_mcp_tool`, next_commands.py,
  headline.py, annotations.py, resources.py), `../autopvs1-link` (envelope.py,
  registries.py `capabilities_version`), `../genereviews-link` (retrieval/
  lexical.py NL tokenizer), `../pubtator-link` (original error/envelope).
- GTEx API probe: `expression/medianGeneExpression` (no `n`),
  `dataset/tissueSiteDetail` -> `rnaSeqSampleSummary.totalCount` (constant `n`),
  `expression/geneExpression` (per-sample arrays for spread); no quartile/boxplot
  endpoint exists.
