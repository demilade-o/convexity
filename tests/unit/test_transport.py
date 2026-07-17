"""The retrying transport: retry only what is worth retrying, and bound it.

Retries are mocked with respx and the sleep is injected, so these tests assert
the *policy* -- which failures retry, how many times, and whether Retry-After is
honoured -- without waiting or touching the network. The whole suite runs under
``--disable-socket``, so a real call would fail loudly.
"""

from __future__ import annotations

import httpx
import pytest
import respx

from convexity.data._transport import RetryingTransport
from convexity.exceptions import (
    ProviderResponseError,
    ProviderUnavailableError,
    RateLimitError,
)

URL = "https://api.example.test/data"


class _RecordingSleep:
    """Captures sleep durations instead of waiting."""

    def __init__(self) -> None:
        self.calls: list[float] = []

    def __call__(self, seconds: float) -> None:
        self.calls.append(seconds)


def _transport(sleep: _RecordingSleep, **kwargs: object) -> RetryingTransport:
    import random

    return RetryingTransport(
        httpx.Client(),
        sleep=sleep,
        rng=random.Random(0),  # deterministic jitter
        **kwargs,  # type: ignore[arg-type]
    )


@respx.mock
def test_success_returns_immediately() -> None:
    respx.get(URL).mock(return_value=httpx.Response(200, json={"ok": True}))
    sleep = _RecordingSleep()
    response = _transport(sleep).get(URL)
    assert response.status_code == 200
    assert sleep.calls == []  # no retries, no waiting


@respx.mock
def test_non_retryable_4xx_returned_without_retry() -> None:
    respx.get(URL).mock(return_value=httpx.Response(404))
    sleep = _RecordingSleep()
    response = _transport(sleep).get(URL)
    assert response.status_code == 404
    assert sleep.calls == []


@respx.mock
def test_retries_on_500_then_succeeds() -> None:
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(500),
        httpx.Response(500),
        httpx.Response(200, json={"ok": True}),
    ]
    sleep = _RecordingSleep()
    response = _transport(sleep).get(URL)
    assert response.status_code == 200
    assert len(sleep.calls) == 2  # two backoffs before the success


@respx.mock
def test_exhausted_5xx_raises_response_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(503))
    sleep = _RecordingSleep()
    with pytest.raises(ProviderResponseError, match="503"):
        _transport(sleep, max_retries=2).get(URL)
    assert len(sleep.calls) == 2  # max_retries backoffs, then give up


@respx.mock
def test_exhausted_429_raises_rate_limit_error() -> None:
    respx.get(URL).mock(return_value=httpx.Response(429))
    sleep = _RecordingSleep()
    with pytest.raises(RateLimitError):
        _transport(sleep, max_retries=1).get(URL)


@respx.mock
def test_retry_after_header_is_honoured() -> None:
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "2"}),
        httpx.Response(200, json={"ok": True}),
    ]
    sleep = _RecordingSleep()
    response = _transport(sleep).get(URL)
    assert response.status_code == 200
    assert sleep.calls == [2.0]  # exact server-advised wait, not jittered backoff


@respx.mock
def test_unparseable_retry_after_falls_back_to_backoff() -> None:
    route = respx.get(URL)
    route.side_effect = [
        httpx.Response(429, headers={"Retry-After": "Wed, 21 Oct 2025 07:28:00 GMT"}),
        httpx.Response(200),
    ]
    sleep = _RecordingSleep()
    _transport(sleep, backoff_factor=1.0).get(URL)
    # Fell back to jittered backoff in [0, 1], not the unparseable date.
    assert len(sleep.calls) == 1
    assert 0.0 <= sleep.calls[0] <= 1.0


@respx.mock
def test_rate_limit_error_carries_retry_after() -> None:
    respx.get(URL).mock(return_value=httpx.Response(429, headers={"Retry-After": "5"}))
    sleep = _RecordingSleep()
    with pytest.raises(RateLimitError) as exc_info:
        _transport(sleep, max_retries=0).get(URL)
    assert exc_info.value.retry_after == 5.0


@respx.mock
def test_connection_error_retried_then_raises_unavailable() -> None:
    respx.get(URL).mock(side_effect=httpx.ConnectError("boom"))
    sleep = _RecordingSleep()
    with pytest.raises(ProviderUnavailableError, match="unreachable"):
        _transport(sleep, max_retries=2).get(URL)
    assert len(sleep.calls) == 2


@respx.mock
def test_backoff_grows_and_is_bounded_by_ceiling() -> None:
    respx.get(URL).mock(return_value=httpx.Response(500))
    sleep = _RecordingSleep()
    with pytest.raises(ProviderResponseError):
        _transport(sleep, max_retries=3, backoff_factor=1.0).get(URL)
    # Full jitter: attempt k waits within [0, 1*2**k].
    assert len(sleep.calls) == 3
    for k, waited in enumerate(sleep.calls):
        assert 0.0 <= waited <= 2**k
