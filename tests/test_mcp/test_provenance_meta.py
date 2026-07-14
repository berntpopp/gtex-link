"""End-to-end provenance guarantees, driven through the REAL MCP facade.

Unit tests that hand `_provenance_meta` a synthetic `McpErrorContext` prove the
envelope *can* report the right release -- they do NOT prove the tools actually
pass their `dataset_id` into that context. Remove `dataset_id=dataset_id` from a
tool's `McpErrorContext` and those unit tests still pass while the bug is back.
So the provenance contract is pinned here, through `mcp.call_tool`:

  1. every dataset-scoped tool reports the release it was ASKED for;
  2. an unknown dataset_id is rejected BEFORE any upstream call (an unknown
     dataset must never be silently resolved against the default GENCODE
     release -- that is the same defect class as the false release stamp);
  3. exactly which tools carry a provenance `_meta` at all -- `fetch` (the flat
     Apps SDK document shape) and `get_server_capabilities` (its own document)
     carry none -- AND that docs/data.md's `_meta` table says the same thing: the
     table is parsed here and each row checked against live tool behaviour.

That live classification is then the ORACLE for a prose lint over README.md, every
docs/**/*.md, and the client-facing strings the server ships: no prose may claim
`_meta` universality unscoped, nor name only SOME of the tools that lack it (the
"all but `fetch`" bug, which dropped `get_server_capabilities` and shipped twice).
docs/superpowers/** is excluded as a dated design archive -- and fenced: every file
there must carry a "Historical design record" banner or this module fails.
"""

from __future__ import annotations

import json
import re
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from gtex_link.mcp.facade import create_gtex_mcp
from gtex_link.mcp.metadata import _ALL_TOOLS
from gtex_link.mcp.profiles import MCPToolProfile
from gtex_link.models.responses import (
    Gene,
    GeneExpression,
    MedianGeneExpression,
    PaginatedGeneExpressionResponse,
    PaginatedGeneResponse,
    PaginatedMedianGeneExpressionResponse,
    PaginatedTissueSiteDetailResponse,
    PaginatedTopExpressedGenesResponse,
    PaginatedTranscriptResponse,
    PaginationInfo,
    TopExpressedGenes,
    Transcript,
)

# The v39 (gtex_v10) id for BRCA1; the v26 (gtex_v8) id is ENSG00000012048.22.
BRCA1_V39 = "ENSG00000012048.20"


@contextmanager
def patch_service(mock_service: AsyncMock) -> Iterator[None]:
    targets = [
        "gtex_link.mcp.service_adapters.get_gtex_service",
        "gtex_link.mcp.tools.reference.get_gtex_service",
        "gtex_link.mcp.tools.expression.get_gtex_service",
        "gtex_link.mcp.tools.search_fetch.get_gtex_service",
    ]
    with (
        patch(targets[0], return_value=mock_service),
        patch(targets[1], return_value=mock_service),
        patch(targets[2], return_value=mock_service),
        patch(targets[3], return_value=mock_service),
    ):
        yield


async def _call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    mcp = create_gtex_mcp(profile=MCPToolProfile.FULL)
    result = await mcp.call_tool(name, arguments)
    return json.loads(result.content[0].text)


def _paging(total: int) -> PaginationInfo:
    return PaginationInfo(numberOfPages=1, page=0, maxItemsPerPage=250, totalNumberOfItems=total)


def _v10_service() -> AsyncMock:
    """A service whose every expression route answers with gtex_v10 rows."""
    gene = Gene.model_validate(
        {
            "chromosome": "chr17",
            "dataSource": "GENCODE",
            "description": "BRCA1 DNA repair associated",
            "end": 43125364,
            "entrezGeneId": 672,
            "gencodeId": BRCA1_V39,
            "gencodeVersion": "v39",
            "geneStatus": "KNOWN",
            "geneSymbol": "BRCA1",
            "geneSymbolUpper": "BRCA1",
            "geneType": "protein_coding",
            "genomeBuild": "GRCh38",
            "start": 43044295,
            "strand": "-",
            "tss": 43125364,
        }
    )
    median = MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v10",
            "ontologyId": "UBERON:0000178",
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "median": 12.5,
            "numSamples": 183,
            "tissueSiteDetailId": "Whole_Blood",
            "unit": "TPM",
        }
    )
    individual = GeneExpression.model_validate(
        {
            "data": [1.0, 2.0],
            "datasetId": "gtex_v10",
            "tissueSiteDetailId": "Whole_Blood",
            "ontologyId": "UBERON:0000178",
            "subsetGroup": None,
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "unit": "TPM",
        }
    )
    top = TopExpressedGenes.model_validate(
        {
            "datasetId": "gtex_v10",
            "tissueSiteDetailId": "Whole_Blood",
            "ontologyId": "UBERON:0000178",
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "median": 12.5,
            "unit": "TPM",
        }
    )
    transcript = Transcript.model_validate(
        {
            "start": 43044295,
            "end": 43125364,
            "featureType": "transcript",
            "genomeBuild": "GRCh38",
            "transcriptId": "ENST00000357654.7",
            "source": "ENSEMBL",
            "chromosome": "chr17",
            "gencodeId": BRCA1_V39,
            "geneSymbol": "BRCA1",
            "gencodeVersion": "v39",
            "strand": "-",
        }
    )
    service = AsyncMock()
    service.get_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[gene], pagingInfo=_paging(1))
    )
    service.get_transcripts = AsyncMock(
        return_value=PaginatedTranscriptResponse(data=[transcript], pagingInfo=_paging(1))
    )
    service.search_genes = AsyncMock(
        return_value=PaginatedGeneResponse(data=[gene], pagingInfo=_paging(1))
    )
    service.get_median_gene_expression = AsyncMock(
        return_value=PaginatedMedianGeneExpressionResponse(data=[median], pagingInfo=_paging(1))
    )
    service.get_gene_expression = AsyncMock(
        return_value=PaginatedGeneExpressionResponse(data=[individual], pagingInfo=_paging(1))
    )
    service.get_top_expressed_genes = AsyncMock(
        return_value=PaginatedTopExpressedGenesResponse(data=[top], pagingInfo=_paging(1))
    )
    service.get_tissue_site_details = AsyncMock(
        return_value=PaginatedTissueSiteDetailResponse(data=[], pagingInfo=_paging(0))
    )
    return service


# Every dataset-scoped tool, with the arguments that reach its happy path.
DATASET_SCOPED: dict[str, dict[str, Any]] = {
    "get_median_expression_levels": {"gencode_id": ["BRCA1"]},
    "get_individual_expression_data": {"gencode_id": ["BRCA1"]},
    "get_top_expressed_genes_by_tissue": {"tissue_site_detail_id": "Whole_Blood"},
}


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(DATASET_SCOPED))
async def test_dataset_scoped_tool_reports_the_release_it_was_asked_for(tool: str) -> None:
    """The tool must WIRE its dataset_id into the envelope, not just be able to.

    Drop `dataset_id=dataset_id` from this tool's `McpErrorContext` and this test
    fails (verified by reverting it) -- which is the whole point: it pins the
    behaviour, not the implementation.
    """
    with patch_service(_v10_service()):
        payload = await _call_tool(tool, {**DATASET_SCOPED[tool], "dataset_id": "gtex_v10"})

    assert payload["success"] is True, payload
    assert payload["_meta"]["dataset_id"] == "gtex_v10"
    assert payload["_meta"]["gtex_release"] == "gtex_v10"
    assert payload["_meta"]["gencode_version"] == "v39"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(DATASET_SCOPED))
async def test_dataset_free_default_still_reports_the_server_default(tool: str) -> None:
    """Omitting dataset_id keeps the gtex_v8 / v26 provenance."""
    service = _v10_service()
    with patch_service(service):
        payload = await _call_tool(tool, DATASET_SCOPED[tool])

    assert payload["success"] is True, payload
    assert payload["_meta"]["gtex_release"] == "gtex_v8"
    assert payload["_meta"]["gencode_version"] == "v26"


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(DATASET_SCOPED))
async def test_unknown_dataset_id_is_rejected_before_any_upstream_call(tool: str) -> None:
    """An unknown dataset must not be silently treated as the default release.

    `gencode_version_for_dataset` used to default an UNKNOWN dataset to v26, and
    the gene-id resolution ran BEFORE request validation -- so
    `dataset_id="not_a_dataset"` resolved genes against v26 upstream and only
    then failed. Reject unknown datasets at the top of the tool: no upstream call,
    and the caller's dataset_id is never echoed into the error message.
    """
    service = _v10_service()
    with patch_service(service):
        payload = await _call_tool(tool, {**DATASET_SCOPED[tool], "dataset_id": "not_a_dataset"})

    assert payload["success"] is False
    assert payload["error_code"] == "invalid_input"
    assert "not_a_dataset" not in payload["message"]
    assert payload["_meta"]["gtex_release"] == "gtex_v8"  # the default, never the caller's text

    for route in (
        service.get_genes,
        service.get_median_gene_expression,
        service.get_gene_expression,
        service.get_top_expressed_genes,
        service.get_tissue_site_details,
    ):
        route.assert_not_awaited()


# Which tools carry a provenance `_meta` -- and which deliberately do NOT.
# `fetch` returns the flat OpenAI Apps-SDK / deep-research document shape
# ({id, title, text, url, metadata}), which is contractual and has no `_meta`
# slot; `get_server_capabilities` IS the provenance document. Any other tool
# goes through `run_mcp_tool` and therefore carries `_meta`.
PROVENANCE_META_TOOLS = {
    "search",
    "search_genes",
    "get_gene_information",
    "get_transcript_information",
    "get_median_expression_levels",
    "get_individual_expression_data",
    "get_top_expressed_genes_by_tissue",
}
NO_PROVENANCE_META_TOOLS = {"fetch", "get_server_capabilities"}

_MINIMAL_ARGS: dict[str, dict[str, Any]] = {
    "search": {"query": "BRCA1"},
    "fetch": {"id": "gene:ENSG00000012048.22"},
    "search_genes": {"query": "BRCA1"},
    "get_gene_information": {"gene_id": ["BRCA1"]},
    "get_transcript_information": {"gencode_id": "ENSG00000012048.22"},
    "get_server_capabilities": {},
    **DATASET_SCOPED,
}


def test_the_meta_partition_covers_every_registered_tool() -> None:
    """A new tool must be classified, not silently inherit a docs claim."""
    assert set(_ALL_TOOLS) == PROVENANCE_META_TOOLS | NO_PROVENANCE_META_TOOLS
    assert not PROVENANCE_META_TOOLS & NO_PROVENANCE_META_TOOLS
    assert set(_MINIMAL_ARGS) == set(_ALL_TOOLS)


# docs/data.md's "Which tools carry `_meta`" table: | `tool` | yes/no | ... |
ROOT = Path(__file__).resolve().parents[2]
DATA_DOC = ROOT / "docs" / "data.md"
_META_ROW_RE = re.compile(r"^\|\s*`(\w+)`\s*\|\s*(yes|no)\s*\|", re.MULTILINE)

# `docs/superpowers/` holds DATED design records (specs and plans, e.g.
# 2026-06-01-mcp-excellence-design.md). They describe intent as it stood when written
# -- some of it superseded -- and rewriting them to match today's code would falsify
# the record. They are therefore excluded from the prose lint, and instead FENCED: every
# file under here must carry a banner marking it as historical, enforced by
# `test_archived_design_records_are_fenced` below, so the archive can never quietly
# grow into a source of false current claims.
ARCHIVE_ROOTS = (ROOT / "docs" / "superpowers",)
ARCHIVE_BANNER = "**Historical design record"


def _is_archived(path: Path) -> bool:
    return any(root in path.parents for root in ARCHIVE_ROOTS)


# Every prose surface that can make a claim about `_meta` to a human or a model. GLOBBED,
# never hardcoded: a hand-maintained file list is the bug this guard exists to catch (the
# previous list opened 5 of the repo's 61 markdown files, so a false claim in, say,
# docs/deployment.md sailed through). The corpus is the whole README (a false claim in
# `## Why` is just as false as one in `## Data & provenance`), every non-archived doc, and
# the client-facing strings the server itself ships (MCP instructions, usage notes,
# capabilities descriptions).
CLIENT_FACING_STRINGS = [
    ROOT / "gtex_link" / "mcp" / "resources.py",
    ROOT / "gtex_link" / "mcp" / "metadata.py",
]
PROSE_SURFACES = [
    *[p for p in sorted(ROOT.glob("docs/**/*.md")) if not _is_archived(p)],
    ROOT / "README.md",
    *CLIENT_FACING_STRINGS,
]

# `_meta` as a token: matches "`_meta`" and "_meta.next_commands", but NOT the
# unrelated `api_v2_metadata_dataset_get` endpoint docs, nor this file's own name
# (`test_provenance_meta.py`) where `_meta` is preceded by a word character.
_META_TOKEN = re.compile(r"(?<!\w)_meta\b")
_UNIVERSAL = re.compile(r"\b(every|all|each)\b", re.IGNORECASE)
# Wording that signals "…except these tools": the exact shape that has now been
# wrong twice ("all but `fetch`" — silently dropping `get_server_capabilities`).
_EXCLUSION = re.compile(r"\b(but|except|without)\b|carries no|carry no|no `?_meta", re.IGNORECASE)
# A universal that is explicitly scoped, and therefore true.
_SCOPED = re.compile(
    r"not every|with a `_meta` frame|that carries a `_meta` frame|"
    r"that has a `_meta` frame|see the table",
    re.IGNORECASE,
)
# Rows of the per-tool table above are owned by the table tests, not the prose lint.
_TABLE_ROW = re.compile(r"^\|\s*`\w+`\s*\|\s*(yes|no)\s*\|")


def _prose_claims() -> list[tuple[str, str]]:
    """Every sentence, across all prose surfaces, that mentions `_meta`.

    Sentences are reassembled from wrapped lines first (a claim split across two
    lines is still one claim -- and the README's `## Why` claim is wrapped, which
    is exactly where the last false one hid).
    """
    claims: list[tuple[str, str]] = []
    for path in PROSE_SURFACES:
        for block in path.read_text(encoding="utf-8").split("\n\n"):
            lines = [
                ln
                for ln in block.splitlines()
                # Per-tool table rows are owned by the table tests above; Python
                # comments are internal notes, not claims shipped to a client.
                if not _TABLE_ROW.match(ln.strip()) and not ln.strip().startswith("#")
            ]
            paragraph = " ".join(lines)
            for sentence in re.split(r"(?<=[.!?])\s+", paragraph):
                if _META_TOKEN.search(sentence):
                    claims.append((path.name, " ".join(sentence.split())))
    return claims


def test_every_markdown_file_is_either_linted_or_fenced() -> None:
    """No doc may be silently skipped -- that is how every false claim here survived.

    Each markdown file under `docs/` (plus the README) must be EITHER in the linted
    corpus OR under a fenced archive root. There is no third bucket, and no
    hand-maintained skip list.
    """
    every_md = {*ROOT.glob("docs/**/*.md"), ROOT / "README.md"}
    linted = set(PROSE_SURFACES) - set(CLIENT_FACING_STRINGS)
    fenced = {p for p in every_md if _is_archived(p)}

    assert linted | fenced == every_md, (
        "markdown files that are neither linted nor fenced: "
        f"{sorted(str(p.relative_to(ROOT)) for p in every_md - linted - fenced)}"
    )
    assert not linted & fenced


def test_archived_design_records_are_fenced() -> None:
    """Every archived doc must SAY it is archived -- the exclusion must be honest.

    The lint skips `docs/superpowers/`, so nothing checks those files' claims. That is
    only defensible if a reader (or an agent) can see at a glance that they are dated
    records, not the live contract. Enforcing the banner here means the convention
    cannot be forgotten: add a file to the archive without the banner and CI fails.
    """
    archived = sorted(p for root in ARCHIVE_ROOTS for p in root.glob("**/*.md"))
    assert archived, "archive roots are empty -- did the archive move?"

    unfenced = [
        str(path.relative_to(ROOT))
        for path in archived
        # The banner must be at the TOP, where it is actually seen.
        if ARCHIVE_BANNER not in "\n".join(path.read_text(encoding="utf-8").splitlines()[:10])
    ]
    assert not unfenced, (
        f"archived design records missing the {ARCHIVE_BANNER!r} banner in their first "
        f"10 lines (they are excluded from the prose lint, so they MUST announce that "
        f"they are historical): {unfenced}"
    )


def test_no_prose_names_only_some_of_the_meta_less_tools() -> None:
    """An "all but X" claim must name EVERY tool that has no `_meta`.

    This is the bug that shipped twice: README said "all but `fetch`" and the
    capabilities doc said "`fetch` ... carries no _meta at all", both silently
    dropping `get_server_capabilities`. The old guard only scanned ONE README
    section, so it could not see either. The oracle is the live classification.
    """
    offenders = [
        (where, sentence)
        for where, sentence in _prose_claims()
        if _EXCLUSION.search(sentence)
        and (named := {t for t in NO_PROVENANCE_META_TOOLS if t in sentence})
        and named != NO_PROVENANCE_META_TOOLS
    ]
    assert not offenders, (
        "prose names only SOME of the tools that carry no `_meta` "
        f"(all of them: {sorted(NO_PROVENANCE_META_TOOLS)}):\n"
        + "\n".join(f"  {where}: {sentence}" for where, sentence in offenders)
    )


def test_no_prose_claims_meta_is_universal() -> None:
    """No prose may claim `_meta` is on every/all/each response without scoping it.

    A universal claim is allowed only if it is explicitly scoped (e.g. "every tool
    that has a `_meta` frame") or names the exceptions outright.
    """
    offenders = [
        (where, sentence)
        for where, sentence in _prose_claims()
        if _UNIVERSAL.search(sentence)
        and not _SCOPED.search(sentence)
        and not {t for t in NO_PROVENANCE_META_TOOLS if t in sentence}
    ]
    assert not offenders, (
        "prose claims `_meta` universality without scoping it or naming the "
        f"exceptions ({sorted(NO_PROVENANCE_META_TOOLS)}):\n"
        + "\n".join(f"  {where}: {sentence}" for where, sentence in offenders)
    )


def _documented_meta_table() -> dict[str, bool]:
    """Parse the docs table into {tool: carries_meta}."""
    text = DATA_DOC.read_text(encoding="utf-8")
    start = text.index("#### Which tools carry `_meta`")
    end = text.index("\n## ", start)
    return {tool: flag == "yes" for tool, flag in _META_ROW_RE.findall(text[start:end])}


def test_docs_meta_table_is_actually_owned_by_this_test() -> None:
    """The docs table must match the LIVE classification -- not just exist.

    Claiming a fact is machine-checked while nothing checks it is worse than not
    claiming it. `docs/data.md` says this test owns that table, so it must: flip
    `fetch` to `yes` there and this test (plus the live-behaviour test below,
    which the table drives) fails.
    """
    documented = _documented_meta_table()

    assert set(documented) == set(_ALL_TOOLS), (
        "docs/data.md's `_meta` table has drifted from the registered tools: "
        f"doc={sorted(documented)} code={sorted(_ALL_TOOLS)}"
    )
    expected = {tool: tool in PROVENANCE_META_TOOLS for tool in _ALL_TOOLS}
    assert documented == expected, (
        "docs/data.md's `_meta` table disagrees with the live classification: "
        f"doc={documented} code={expected}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(_ALL_TOOLS))
async def test_each_tool_matches_what_the_docs_table_claims(tool: str) -> None:
    """Drive the DOCUMENTED claim against the real MCP facade, tool by tool.

    This closes the loop: the table is compared to what the server actually
    returns, so a wrong `yes`/`no` in docs/data.md fails CI.
    """
    documented_has_meta = _documented_meta_table()[tool]

    with patch_service(_v10_service()):
        payload = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert ("_meta" in payload) is documented_has_meta, (
        f"docs/data.md claims {tool} "
        f"{'has' if documented_has_meta else 'has no'} `_meta`, but the live tool "
        f"{'has one' if '_meta' in payload else 'has none'}"
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(PROVENANCE_META_TOOLS))
async def test_tool_carries_provenance_meta(tool: str) -> None:
    with patch_service(_v10_service()):
        payload = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert "_meta" in payload, f"{tool} must carry a provenance _meta"
    assert payload["_meta"]["gtex_release"] in {"gtex_v8", "gtex_v10", "gtex_snrnaseq_pilot"}
    assert payload["_meta"]["unsafe_for_clinical_use"] is True


@pytest.mark.asyncio
@pytest.mark.parametrize("tool", sorted(NO_PROVENANCE_META_TOOLS))
async def test_tool_carries_no_provenance_meta(tool: str) -> None:
    """Pins the honest half of the docs claim: these two carry NO `_meta`.

    Do not "fix" this by bolting `_meta` onto `fetch` -- its flat document shape
    is fixed by the Apps SDK contract. The docs must say so instead.
    """
    with patch_service(_v10_service()):
        payload = await _call_tool(tool, _MINIMAL_ARGS[tool])

    assert "_meta" not in payload, f"{tool} unexpectedly grew a provenance _meta"
    assert "gtex_release" not in payload.get("metadata", {})
