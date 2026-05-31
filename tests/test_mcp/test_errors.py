"""Tests for MCP error mapping."""

from __future__ import annotations

from gtex_link.exceptions import (
    GTExAPIError,
    RateLimitError,
    ServiceUnavailableError,
    ValidationError,
)
from gtex_link.mcp.errors import map_to_mcp_error_message


def test_rate_limit_error_maps_to_friendly_message() -> None:
    err = RateLimitError("Rate limit exceeded", retry_after=10.0)
    msg = map_to_mcp_error_message(err)
    assert "rate limit" in msg.lower()
    # Does not leak retry-after detail or upstream URL
    assert "https" not in msg


def test_service_unavailable_error_maps_to_friendly_message() -> None:
    err = ServiceUnavailableError()
    msg = map_to_mcp_error_message(err)
    assert "unavailable" in msg.lower()


def test_validation_error_maps_to_friendly_message() -> None:
    err = ValidationError("must be one of A, B, C", field="dataset")
    msg = map_to_mcp_error_message(err)
    assert "dataset" in msg
    assert "must be one of" in msg


def test_gtex_api_error_maps_to_generic_message() -> None:
    err = GTExAPIError("internal upstream failure", status_code=502)
    msg = map_to_mcp_error_message(err)
    assert "502" not in msg  # leaked detail
    assert "GTEx" in msg


def test_unknown_exception_maps_to_generic_message() -> None:
    err = RuntimeError("internal traceback should not leak")
    msg = map_to_mcp_error_message(err)
    assert "internal traceback" not in msg


def test_pydantic_validation_error_maps_to_invalid_input() -> None:
    from pydantic import BaseModel
    from pydantic import ValidationError as PydanticValidationError

    class _Probe(BaseModel):
        x: int

    try:
        _Probe.model_validate({"x": "not-an-int"})
    except PydanticValidationError as exc:
        msg = map_to_mcp_error_message(exc)
        assert "Invalid input" in msg
        assert "x" in msg
    else:
        raise AssertionError("Expected PydanticValidationError")
