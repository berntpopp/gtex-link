"""Outbound URL policy guard for the GTEx Portal client (F-17).

The client keeps httpx's redirect machinery (``follow_redirects=True``) but
validates every outgoing hop -- the initial request AND each auto-followed
redirect -- against an exact normalized origin allowlist derived from the
configured base URL. Keeping httpx's redirect handling and only *validating* each hop is safer
and simpler than disabling redirects and re-implementing the manual loop.

The GTEx Portal is GET-only and same-host HTTPS; its only observed 3xx is a
trailing-slash ``307 -> http`` downgrade, which the https-only check correctly
rejects. The allowlist is derived from configuration (never hardcoded) because
the base URL is operator-overridable.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx

RequestHook = Callable[[httpx.Request], Awaitable[None]]


class DisallowedURLError(Exception):
    """An outbound request/redirect targeted a non-allowlisted URL.

    NON-RETRYABLE: deliberately does not subclass ``httpx.RequestError`` /
    ``httpx.TimeoutException`` so the client's transport-retry branch never
    swallows and re-attempts a policy violation.

    HOST-FREE MESSAGE: the caller/attacker-controlled offending value (redirect
    host or scheme) is NEVER interpolated into the exception ``message`` -- a
    host in the message reaches the logs via chained-exception rendering
    (``raise ... from e`` + ``logger.exception``) or any ``str(exc)`` surface.
    No attacker-controlled destination detail is retained on the exception.
    """

    def __init__(self, *_: object, **__: object) -> None:
        super().__init__("outbound URL rejected")


class ResponseTooLargeError(Exception):
    """A response body exceeded the fail-closed byte cap. NON-RETRYABLE.

    A truncated JSON body is unparseable, so the cap REFUSES an oversized body
    rather than silently truncating it.
    """

    def __init__(self, *_: object, **__: object) -> None:
        super().__init__("outbound response rejected")


@dataclass(frozen=True)
class AllowedOrigin:
    """Normalized HTTPS origin that an outbound request may target."""

    host: str
    port: int


def build_allowed_origins(*base_urls: str) -> frozenset[AllowedOrigin]:
    """Derive exact normalized origins from configured base URL(s).

    Hosts are never hardcoded: every backend base URL is operator-overridable.
    """
    origins: set[AllowedOrigin] = set()
    for url in base_urls:
        parsed = urlsplit(url)
        host = parsed.hostname
        if host:
            origins.add(AllowedOrigin(host.lower(), parsed.port or 443))
    return frozenset(origins)


def build_host_allowlist(*base_urls: str) -> frozenset[str]:
    """Compatibility helper for callers that only need configured host names."""
    return frozenset(origin.host for origin in build_allowed_origins(*base_urls))


def make_url_guard(allowed_origins: frozenset[AllowedOrigin] | frozenset[str]) -> RequestHook:
    """Build an httpx ``request`` event-hook enforcing scheme/userinfo/origin policy.

    Fires on every hop (including auto-followed redirects). Raises
    :class:`DisallowedURLError` on any violation; the client maps that into its
    error ladder as a fixed, non-retryable failure.
    """

    normalized_origins = frozenset(
        AllowedOrigin(origin, 443) if isinstance(origin, str) else origin
        for origin in allowed_origins
    )

    async def _guard(request: httpx.Request) -> None:
        url = request.url
        if url.scheme != "https":
            raise DisallowedURLError()
        # ``url.userinfo`` is the raw bytes (``b''`` when absent), so this also
        # rejects the empty ``:@`` form (username==password=="" but userinfo==b':')
        # that a ``username or password`` check would miss. Subsumes both.
        authority = str(url).split("://", 1)[-1].split("/", 1)[0]
        if url.userinfo or "@" in authority:
            raise DisallowedURLError()
        host = (url.host or "").lower()
        origin = AllowedOrigin(host, url.port or 443)
        if origin not in normalized_origins:
            raise DisallowedURLError()

    return _guard
