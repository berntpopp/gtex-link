"""Tool-name compliance with the GeneFoundry Tool-Naming Standard v1.1.

Every registered tool must be unprefixed, snake_case, <= 50 chars, and start with
a canonical verb so it composes cleanly behind the ``genefoundry-router`` gateway,
which mounts this server under the ``gtex`` namespace (tools surface as
``gtex_<tool>``). Guards against future drift. See issue berntpopp/gtex-link#34.

**Ratified verb canon (v1.1):**

  Tier-1 (universal read/query): get, search, list, resolve, find, compare,
  compute, map
  Tier-2 (sanctioned action/compute): predict, annotate, recode, liftover,
  analyze, score, submit, export, generate, download

**Ops/meta carve-out:** tools exempted by the Standard v1.1 ops/meta tag
carve-out (operational or Apps-SDK contract tools) are listed in
``_OPS_META_CARVE_OUT`` and skip the verb rule (charset/length/no-self-prefix
still apply). The ``search`` / ``fetch`` deep-research pair is the OpenAI
deep-research / Apps SDK contract; ``fetch`` is not a domain verb, so it
qualifies for the carve-out. ``search`` passes the Tier-1 check on its own.
"""

from __future__ import annotations

import re
from typing import Any

_NAME_RE = re.compile(r"^[a-z0-9_]{1,50}$")
# Tier-1: universal read/query canon (Tool-Naming Standard v1.1, ratified 2026-06-30)
_CANONICAL_VERBS = frozenset(
    {"get", "search", "list", "resolve", "find", "compare", "compute", "map"}
)
# Tier-2: sanctioned domain action/compute verbs (v1.1)
_TIER2_VERBS = frozenset(
    {
        "predict",
        "annotate",
        "recode",
        "liftover",
        "analyze",
        "score",
        "submit",
        "export",
        "generate",
        "download",
    }
)
_NAMESPACE = "gtex"
# Ops/meta carve-out (Standard v1.1 §ops/meta): tools exempted from the verb rule
# because they fulfil an operational or Apps-SDK contract rather than a domain
# query. The ChatGPT / OpenAI deep-research ``fetch`` tool (verbatim name required
# by the Apps SDK integration) lives here. ``search`` is also in the pair but
# passes Tier-1 on its own.
_OPS_META_CARVE_OUT = frozenset({"fetch"})


async def test_tool_names_conform_to_standard_v1(facade: Any) -> None:
    names = sorted(t.name for t in await facade.list_tools())
    assert names, "no tools registered on the facade"
    _all_verbs = _CANONICAL_VERBS | _TIER2_VERBS
    for name in names:
        assert _NAME_RE.match(name), f"{name!r} must match ^[a-z0-9_]{{1,50}}$"
        if name not in _OPS_META_CARVE_OUT:
            assert name.split("_", 1)[0] in _all_verbs, (
                f"{name!r} must start with a Tier-1 or Tier-2 canonical verb "
                f"{sorted(_all_verbs)} or be listed in _OPS_META_CARVE_OUT"
            )
        assert not name.startswith(f"{_NAMESPACE}_"), (
            f"{name!r} must not self-prefix the '{_NAMESPACE}' namespace "
            "token — the gateway adds it"
        )
