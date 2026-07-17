"""A retrying HTTP transport with bounded backoff, isolated from provider logic.

This is the only place in the library, besides the concrete providers, that
imports :mod:`httpx`. It is imported lazily by providers, never by the analytics
core, so ``import convexity`` performs no network setup and needs no HTTP client.

The retry policy is deliberately narrow: only idempotent GETs, only genuinely
transient failures (connection/timeout errors, ``429``, and ``5xx``), a bounded
number of attempts, exponential backoff with full jitter, and respect for a
server's ``Retry-After``. A ``4xx`` other than ``429`` is a client error and is
returned immediately rather than retried, because retrying it would only repeat
the same mistake.

The clock (``sleep``) and the jitter source (``rng``) are injected so tests are
deterministic and never actually wait.
"""

from __future__ import annotations

import random
import time
from typing import TYPE_CHECKING

import httpx

from convexity.exceptions import (
    ProviderResponseError,
    ProviderUnavailableError,
    RateLimitError,
)

if TYPE_CHECKING:
    from collections.abc import Callable, Mapping

__all__ = ["RetryingTransport"]

#: Status codes worth retrying: rate limiting and transient server errors.
_RETRYABLE_STATUS = frozenset({429, 500, 502, 503, 504})


class RetryingTransport:
    """Wrap an :class:`httpx.Client` with bounded, jittered retries.

    Parameters
    ----------
    client
        The HTTP client to send requests through. Injected so connection reuse,
        base URLs, and (in tests) mock transports are the caller's choice.
    max_retries
        Maximum number of retries after the first attempt. Three means up to four
        requests in total.
    backoff_factor
        Base delay in seconds; attempt ``k`` waits up to
        ``backoff_factor * 2**k`` seconds before jitter.
    timeout
        Per-request timeout in seconds.
    sleep
        Callable used to wait between attempts. Injected; defaults to
        :func:`time.sleep`.
    rng
        Random source for jitter. Injected; defaults to a module-level generator.
    """

    def __init__(
        self,
        client: httpx.Client,
        *,
        max_retries: int = 3,
        backoff_factor: float = 0.5,
        timeout: float = 10.0,
        sleep: Callable[[float], None] = time.sleep,
        rng: random.Random | None = None,
    ) -> None:
        self._client = client
        self._max_retries = max_retries
        self._backoff_factor = backoff_factor
        self._timeout = timeout
        self._sleep = sleep
        # Jitter, not cryptography: the standard PRNG is exactly right here.
        self._rng = rng or random.Random()  # noqa: S311

    def get(
        self,
        url: str,
        *,
        params: Mapping[str, str] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> httpx.Response:
        """Send a GET, retrying transient failures.

        Parameters
        ----------
        url
            The URL to request.
        params
            Query parameters.
        headers
            Request headers.

        Returns
        -------
        httpx.Response
            A successful or non-retryable response.

        Raises
        ------
        ProviderUnavailableError
            If every attempt failed with a connection or timeout error.
        RateLimitError
            If the server kept returning ``429`` until retries were exhausted.
        ProviderResponseError
            If the server kept returning a ``5xx`` until retries were exhausted.
        """
        last_response: httpx.Response | None = None
        # The loop always exits via return, raise, or break; it never falls
        # through, so there is no natural-completion branch to cover.
        for attempt in range(self._max_retries + 1):  # pragma: no branch
            try:
                response = self._client.get(
                    url, params=params, headers=headers, timeout=self._timeout
                )
            except (httpx.TimeoutException, httpx.TransportError) as exc:
                if attempt == self._max_retries:
                    msg = (
                        f"GET {url} failed after {attempt + 1} attempt(s): {exc}. "
                        f"The provider may be unreachable; try offline mode if a "
                        f"cached copy exists."
                    )
                    raise ProviderUnavailableError(msg) from exc
                self._wait(attempt, retry_after=None)
                continue

            if response.status_code not in _RETRYABLE_STATUS:
                return response

            last_response = response
            if attempt == self._max_retries:
                break
            self._wait(attempt, retry_after=self._retry_after(response))

        # Retries exhausted on a retryable status.
        assert last_response is not None  # noqa: S101 - loop guarantees this
        if last_response.status_code == 429:
            msg = (
                f"GET {url} was rate limited ({last_response.status_code}) after "
                f"{self._max_retries + 1} attempt(s). Back off and retry later."
            )
            raise RateLimitError(msg, retry_after=self._retry_after(last_response))
        msg = (
            f"GET {url} returned {last_response.status_code} after "
            f"{self._max_retries + 1} attempt(s). The provider is failing; try "
            f"again later or use a cached copy."
        )
        raise ProviderResponseError(msg)

    def _wait(self, attempt: int, *, retry_after: float | None) -> None:
        """Sleep before the next attempt, honouring Retry-After when present."""
        if retry_after is not None:
            self._sleep(retry_after)
            return
        ceiling = self._backoff_factor * (2**attempt)
        # Full jitter: a uniform draw in [0, ceiling] avoids synchronised retries.
        self._sleep(self._rng.uniform(0.0, ceiling))

    @staticmethod
    def _retry_after(response: httpx.Response) -> float | None:
        """Parse an integer-seconds Retry-After header, or return None."""
        raw = response.headers.get("Retry-After")
        if raw is None:
            return None
        try:
            return float(raw)
        except ValueError:
            # An HTTP-date form is valid but rare for these providers; fall back
            # to jittered backoff rather than misparsing it.
            return None
