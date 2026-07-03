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

**Ops/meta carve-out (tag-based):** tools tagged ``ops`` or ``meta`` skip the
verb rule (charset/length/no-self-prefix still apply). This carve-out set is
exactly ``{ops, meta}`` — identical to the authoritative router validator
(``genefoundry_router.cli.check_leaf_name``) — so a tool that passes here also
passes ``router doctor --strict-naming`` (no local false green). The ChatGPT /
OpenAI deep-research ``fetch`` tool (verbatim name required by the Apps SDK
integration; ``fetch`` is not a canonical verb) carries a ``meta`` tag and is
exempted via this carve-out. Its partner ``search`` passes Tier-1 on its own.
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
# Ops/meta carve-out (Standard v1.1): tools tagged ops/meta skip the verb rule.
# Exactly mirrors the router validator's carve-out set so local-green == gateway-green.
_OPS_META_TAGS = frozenset({"ops", "meta"})


async def test_tool_names_conform_to_standard_v1_1(facade: Any) -> None:
    tools = await facade.list_tools()
    assert tools, "no tools registered on the facade"
    _all_verbs = _CANONICAL_VERBS | _TIER2_VERBS
    for tool in tools:
        name = tool.name
        tags = set(getattr(tool, "tags", None) or ())
        assert _NAME_RE.match(name), f"{name!r} must match ^[a-z0-9_]{{1,50}}$"
        assert not name.startswith(f"{_NAMESPACE}_"), (
            f"{name!r} must not self-prefix the '{_NAMESPACE}' namespace "
            "token — the gateway adds it"
        )
        # Ops/meta tag carve-out: operational / Apps-SDK-contract tools skip the
        # verb rule (they still passed charset/length/no-self-prefix above).
        if tags & _OPS_META_TAGS:
            continue
        assert name.split("_", 1)[0] in _all_verbs, (
            f"{name!r} must start with a Tier-1 or Tier-2 canonical verb "
            f"{sorted(_all_verbs)} or carry an ops/meta tag"
        )


async def test_ops_meta_carveout_is_exercised_only_where_expected(facade: Any) -> None:
    """Drift guard: the only non-canonical-verb tool relying on the carve-out is
    ``fetch`` (OpenAI Apps-SDK contract). If a future tool sneaks a non-canonical
    verb past the verb rule via an ops/meta tag, this fails so the exemption gets
    an explicit review instead of silently widening the carve-out."""
    _all_verbs = _CANONICAL_VERBS | _TIER2_VERBS
    carved = {
        tool.name
        for tool in await facade.list_tools()
        if (set(getattr(tool, "tags", None) or ()) & _OPS_META_TAGS)
        and tool.name.split("_", 1)[0] not in _all_verbs
    }
    assert carved == {"fetch"}, f"unexpected ops/meta carve-out reliance: {sorted(carved)}"
