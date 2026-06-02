from __future__ import annotations

from gtex_link.mcp.schema_relax import relax_output_schema


def test_relax_strips_required_and_opens_objects() -> None:
    schema = {
        "type": "object",
        "required": ["headline", "genes"],
        "additionalProperties": False,
        "properties": {"headline": {"type": "string"}},
    }
    relaxed = relax_output_schema(schema)
    assert "required" not in relaxed
    assert relaxed["additionalProperties"] is True
    assert relaxed["properties"]["headline"] == {"type": "string"}
