"""Loosen output JSON Schemas so injected envelope keys (success/_meta) pass.

The MCP SDK validates tool responses against the declared output schema. Our
run_mcp_tool injects success/_meta, so strict success schemas would reject the
envelope. Stripping `required` and forcing additionalProperties=True keeps the
schema's discovery value while letting the envelope flow through.
"""

from __future__ import annotations

from typing import Any


def relax_output_schema(schema: Any) -> Any:
    """Deep-copy *schema* with `required` stripped and objects opened."""
    if not isinstance(schema, dict):
        return schema
    relaxed: dict[str, Any] = {}
    for key, value in schema.items():
        if key == "required":
            continue
        if key == "additionalProperties":
            relaxed[key] = True
            continue
        if key == "properties" and isinstance(value, dict):
            relaxed[key] = {k: relax_output_schema(v) for k, v in value.items()}
            continue
        if key == "items":
            relaxed[key] = (
                [relax_output_schema(v) for v in value]
                if isinstance(value, list)
                else relax_output_schema(value)
            )
            continue
        if key in ("$defs", "definitions") and isinstance(value, dict):
            relaxed[key] = {k: relax_output_schema(v) for k, v in value.items()}
            continue
        if key in ("oneOf", "anyOf", "allOf") and isinstance(value, list):
            relaxed[key] = [relax_output_schema(v) for v in value]
            continue
        relaxed[key] = value
    if relaxed.get("type") == "object" and "additionalProperties" not in relaxed:
        relaxed["additionalProperties"] = True
    return relaxed
