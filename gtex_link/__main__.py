"""``python -m gtex_link`` entry — delegates to the typer CLI app."""

from __future__ import annotations

from gtex_link.cli import app

if __name__ == "__main__":
    app()
