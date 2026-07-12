"""F-17: outbound redirect/host validation + fail-closed response byte cap.

The GTEx Portal client keeps httpx's redirect machinery
(``follow_redirects=True``) but validates every hop -- initial request AND each
auto-followed redirect -- against an exact HTTPS host allowlist derived from the
configured base URL, and caps the response body before decoding. GTEx is
GET-only; its only observed 3xx is a trailing-slash 307 -> http downgrade, which
the https-only check correctly rejects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
import pytest

from gtex_link.api import client as client_mod
from gtex_link.api.client import GTExClient
from gtex_link.api.url_guard import (
    DisallowedURLError,
    ResponseTooLargeError,
    build_host_allowlist,
    make_url_guard,
)
from gtex_link.config import GTExAPIConfigModel
from gtex_link.exceptions import GTExAPIError

if TYPE_CHECKING:
    import respx

GTEX_DEFAULT_BASE = "https://gtexportal.org/api/v2"


# --------------------------------------------------------------------------- #
# Unit: the guard helpers in isolation                                        #
# --------------------------------------------------------------------------- #


def test_allowlist_derived_from_config_host() -> None:
    """The allowlist is derived from the configured base URL host, not hardcoded."""
    allowed = build_host_allowlist(GTExAPIConfigModel().base_url)
    assert allowed == frozenset({"gtexportal.org"})


@pytest.mark.asyncio
async def test_guard_rejects_cross_host() -> None:
    guard = make_url_guard(frozenset({"gtexportal.org"}))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("GET", "https://evil.example/api/v2/x"))


@pytest.mark.asyncio
async def test_guard_rejects_http_downgrade() -> None:
    guard = make_url_guard(frozenset({"gtexportal.org"}))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("GET", "http://gtexportal.org/api/v2/x"))


@pytest.mark.asyncio
async def test_guard_rejects_userinfo() -> None:
    guard = make_url_guard(frozenset({"gtexportal.org"}))
    with pytest.raises(DisallowedURLError):
        await guard(httpx.Request("GET", "https://user:pass@gtexportal.org/api/v2/x"))


@pytest.mark.asyncio
async def test_guard_allows_configured_host() -> None:
    guard = make_url_guard(frozenset({"gtexportal.org"}))
    # Must not raise.
    await guard(httpx.Request("GET", "https://gtexportal.org/api/v2/x"))


def test_guard_exceptions_are_not_httpx_retryable() -> None:
    """Guard exceptions must NOT subclass httpx retryable types (non-retryable)."""
    assert not issubclass(DisallowedURLError, httpx.RequestError)
    assert not issubclass(DisallowedURLError, httpx.TimeoutException)
    assert not issubclass(ResponseTooLargeError, httpx.RequestError)
    assert not issubclass(ResponseTooLargeError, httpx.TimeoutException)


# --------------------------------------------------------------------------- #
# Integration: the guard wired through GTExClient._make_request                #
# --------------------------------------------------------------------------- #


@pytest.mark.asyncio
async def test_cross_host_redirect_fails_closed(respx_mock: respx.MockRouter) -> None:
    """A redirect to a non-allowlisted host is caught, mapped, and NOT retried."""
    client = GTExClient(config=GTExAPIConfigModel(max_retries=3), logger=None)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
        302, headers={"Location": "https://evil.example/steal"}
    )

    with pytest.raises(GTExAPIError) as exc_info:
        await client._make_request("GET", "test/endpoint")
    await client.close()

    exc = exc_info.value
    # Mapped through the ladder (not raw DisallowedURLError) and body-free: the
    # disallowed host must not leak into the caller-visible message.
    assert "evil.example" not in str(exc)
    # Non-retryable path -> the "blocked" message, not the retry-exhaustion one.
    assert "blocked" in str(exc).lower()
    assert "after" not in str(exc).lower()


@pytest.mark.asyncio
async def test_http_downgrade_redirect_fails_closed(respx_mock: respx.MockRouter) -> None:
    """The real GTEx trailing-slash 307 -> http downgrade is rejected."""
    client = GTExClient(config=GTExAPIConfigModel(), logger=None)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
        307, headers={"Location": "http://gtexportal.org/api/v2/test/endpoint"}
    )

    with pytest.raises(GTExAPIError) as exc_info:
        await client._make_request("GET", "test/endpoint")
    await client.close()

    assert "blocked" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_userinfo_redirect_fails_closed(respx_mock: respx.MockRouter) -> None:
    """A redirect carrying userinfo is rejected."""
    client = GTExClient(config=GTExAPIConfigModel(), logger=None)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
        302, headers={"Location": "https://user:pass@gtexportal.org/api/v2/x"}
    )

    with pytest.raises(GTExAPIError) as exc_info:
        await client._make_request("GET", "test/endpoint")
    await client.close()

    exc = exc_info.value
    assert "blocked" in str(exc).lower()
    assert "user:pass" not in str(exc)


@pytest.mark.asyncio
async def test_oversized_response_fails_closed(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A body past the byte cap is REFUSED (never truncated) before decode.

    The 16 MB production cap is shrunk to a tiny value so the enforcement path is
    exercised deterministically without allocating a real oversized payload.
    """
    monkeypatch.setattr(client_mod, "MAX_RESPONSE_BYTES", 8)
    client = GTExClient(config=GTExAPIConfigModel(), logger=None)
    # 200 with a well-formed JSON body larger than the (shrunk) cap.
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
        200, json={"data": "x" * 64}, headers={"content-type": "application/json"}
    )

    with pytest.raises(GTExAPIError) as exc_info:
        await client._make_request("GET", "test/endpoint")
    await client.close()

    assert "blocked" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_content_length_fast_path_fails_closed(
    respx_mock: respx.MockRouter, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An oversized declared Content-Length is refused before streaming the body."""
    monkeypatch.setattr(client_mod, "MAX_RESPONSE_BYTES", 8)
    client = GTExClient(config=GTExAPIConfigModel(), logger=None)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(
        200,
        content=b'{"data": 1}',
        headers={"content-type": "application/json", "content-length": "9999"},
    )

    with pytest.raises(GTExAPIError):
        await client._make_request("GET", "test/endpoint")
    await client.close()


@pytest.mark.asyncio
async def test_default_cap_is_16_mib() -> None:
    """The production cap is 16 MB -- never 2 MB (a real 1.73 MB payload exists)."""
    assert client_mod.MAX_RESPONSE_BYTES == 16 * 1024 * 1024


@pytest.mark.asyncio
async def test_happy_path_200_unchanged(respx_mock: respx.MockRouter) -> None:
    """A normal same-host HTTPS 200 is unaffected by the guard/cap."""
    client = GTExClient(config=GTExAPIConfigModel(), logger=None)
    payload = {"data": [{"gene": "TP53"}], "paging_info": {"numberOfPages": 1}}
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(200, json=payload)

    result = await client._make_request("GET", "test/endpoint")
    await client.close()

    assert result == payload


@pytest.mark.asyncio
async def test_non_dict_json_wrapped(respx_mock: respx.MockRouter) -> None:
    """A top-level JSON array is still wrapped as {"data": [...]} after the cap read."""
    client = GTExClient(config=GTExAPIConfigModel(), logger=None)
    respx_mock.get(f"{GTEX_DEFAULT_BASE}/test/endpoint").respond(200, json=[1, 2, 3])

    result = await client._make_request("GET", "test/endpoint")
    await client.close()

    assert result == {"data": [1, 2, 3]}
