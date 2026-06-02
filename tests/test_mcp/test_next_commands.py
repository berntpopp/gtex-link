from __future__ import annotations

from gtex_link.mcp.next_commands import after_gene_search, after_median, cmd


def test_cmd_shape() -> None:
    assert cmd("get_gene_information", gene_id=["UMOD"]) == {
        "tool": "get_gene_information", "arguments": {"gene_id": ["UMOD"]}
    }


def test_after_gene_search_points_at_gene_info_then_median() -> None:
    cmds = after_gene_search(["ENSG00000169344.15"])
    tools = [c["tool"] for c in cmds]
    assert tools == ["get_gene_information", "get_median_expression_levels"]


def test_after_median_points_at_top_expressed_for_top_tissue() -> None:
    cmds = after_median("Kidney_Medulla")
    assert cmds[0]["tool"] == "get_top_expressed_genes_by_tissue"
    assert cmds[0]["arguments"]["tissue_site_detail_id"] == "Kidney_Medulla"
