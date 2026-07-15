"""Tests for median-row grouping/shaping."""

from __future__ import annotations

from gtex_link.mcp.shaping import group_median
from gtex_link.models.responses import MedianGeneExpression


def _row(
    tissue: str, value: float, gene: str = "UMOD", gencode: str = "ENSG00000169344.15"
) -> MedianGeneExpression:
    return MedianGeneExpression.model_validate(
        {
            "datasetId": "gtex_v8",
            "ontologyId": "UBERON:1",
            "gencodeId": gencode,
            "geneSymbol": gene,
            "median": value,
            "numSamples": None,
            "tissueSiteDetailId": tissue,
            "unit": "TPM",
        }
    )


def test_group_sorts_descending_and_applies_top_n() -> None:
    rows = [
        _row("Adipose_Subcutaneous", 0.0),
        _row("Kidney_Medulla", 2116.02),
        _row("Kidney_Cortex", 190.1),
    ]
    result = group_median(
        rows,
        counts={"Kidney_Medulla": 4, "Kidney_Cortex": 85, "Adipose_Subcutaneous": 663},
        sort="desc",
        top_n=2,
        response_mode="compact",
        spread_by_key={},
    )
    group = result.genes[0]
    assert [t.tissue for t in group.tissues] == ["Kidney_Medulla", "Kidney_Cortex"]
    assert group.tissues[0].n == 4
    assert group.tissues_returned == 2
    assert group.tissues_total == 3
    assert "Kidney_Medulla" in result.headline and "2116.02" in result.headline


def test_compact_omits_ontology_full_includes_it() -> None:
    rows = [_row("Kidney_Medulla", 2116.02)]
    compact = group_median(
        rows, counts={}, sort="desc", top_n=None, response_mode="compact", spread_by_key={}
    )
    full = group_median(
        rows, counts={}, sort="desc", top_n=None, response_mode="full", spread_by_key={}
    )
    assert compact.genes[0].tissues[0].ontology_id is None
    assert full.genes[0].tissues[0].ontology_id == "UBERON:1"


def test_multiple_genes_grouped_separately() -> None:
    rows = [
        _row("Kidney_Medulla", 2116.0, "UMOD", "ENSG00000169344.15"),
        _row("Whole_Blood", 5.0, "BRCA1", "ENSG00000012048.22"),
    ]
    result = group_median(
        rows, counts={}, sort="desc", top_n=None, response_mode="compact", spread_by_key={}
    )
    assert {g.gene_symbol for g in result.genes} == {"UMOD", "BRCA1"}


def test_tissues_filter_restricts_and_sets_total() -> None:
    rows = [
        _row("Brain_Cerebellum", 0.0),
        _row("Kidney_Cortex", 190.1),
        _row("Kidney_Medulla", 2116.02),
    ]
    result = group_median(
        rows,
        counts={},
        sort="desc",
        top_n=None,
        response_mode="compact",
        spread_by_key={},
        tissues_filter={"Kidney_Cortex", "Kidney_Medulla"},
    )
    group = result.genes[0]
    assert {t.tissue for t in group.tissues} == {"Kidney_Cortex", "Kidney_Medulla"}
    assert group.tissues_total == 2
    assert group.tissues_returned == 2


def test_median_values_are_rounded() -> None:
    rows = [_row("Kidney_Medulla", 484.38300000000004)]
    result = group_median(
        rows, counts={}, sort="desc", top_n=None, response_mode="compact", spread_by_key={}
    )
    assert result.genes[0].tissues[0].median == 484.383


def _umod_rows() -> list[MedianGeneExpression]:
    return [
        _row("Adipose_Subcutaneous", 0.0),
        _row("Kidney_Cortex", 190.1),
        _row("Kidney_Medulla", 2116.02),
    ]


def test_headline_asc_reports_lowest_never_highest() -> None:
    """Regression (issue #76 D1): sort=asc must not label the LEAST-expressed tissue 'highest'."""
    result = group_median(
        _umod_rows(), counts={}, sort="asc", top_n=3, response_mode="compact", spread_by_key={}
    )
    # sort=asc puts the least-expressed tissue first; the headline must say so.
    assert "highest" not in result.headline.lower()
    assert "lowest" in result.headline.lower()
    assert "Adipose_Subcutaneous" in result.headline
    assert "0.00" in result.headline


def test_headline_none_uses_no_superlative() -> None:
    """Regression (issue #76 D1): sort=none must not claim 'highest' (or 'lowest')."""
    result = group_median(
        _umod_rows(), counts={}, sort="none", top_n=None, response_mode="compact", spread_by_key={}
    )
    assert "highest" not in result.headline.lower()
    assert "lowest" not in result.headline.lower()


def test_headline_desc_still_reports_highest() -> None:
    result = group_median(
        _umod_rows(), counts={}, sort="desc", top_n=3, response_mode="compact", spread_by_key={}
    )
    assert "highest" in result.headline.lower()
    assert "Kidney_Medulla" in result.headline
    assert "2116.02" in result.headline
