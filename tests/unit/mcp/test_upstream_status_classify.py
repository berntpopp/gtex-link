"""An upstream 4xx is the caller's input, not an outage (issue #165).

`_classify` must branch on the HTTP status a `GTExAPIError` carries: 400/422 ->
non-retryable `invalid_input`, 404 -> `not_found`, any other 4xx a non-retryable
`upstream_unavailable`;
status-less transport failures and 5xx stay retryable `upstream_unavailable`.
"""

from __future__ import annotations

import pytest

from gtex_link.exceptions import GTExAPIError, ServiceUnavailableError
from gtex_link.mcp.envelope import _classify, _recovery_action


@pytest.mark.parametrize(
    ("exc", "code", "retryable"),
    [
        (GTExAPIError("x", status_code=422), "invalid_input", False),
        (GTExAPIError("x", status_code=400), "invalid_input", False),
        (GTExAPIError("x", status_code=404), "not_found", False),
        (GTExAPIError("x", status_code=403), "upstream_unavailable", False),
        (GTExAPIError("Failed to connect"), "upstream_unavailable", True),
        # Invalid JSON on a 200 is an upstream fault, not the caller's input.
        (GTExAPIError("bad json", status_code=200), "upstream_unavailable", True),
        (ServiceUnavailableError("HTTP 503"), "upstream_unavailable", True),
    ],
)
def test_classify_branches_on_upstream_status(
    exc: GTExAPIError, code: str, retryable: bool
) -> None:
    got_code, message, got_retryable = _classify(exc)
    assert (got_code, got_retryable) == (code, retryable)
    # Never "upstream error" and "verify inputs" in one breath.
    assert not ("Verify" in message and code == "upstream_unavailable")


def test_422_recovery_is_reformulate_input() -> None:
    code, _, retryable = _classify(GTExAPIError("x", status_code=422))
    assert _recovery_action(code, retryable) == "reformulate_input"
