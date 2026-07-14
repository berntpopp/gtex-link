"""The README's ``## Tools`` table must match the registered MCP surface exactly.

GeneFoundry README Standard v1, Rule 6: the tool table is machine-verified, not
hand-maintained. Adding, renaming, or removing a tool without updating the README
fails here rather than shipping a README that quietly lies.

The live tool list comes from the same ``facade`` fixture ``test_tool_names.py``
uses (``tests/unit/conftest.py`` -> ``create_gtex_mcp(profile=MCPToolProfile.FULL)``),
so this test cannot drift from the real registration path. It is deliberately never
hardcoded.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

README = Path(__file__).resolve().parents[2] / "README.md"

# A table row: | `tool_name` | Purpose |
_ROW_RE = re.compile(r"^\|\s*`([a-z0-9_]+)`\s*\|")


def _readme_tool_names() -> set[str]:
    """Tool names in the README's ``## Tools`` table.

    Scans from the ``## Tools`` heading to the next H2, so prose tables elsewhere
    in the README (e.g. Data & provenance) cannot leak in.
    """
    lines = README.read_text(encoding="utf-8").splitlines()
    try:
        start = lines.index("## Tools")
    except ValueError as exc:  # pragma: no cover - guards a malformed README
        raise AssertionError("README.md has no '## Tools' section") from exc

    names: set[str] = set()
    for line in lines[start + 1 :]:
        if line.startswith("## "):
            break
        match = _ROW_RE.match(line)
        if match:
            names.add(match.group(1))
    return names


async def test_readme_tool_table_matches_registered_tools(facade: Any) -> None:
    registered = {tool.name for tool in await facade.list_tools()}
    assert registered, "no tools registered on the facade"

    documented = _readme_tool_names()

    missing = registered - documented
    extra = documented - registered
    assert not missing, f"tools registered but absent from the README table: {sorted(missing)}"
    assert not extra, f"README table lists tools that are not registered: {sorted(extra)}"
    assert documented == registered
