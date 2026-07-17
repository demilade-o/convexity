"""Yahoo Finance via yfinance: an optional research-only price adapter.

This adapter exists so a researcher can pull a quick price history in a notebook.
It is not a foundation of the library and must never be treated as one.

yfinance's own documentation states that it is not affiliated with, endorsed by,
or vetted by Yahoo, and that Yahoo Finance data is intended for personal use.
Accordingly, in this package:

- it lives behind the ``convexity[yahoo]`` extra and is imported only on demand;
- the analytics core never imports it, enforced by the import contracts;
- no Yahoo data is ever cached to disk here, shipped, or redistributed;
- every response is labelled research/personal-use in its provenance;
- it is replaceable through the :class:`~convexity.data.protocols.PriceHistoryProvider`
  protocol like any other provider.

If your use is commercial, or you need a reliability guarantee, this adapter is
not for you.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Protocol

import pandas as pd

from convexity.data.cache import CacheState
from convexity.data.models import DataEnvelope, Provenance
from convexity.exceptions import ProviderResponseError, ProviderUnavailableError

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["YahooFinanceProvider"]

_OHLCV = {
    "Open": "open",
    "High": "high",
    "Low": "low",
    "Close": "close",
    "Volume": "volume",
}


class _Ticker(Protocol):
    """The slice of yfinance's ``Ticker`` this adapter depends on."""

    def history(self, **kwargs: object) -> pd.DataFrame: ...


def _utc_now() -> datetime:
    return datetime.now(UTC)


def _default_ticker_factory(symbol: str) -> _Ticker:
    try:
        import yfinance
    except ImportError as exc:
        msg = (
            "yfinance is not installed. Install the optional research extra with "
            "`pip install convexity[yahoo]`. Note it is research/personal-use only."
        )
        raise ProviderUnavailableError(msg) from exc
    ticker: _Ticker = yfinance.Ticker(symbol)
    return ticker


class YahooFinanceProvider:
    """Price histories from Yahoo Finance, for research and personal use only.

    Parameters
    ----------
    ticker_factory
        Callable mapping a symbol to an object with a ``history(**kwargs)``
        method. Injected so tests never touch the network and so the real
        yfinance import stays lazy. Defaults to constructing ``yfinance.Ticker``.
    clock
        UTC clock, injected for deterministic provenance timestamps.

    Notes
    -----
    Satisfies :class:`~convexity.data.protocols.PriceHistoryProvider`.
    """

    TERMS_URL = "https://ranaroussi.github.io/yfinance/"

    # Provider metadata, constant for this provider. These class attributes
    # satisfy the read-only properties of the Provider protocol structurally.
    name = "yahoo_finance"
    terms_url = TERMS_URL
    attribution = (
        "Data via yfinance, which is not affiliated with, endorsed by, or "
        "vetted by Yahoo. Yahoo Finance data is intended for personal use."
    )
    requires_auth = False
    research_only = True

    def __init__(
        self,
        *,
        ticker_factory: Callable[[str], _Ticker] = _default_ticker_factory,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._ticker_factory = ticker_factory
        self._clock = clock

    # -- capability --------------------------------------------------------- #

    def fetch_prices(
        self,
        symbol: str,
        *,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        offline: bool = False,
        use_cache: bool = True,
    ) -> DataEnvelope[pd.DataFrame]:
        """Fetch a price history for ``symbol`` wrapped in provenance.

        Parameters
        ----------
        symbol
            The ticker symbol to fetch.
        start, end
            Optional inclusive date bounds.
        offline
            Not supported by this adapter: it holds no local cache, so an offline
            call cannot be served and raises. This is deliberate -- the research
            adapter makes no availability guarantee.
        use_cache
            Ignored; retained for protocol conformance.

        Returns
        -------
        DataEnvelope[pandas.DataFrame]
            Normalised OHLCV columns and provenance labelled research-only.

        Raises
        ------
        ProviderUnavailableError
            If ``offline`` is set, or if yfinance is not installed.
        ProviderResponseError
            If the response is empty or has no recognisable OHLCV columns.
        """
        if offline:
            msg = (
                "the Yahoo research adapter has no local cache and cannot serve "
                "offline requests. Use an official provider for reproducible work."
            )
            raise ProviderUnavailableError(msg)

        ticker = self._ticker_factory(symbol)
        raw = ticker.history(start=start, end=end, auto_adjust=True)
        frame, mapping = self._normalise(raw, symbol)

        provenance = Provenance(
            provider=self.name,
            dataset=symbol,
            retrieved_at=pd.Timestamp(self._clock()),
            source_url=f"{self.TERMS_URL}#{symbol}",
            terms_url=self.TERMS_URL,
            attribution=self.attribution,
            units="price (auto-adjusted) and share volume",
            cache_state=CacheState.BYPASS,
            currency=None,
            frequency="daily",
            request_params={"symbol": symbol},
            field_mapping=mapping,
            warnings=(
                "Research/personal-use only. Not affiliated with Yahoo. No claim "
                "is made about availability, completeness, or production suitability.",
            ),
            research_only=True,
        )
        return DataEnvelope(frame, provenance)

    @staticmethod
    def _normalise(
        raw: pd.DataFrame, symbol: str
    ) -> tuple[pd.DataFrame, dict[str, str]]:
        if raw is None or raw.empty:
            msg = (
                f"Yahoo returned no data for {symbol!r}. The symbol may be wrong, "
                f"delisted, or outside the requested date range."
            )
            raise ProviderResponseError(msg)
        present = {src: dst for src, dst in _OHLCV.items() if src in raw.columns}
        if not present:
            msg = (
                f"Yahoo response for {symbol!r} had no recognisable OHLCV columns "
                f"(got {list(raw.columns)})."
            )
            raise ProviderResponseError(msg)
        frame = raw.loc[:, list(present)].rename(columns=present).astype(float)
        return frame, present
