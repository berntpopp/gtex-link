"""`docs/configuration.md` must document every settable env var, under a name that binds.

Two failure modes this pins, both of which had already happened:

1. **Documented but inert.** `api` and `cache` are nested models. Without
   `env_nested_delimiter`, pydantic-settings ignores per-field env names and
   `extra="ignore"` swallows them without a word -- so the `GTEX_LINK_CACHE_TTL`
   and `GTEX_LINK_API_RATE_LIMIT_PER_SECOND` that the docs *and*
   `docker/docker-compose.prod.yml` passed were dead letters. A doc that names a
   variable which does nothing is worse than no doc.
2. **Undocumented but live.** The README claims configuration.md covers *every*
   `GTEX_LINK_*` variable. That claim is only worth making if a machine checks it.

Both directions are asserted, so the tables cannot drift from `config.py`.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel
from pydantic_settings import BaseSettings

from gtex_link.config import ServerSettings

CONFIG_DOC = Path(__file__).resolve().parents[2] / "docs" / "configuration.md"
PREFIX = "GTEX_LINK_"
DELIM = "__"

# Named in configuration.md's Docker section but read by Compose, not by
# ServerSettings. Deliberately allowlisted rather than silently tolerated.
COMPOSE_ONLY = {"GTEX_LINK_HOST_PORT"}


def _env_names(model: type[BaseModel], prefix: str = PREFIX) -> set[str]:
    """Every env var name that binds a field on *model*, recursing into groups."""
    names: set[str] = set()
    for field_name, field in model.model_fields.items():
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            names |= _env_names(annotation, f"{prefix}{field_name.upper()}{DELIM}")
        else:
            names.add(f"{prefix}{field_name.upper()}")
    return names


def _documented_names() -> set[str]:
    """Names in the *variable column* of a table row: `| \\`GTEX_LINK_X\\` | default | ... |`.

    Deliberately not a whole-file scan. The prose legitimately names inert
    spellings in order to warn against them ("a single-underscore
    `GTEX_LINK_CACHE_TTL` does nothing at all"); it is the tables that make the
    claim "this variable is settable".
    """
    rows = re.findall(
        rf"^\|\s*`({PREFIX}[A-Z0-9_]+)`\s*\|",
        CONFIG_DOC.read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    return set(rows)


def test_settings_model_config_is_the_documented_contract() -> None:
    config = ServerSettings.model_config
    assert config.get("env_prefix") == PREFIX
    assert config.get("env_nested_delimiter") == DELIM


def test_every_setting_is_documented() -> None:
    missing = _env_names(ServerSettings) - _documented_names()
    assert not missing, (
        f"settable but absent from docs/configuration.md: {sorted(missing)}. "
        "The README promises the file covers every GTEX_LINK_* variable."
    )


def test_no_documented_variable_is_inert() -> None:
    """Every GTEX_LINK_* name in the doc must actually bind to a field."""
    bogus = _documented_names() - _env_names(ServerSettings) - COMPOSE_ONLY
    assert not bogus, (
        f"documented but ignored by ServerSettings: {sorted(bogus)}. "
        "extra='ignore' means an operator setting these gets no effect and no warning."
    )


@pytest.mark.parametrize(
    ("env_name", "path", "raw", "expected"),
    [
        ("GTEX_LINK_PORT", ("port",), "9099", 9099),
        ("GTEX_LINK_CACHE__SIZE", ("cache", "size"), "2000", 2000),
        ("GTEX_LINK_CACHE__TTL", ("cache", "ttl"), "7200", 7200),
        ("GTEX_LINK_API__TIMEOUT", ("api", "timeout"), "99", 99),
        (
            "GTEX_LINK_API__RATE_LIMIT_PER_SECOND",
            ("api", "rate_limit_per_second"),
            "2.5",
            2.5,
        ),
    ],
)
def test_documented_env_names_bind(
    monkeypatch: pytest.MonkeyPatch,
    env_name: str,
    path: tuple[str, ...],
    raw: str,
    expected: object,
) -> None:
    """The names in configuration.md and the Compose overlays reach the settings."""
    monkeypatch.setenv(env_name, raw)
    settings: Any = ServerSettings(_env_file=None)
    for part in path:
        settings = getattr(settings, part)
    assert settings == expected


def test_single_underscore_nested_name_does_not_bind(monkeypatch: pytest.MonkeyPatch) -> None:
    """The trap the docs warn about, pinned so the warning stays true.

    `GTEX_LINK_CACHE_TTL` (one underscore) is NOT a recognised name -- it is
    silently dropped. If a future pydantic-settings makes it bind, this test fails
    and the "double underscore" warning in configuration.md must be revisited.
    """
    monkeypatch.setenv("GTEX_LINK_CACHE_TTL", "7200")
    settings = ServerSettings(_env_file=None)
    assert settings.cache.ttl == 3600, "the single-underscore spelling now binds"


def test_settings_are_isolated_from_a_developer_dotenv() -> None:
    """Sanity: the assertions above measure env, not a stray local .env."""
    assert isinstance(ServerSettings(_env_file=None), BaseSettings)
