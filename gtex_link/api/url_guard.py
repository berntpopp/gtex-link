"""Outbound URL policy guard for the GTEx Portal client (F-17).

The client keeps httpx's redirect machinery (``follow_redirects=True``) but
validates every outgoing hop -- the initial request AND each auto-followed
redirect -- against an exact host allowlist derived from the configured base
URL. Keeping httpx's redirect handling and only *validating* each hop is safer
and simpler than disabling redirects and re-implementing the manual loop.

The GTEx Portal is GET-only and same-host HTTPS; its only observed 3xx is a
trailing-slash ``307 -> http`` downgrade, which the https-only check correctly
rejects. The allowlist is derived from configuration (never hardcoded) because
the base URL is operator-overridable.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from urllib.parse import urlsplit

import httpx

RequestHook = Callable[[httpx.Request], Awaitable[None]]


class DisallowedURLError(Exception):
    """An outbound request/redirect targeted a non-allowlisted URL.

    NON-RETRYABLE: deliberately does not subclass ``httpx.RequestError`` /
    ``httpx.TimeoutException`` so the client's transport-retry branch never
    swallows and re-attempts a policy violation.
    """


class ResponseTooLargeError(Exception):
    """A response body exceeded the fail-closed byte cap. NON-RETRYABLE.

    A truncated JSON body is unparseable, so the cap REFUSES an oversized body
    rather than silently truncating it.
    """


def build_host_allowlist(*base_urls: str) -> frozenset[str]:
    """Derive an exact host allowlist from the configured base URL(s).

    Hosts are never hardcoded: every backend base URL is operator-overridable.
    """
    hosts: set[str] = set()
    for url in base_urls:
        host = urlsplit(url).hostname
        if host:
            hosts.add(host.lower())
    return frozenset(hosts)


def make_url_guard(allowed_hosts: frozenset[str]) -> RequestHook:
    """Build an httpx ``request`` event-hook enforcing scheme/userinfo/host policy.

    Fires on every hop (including auto-followed redirects). Raises
    :class:`DisallowedURLError` on any violation; the client maps that into its
    error ladder as a fixed, non-retryable failure.
    """

    async def _guard(request: httpx.Request) -> None:
        url = request.url
        if url.scheme != "https":
            raise DisallowedURLError(f"non-https scheme: {url.scheme}")
        if url.username or url.password:
            raise DisallowedURLError("userinfo is not permitted in request URLs")
        host = (url.host or "").lower()
        if host not in allowed_hosts:
            raise DisallowedURLError(f"host not allowlisted: {host}")

    return _guard
