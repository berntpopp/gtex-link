"""GTEx-Link: High-performance MCP/API server for GTEx Portal."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("gtex-link")
except PackageNotFoundError:  # pragma: no cover - source tree without install
    __version__ = "0.0.0"

__author__ = "GTEx-Link Development Team"
