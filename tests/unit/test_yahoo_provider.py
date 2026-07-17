"""The Yahoo research adapter: labelled, injectable, and never a hard dependency.

yfinance is not installed in the test environment (it is only in the optional
``yahoo`` extra), so the default code path genuinely raises a helpful error. The
happy path injects a fake ticker, so no network and no yfinance are involved.
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime

import pandas as pd
import pytest

from convexity.data.cache import CacheState
from convexity.data.providers.yahoo import YahooFinanceProvider
from convexity.exceptions import ProviderResponseError, ProviderUnavailableError


class _FakeTicker:
    def __init__(self, frame: pd.DataFrame) -> None:
        self._frame = frame

    def history(self, **kwargs: object) -> pd.DataFrame:
        return self._frame


def _yahoo_frame() -> pd.DataFrame:
    idx = pd.date_range("2024-01-02", periods=3, freq="D")
    return pd.DataFrame(
        {
            "Open": [100.0, 101.0, 102.0],
            "High": [103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [102.0, 103.0, 104.0],
            "Volume": [1_000, 1_100, 1_200],
            "Dividends": [0.0, 0.0, 0.0],  # extra columns should be dropped
        },
        index=idx,
    )


def _clock() -> datetime:
    return datetime(2024, 6, 1, tzinfo=UTC)


def _provider(frame: pd.DataFrame) -> YahooFinanceProvider:
    return YahooFinanceProvider(
        ticker_factory=lambda _s: _FakeTicker(frame), clock=_clock
    )


class TestNormalisation:
    def test_returns_normalised_ohlcv(self) -> None:
        envelope = _provider(_yahoo_frame()).fetch_prices("AAPL")
        frame = envelope.data
        assert list(frame.columns) == ["open", "high", "low", "close", "volume"]
        assert frame["close"].tolist() == [102.0, 103.0, 104.0]
        assert frame.dtypes.eq("float64").all()

    def test_provenance_is_research_only(self) -> None:
        prov = _provider(_yahoo_frame()).fetch_prices("AAPL").provenance
        assert prov.provider == "yahoo_finance"
        assert prov.research_only is True
        assert prov.cache_state is CacheState.BYPASS
        assert "personal use" in prov.attribution.lower()
        assert any("research" in w.lower() for w in prov.warnings)
        assert prov.field_mapping["Close"] == "close"


class TestFailureModes:
    def test_empty_frame_raises(self) -> None:
        provider = _provider(pd.DataFrame())
        with pytest.raises(ProviderResponseError, match="no data"):
            provider.fetch_prices("AAPL")

    def test_no_ohlcv_columns_raises(self) -> None:
        junk = pd.DataFrame(
            {"Nonsense": [1.0]}, index=pd.date_range("2024-01-01", periods=1)
        )
        provider = _provider(junk)
        with pytest.raises(ProviderResponseError, match="OHLCV"):
            provider.fetch_prices("AAPL")

    def test_offline_is_unsupported(self) -> None:
        provider = _provider(_yahoo_frame())
        with pytest.raises(ProviderUnavailableError, match="offline"):
            provider.fetch_prices("AAPL", offline=True)

    def test_missing_yfinance_raises_helpful_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Force the import to fail regardless of whether yfinance happens to be
        # installed, so the default factory's error path is exercised.
        monkeypatch.setitem(sys.modules, "yfinance", None)
        provider = YahooFinanceProvider()
        with pytest.raises(ProviderUnavailableError, match="convexity\\[yahoo\\]"):
            provider.fetch_prices("AAPL")


class TestDefaults:
    def test_default_clock_is_utc(self) -> None:
        # Exercises the module default clock without injection.
        envelope = YahooFinanceProvider(
            ticker_factory=lambda _s: _FakeTicker(_yahoo_frame())
        ).fetch_prices("AAPL")
        assert envelope.provenance.retrieved_at.tz is not None

    def test_default_factory_builds_a_ticker_when_present(self) -> None:
        yfinance = pytest.importorskip("yfinance")
        from convexity.data.providers.yahoo import _default_ticker_factory

        ticker = _default_ticker_factory("AAPL")
        assert isinstance(ticker, yfinance.Ticker)
