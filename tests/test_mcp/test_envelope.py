"""Tests for the shared MCP envelope boundary."""

from __future__ import annotations

import pytest

from gtex_link.exceptions import RateLimitError, ValidationError
from gtex_link.mcp.envelope import McpErrorContext, run_mcp_tool


@pytest.mark.asyncio
async def test_success_injects_success_and_meta() -> None:
    async def call() -> dict[str, object]:
        return {"data": [1, 2, 3]}

    result = await run_mcp_tool("demo", call)

    assert result["data"] == [1, 2, 3]
    assert result["success"] is True
    assert result["_meta"]["unsafe_for_clinical_use"] is True
    assert result["_meta"]["gtex_release"] == "gtex_v8"


@pytest.mark.asyncio
async def test_rate_limit_maps_to_rate_limited_envelope() -> None:
    async def call() -> dict[str, object]:
        raise RateLimitError("slow down")

    result = await run_mcp_tool("demo", call)

    assert result["success"] is False
    assert result["error_code"] == "rate_limited"
    assert "rate limit" in result["message"].lower()
    assert result["_meta"]["tool"] == "demo"


@pytest.mark.asyncio
async def test_validation_error_maps_to_invalid_input() -> None:
    async def call() -> dict[str, object]:
        raise ValidationError("bad gene", field="gencode_id")

    result = await run_mcp_tool("demo", call)

    assert result["success"] is False
    assert result["error_code"] == "invalid_input"


@pytest.mark.asyncio
async def test_explicit_mcp_tool_error_passes_code_through() -> None:
    from gtex_link.mcp.envelope import McpToolError

    async def call() -> dict[str, object]:
        raise McpToolError(error_code="not_found", message="no gene")

    result = await run_mcp_tool("demo", call, context=McpErrorContext(tool_name="demo"))

    assert result["error_code"] == "not_found"
    assert result["success"] is False


@pytest.mark.asyncio
async def test_rate_limited_is_retryable_with_backoff() -> None:
    async def call() -> dict[str, object]:
        raise RateLimitError("slow")

    result = await run_mcp_tool("demo", call)
    assert result["retryable"] is True
    assert result["recovery_action"] == "retry_backoff"


@pytest.mark.asyncio
async def test_invalid_input_is_not_retryable_reformulate() -> None:
    async def call() -> dict[str, object]:
        raise ValidationError("bad", field="gencode_id")

    result = await run_mcp_tool("demo", call)
    assert result["retryable"] is False
    assert result["recovery_action"] == "reformulate_input"


@pytest.mark.asyncio
async def test_pydantic_error_lists_field_errors() -> None:
    from gtex_link.models import MedianGeneExpressionRequest

    async def call() -> dict[str, object]:
        MedianGeneExpressionRequest.model_validate({"gencodeId": []})  # min_length=1 violation
        return {}

    result = await run_mcp_tool("demo", call)
    assert result["error_code"] == "invalid_input"
    assert isinstance(result["field_errors"], list)
    assert result["field_errors"][0]["field"]


@pytest.mark.asyncio
async def test_success_meta_includes_recommended_citation() -> None:
    async def call() -> dict[str, object]:
        return {"data": []}

    result = await run_mcp_tool("demo", call)
    assert "GTEx Consortium" in result["_meta"]["recommended_citation"]
