"""Tests for the output validation middleware hook."""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastmcp import FastMCP

from gtex_link.mcp.output_validation import install_output_validation_error_handler


@pytest.mark.asyncio
async def test_middleware_logs_and_reraises_on_tool_error(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """The middleware logs structured error info and re-raises (does not swallow)."""
    mcp = FastMCP(name="probe")
    install_output_validation_error_handler(mcp)

    # `install_output_validation_error_handler` appends a single middleware
    # instance; grab it directly so we can exercise the hook without going
    # through the full FastMCP dispatch machinery.
    middleware = mcp.middleware[-1]

    context = MagicMock()
    context.message = MagicMock()
    context.message.name = "broken_tool"

    async def boom(_ctx: object) -> None:
        raise ValueError("simulated tool failure")

    with (
        caplog.at_level(logging.ERROR, logger="gtex_link.mcp.output_validation"),
        pytest.raises(ValueError, match="simulated tool failure"),
    ):
        # `boom` is a deliberately minimal stand-in for CallNext; the
        # middleware only awaits it, so the concrete CallToolRequestParams /
        # ToolResult generic parameters are not exercised here.
        await middleware.on_call_tool(context, boom)  # type: ignore[arg-type]

    matching = [r for r in caplog.records if "MCP output validation failed" in r.message]
    assert matching, "Expected structured error log was not emitted"
    record = matching[-1]
    assert getattr(record, "tool", None) == "broken_tool"
    assert getattr(record, "error_type", None) == "ValueError"
    assert getattr(record, "error", None) == "simulated tool failure"


def test_fallback_logs_warning_when_add_middleware_missing(
    caplog: pytest.LogCaptureFixture,
) -> None:
    """If the FastMCP instance lacks add_middleware, the hook warns and returns."""

    class FakeMCP:
        pass

    with caplog.at_level(logging.WARNING, logger="gtex_link.mcp.output_validation"):
        # Deliberately exercising the duck-typed fallback for objects that do
        # not implement add_middleware; ignore the type-arg mismatch.
        install_output_validation_error_handler(FakeMCP())  # type: ignore[arg-type]

    assert any("lacks add_middleware" in r.message for r in caplog.records), (
        "Expected fallback warning was not emitted"
    )
