"""Unit contract for the error-message sanitizer primitive."""

from __future__ import annotations

from gtex_link.mcp.untrusted_content import MAX_MESSAGE_CHARS, sanitize_message


def test_sanitize_message_strips_nul_zwj_bom_and_bidi() -> None:
    dirty = "boom\x00‍﻿‮ tail"
    clean = sanitize_message(dirty)
    assert "\x00" not in clean
    assert "‍" not in clean  # zero-width joiner
    assert "﻿" not in clean  # BOM
    assert "‮" not in clean  # RTL override
    assert clean == "boom tail"


def test_sanitize_message_preserves_ordinary_prose() -> None:
    prose = "GTEx Portal returned an error. Verify the request inputs."
    assert sanitize_message(prose) == prose


def test_sanitize_message_length_capped() -> None:
    capped = sanitize_message("x" * 1000)
    assert len(capped) == MAX_MESSAGE_CHARS
    assert MAX_MESSAGE_CHARS == 280
