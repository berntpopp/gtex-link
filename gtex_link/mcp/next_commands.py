"""Builders for _meta.next_commands entries: {tool, arguments} (never empty)."""

from __future__ import annotations

from typing import Any


def cmd(tool: str, **arguments: Any) -> dict[str, Any]:
    """One ready-to-call next step."""
    return {"tool": tool, "arguments": arguments}


def after_gene_search(gencode_ids: list[str]) -> list[dict[str, Any]]:
    """After resolving genes: fetch detail, then median expression."""
    return [
        cmd("get_gene_information", gene_id=gencode_ids),
        cmd("get_median_expression_levels", gencode_id=gencode_ids),
    ]


def after_median(top_tissue: str | None) -> list[dict[str, Any]]:
    """After median expression: pivot to what else is expressed in the top tissue."""
    if not top_tissue:
        return []
    return [cmd("get_top_expressed_genes_by_tissue", tissue_site_detail_id=top_tissue)]
