# gtex-link

[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![CI](https://github.com/berntpopp/gtex-link/actions/workflows/ci.yml/badge.svg)](https://github.com/berntpopp/gtex-link/actions/workflows/ci.yml)
[![Conformance](https://github.com/berntpopp/gtex-link/actions/workflows/conformance.yml/badge.svg)](https://github.com/berntpopp/gtex-link/actions/workflows/conformance.yml)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)

An MCP server over the [GTEx Portal](https://gtexportal.org/) v2 API, serving GTEx
tissue expression — median and individual-sample TPM, top genes per tissue, gene and
transcript annotation — to AI assistants over Streamable HTTP. It also serves a REST API
from the same process.

> [!IMPORTANT]
> Research use only. Not clinical decision support. Do not use for diagnosis,
> treatment, triage, or patient management.

## Why

The GTEx Portal v2 API is public and needs no key, but it is shaped for the Portal's own
UI rather than for a model. `/expression/medianGeneExpression` **requires versioned
GENCODE IDs** (`ENSG00000012048.23`) — a gene symbol is not a valid argument — so every
question starts with a separate resolution call whose GENCODE version and genome build
must line up with the expression call that follows. Tissues are addressed by internal
`tissueSiteDetailId` codes, and "where is this gene expressed?" spans several paginated
endpoints that return wide, untyped JSON.

Worse, the release you query decides the annotation: `gtex_v8` is GENCODE v26 and
`gtex_v10` is GENCODE v39, so an ID resolved against the wrong one silently returns
nothing.

gtex-link answers that question in one call. Symbols are auto-resolved to GENCODE IDs
**in the release backing the dataset you asked for**; tissue expression comes back ranked
and compact by default; every result with a `_meta` frame (all but `fetch`, whose document
shape is fixed by the Apps SDK) stamps provenance naming the release actually queried plus
the required citation, and the tools with an obvious next step add `_meta.next_commands` so
a model chains without guessing; and a token-bucket limiter keeps the whole fleet inside
GTEx's request budget.

## Quick start

Hosted — nothing to install, no data to build:

```bash
claude mcp add --transport http gtex-link https://gtex-link.genefoundry.org/mcp
```

Run it yourself (Python 3.12+, [uv](https://github.com/astral-sh/uv)). There is no data
bundle and no ingest step — the server proxies the live GTEx Portal API:

```bash
uv sync --group dev
make dev                                    # unified REST + MCP on 127.0.0.1:8000
curl http://127.0.0.1:8000/api/health
```

The MCP endpoint is `http://127.0.0.1:8000/mcp`. Streamable HTTP is the only transport —
there is no stdio, and `gtex-link serve --transport http` is **REST-only and serves no
`/mcp`**; MCP clients need the default `unified` transport. See
[deployment.md](docs/deployment.md).

## Tools

| Tool | Purpose |
|------|---------|
| `search` | Natural-language gene search; returns result documents (`id`/`title`/`url`) |
| `fetch` | Full gene detail for an `id` returned by `search` |
| `search_genes` | Search the GTEx Portal gene catalog by symbol or partial match |
| `get_gene_information` | Gene detail for a GENCODE ID or symbol |
| `get_transcript_information` | Transcript annotations for a GENCODE ID |
| `get_median_expression_levels` | Median expression (TPM) per tissue |
| `get_individual_expression_data` | Individual-sample expression (TPM) |
| `get_top_expressed_genes_by_tissue` | Top expressed genes for a tissue |
| `get_server_capabilities` | Discover tools, datasets, tissues, limits, and workflows |

`search` / `fetch` are the OpenAI deep-research / Apps SDK contract and are retained
verbatim — a documented exception to the canonical-verb rule of the GeneFoundry
Tool-Naming Standard v1.

**Namespace.** Leaf tool names are unprefixed, per Tool-Naming Standard v1. Behind the
[`genefoundry-router`](https://github.com/berntpopp/genefoundry-router) gateway, which
mounts this server with `mount(namespace="gtex")`, they surface as `gtex_<tool>` —
`get_gene_information` becomes `gtex_get_gene_information`. A leaf-level `gtex_` prefix
would double-prefix to `gtex_gtex_…`, so do not add one.

## Data & provenance

| | |
|---|---|
| **Source** | [GTEx Portal](https://gtexportal.org/) v2 API — `https://gtexportal.org/api/v2/`, public, **no authentication** |
| **Datasets** | `gtex_v8` (GENCODE `v26`, the default), `gtex_v10` (`v39`), `gtex_snrnaseq_pilot` (`v26`) — pick one with the `dataset_id` argument on the expression tools |
| **Provenance** | On every tool that has a `_meta` frame, `_meta.gtex_release` names the release the data **actually came from**: it follows `dataset_id`, and a dataset-scoped call also reports the `_meta.gencode_version` its gene IDs were resolved against. Tools taking no `dataset_id` report the server default (`gtex_v8`); `fetch` and `get_server_capabilities` carry no `_meta` at all ([data.md](docs/data.md)) |
| **Refresh** | None to run: no bundle, no mirror, no ingest. Calls proxy the live API behind a TTL cache, so freshness tracks the Portal |
| **Rate limit** | Token bucket, 5 req/s with burst 10 — upstream courtesy, not a local throttle. Do not raise it casually |
| **Data licence** | GTEx Portal [terms](https://gtexportal.org/home/license). Only open-access GTEx data are reachable here; protected individual-level genotype data are dbGaP-controlled and are not exposed |

Required citation — returned verbatim in `_meta.recommended_citation` and at the
`gtex://citations` resource:

> GTEx Consortium. The GTEx Consortium atlas of genetic regulatory effects across human
> tissues. Science. 2020;369(6509):1318-1330. doi:10.1126/science.aaz1776

More: [data.md](docs/data.md).

## Documentation

- [Data & provenance](docs/data.md) — dataset, refresh model, licence, citation, response modes, and error codes.
- [Configuration](docs/configuration.md) — every `GTEX_LINK_*` variable, the MCP tool profiles, and the Host/Origin request boundary.
- [Deployment](docs/deployment.md) — transports, the CLI, Docker and Compose overlays, the proxy boundary, and health checks.
- [Architecture](docs/architecture.md) — the layering, the REST surface, and why REST and MCP are deliberately not symmetric.
- [Conventions](docs/conventions.md) — code style, test data standards, and upstream pagination.
- [GTEx Portal API reference](docs/README.md) — the upstream endpoint catalogue, generated from the OpenAPI spec.
- [AGENTS.md](AGENTS.md) — engineering conventions for humans and coding agents.
- [SECURITY.md](SECURITY.md) — the trust boundary and how to report a vulnerability.
- [CHANGELOG.md](CHANGELOG.md) — release history.

## Contributing

Read [AGENTS.md](AGENTS.md) first — it is the engineering guide. `make ci-local` is the
definition-of-done gate: format, lint, line budget, README standard, type check, and
tests. It must be green before handoff.

## License

Code: [MIT](LICENSE). Data: GTEx Portal data remain subject to the GTEx Portal's
[terms](https://gtexportal.org/home/license) and carry the citation requirement above.
