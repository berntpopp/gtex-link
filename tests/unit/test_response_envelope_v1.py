"""Locks the ratified GeneFoundry Response-Envelope Standard v1 (flat banner)
at this backend's MCP wrapper boundary (``gtex_link.mcp.envelope.run_mcp_tool``).
Adapted from clingen-link (the fleet reference, PR #20). SUCCESS ->
``{success, results|result, _meta(unsafe_for_clinical_use)}``; FAILURE -> flat
``{success: False, error_code, message, retryable, recovery_action, _meta{tool,...}}``.
"""

from __future__ import annotations

from gtex_link.exceptions import ValidationError
from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool


async def test_success_envelope_matches_response_envelope_standard_v1() -> None:
    async def call() -> dict[str, object]:
        return {"results": [{"id": "x"}]}

    result = await run_mcp_tool("get_median_expression_levels", call)
    assert result["success"] is True
    assert result["results"] == [{"id": "x"}]
    assert result["_meta"]["unsafe_for_clinical_use"] is True


async def test_single_item_result_key_is_preserved() -> None:
    async def call() -> dict[str, object]:
        return {"result": {"id": "x"}}

    result = await run_mcp_tool("get_median_expression_levels", call)
    assert result["success"] is True
    assert result["result"] == {"id": "x"}
    assert result["_meta"]["unsafe_for_clinical_use"] is True


async def test_error_envelope_is_flat_not_a_bare_exception() -> None:
    async def call() -> dict[str, object]:
        raise ValidationError("bad input", field="gene_id")

    result = await run_mcp_tool(
        "get_median_expression_levels",
        call,
        context=McpErrorContext(tool_name="get_median_expression_levels"),
    )
    assert result["success"] is False
    assert isinstance(result["error_code"], str) and result["error_code"]
    assert isinstance(result["message"], str) and result["message"]
    assert isinstance(result["retryable"], bool)
    assert isinstance(result["recovery_action"], str)
    assert "error" not in result  # flat, not nested
    assert result["_meta"]["tool"] == "get_median_expression_levels"
    assert result["_meta"]["unsafe_for_clinical_use"] is True
