"""F-19: the Docker builder must pin uv by digest, not bootstrap floating pip/uv.

An unbounded ``pip install --upgrade pip uv`` resolves whatever the index serves
at build time, so two builds of the same commit are not byte-reproducible and a
compromised/yanked installer could slip in. Replace it with a digest-pinned uv
COPY (the fleet-shared anchor) and prove the floating upgrade is gone.
"""

from __future__ import annotations

from pathlib import Path

DOCKERFILE = Path(__file__).resolve().parents[1] / "docker" / "Dockerfile"

# Fleet-shared uv anchor (identical digest across the router + every -link repo).
UV_PINNED_COPY = (
    "ghcr.io/astral-sh/uv:0.8.7@sha256:"
    "1e26f9a868360eeb32500a35e05787ffff3402f01a8dc8168ef6aee44aef0aab"
)


def test_dockerfile_pins_uv_and_has_no_floating_pip_upgrade() -> None:
    """No floating ``pip install --upgrade`` and the exact uv digest COPY present."""
    text = DOCKERFILE.read_text(encoding="utf-8")
    assert "pip install --upgrade" not in text, (
        "floating pip/uv upgrade must be removed (non-reproducible build bootstrap)"
    )
    assert UV_PINNED_COPY in text, "builder must COPY the digest-pinned uv binary"
