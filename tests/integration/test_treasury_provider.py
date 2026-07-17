"""The Treasury provider end to end, with the network mocked.

respx intercepts the HTTP call, so no socket opens (the suite also runs under
``--disable-socket``). The fixtures mimic the documented Fiscal Data response
shape; none is a captured response. A movable clock drives cache-age arithmetic.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import numpy as np
import pandas as pd
import pytest
import respx

import convexity as cx
from convexity.conventions import Compounding, DayCount
from convexity.data._transport import RetryingTransport
from convexity.data.cache import CacheState, FileCache
from convexity.data.providers.treasury import TreasuryFiscalDataProvider
from convexity.exceptions import ProviderResponseError, ProviderUnavailableError
from convexity.rates import RateInstrument, RiskFreeSeries

ENDPOINT = (
    "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    "/v2/accounting/od/avg_interest_rates"
)

_RESPONSE = {
    "data": [
        {
            "record_date": "2024-01-31",
            "security_desc": "Treasury Bills",
            "avg_interest_rate_amt": "5.123",
        },
        {
            "record_date": "2024-02-29",
            "security_desc": "Treasury Bills",
            "avg_interest_rate_amt": "5.098",
        },
    ],
    "meta": {"count": 2},
    "links": {"self": "&page%5Bnumber%5D=1"},
}


class _Clock:
    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock() -> _Clock:
    return _Clock(datetime(2024, 3, 1, tzinfo=UTC))


def _provider(clock: _Clock, cache: FileCache | None) -> TreasuryFiscalDataProvider:
    return TreasuryFiscalDataProvider(
        RetryingTransport(httpx.Client(), sleep=lambda _s: None),
        cache=cache,
        clock=clock,
    )


@respx.mock
def test_fetch_parses_percent_to_decimal(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    envelope = provider.fetch_risk_free()

    series = envelope.data
    assert isinstance(series, RiskFreeSeries)
    # 5.123% -> 0.05123, 5.098% -> 0.05098.
    assert series.rates.round(5).tolist() == [0.05123, 0.05098]
    assert series.currency == "USD"
    assert series.instrument is RateInstrument.TREASURY_BILL
    assert series.compounding is Compounding.SIMPLE
    assert series.day_count is DayCount.ACT_365F


@respx.mock
def test_provenance_is_complete(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    prov = provider.fetch_risk_free().provenance

    assert prov.provider == "us_treasury_fiscal_data"
    assert prov.dataset == "avg_interest_rates"
    assert prov.currency == "USD"
    assert prov.units == "decimal annual rate"
    assert prov.cache_state is CacheState.MISS
    assert prov.terms_url.startswith("https://")
    assert "Fiscal Data" in prov.attribution
    assert prov.research_only is False
    # The "average on outstanding stock" caveat must be surfaced, not buried.
    assert any("outstanding" in w for w in prov.warnings)
    assert prov.request_params["sort"] == "record_date"


@respx.mock
def test_second_call_is_a_cache_hit_with_age(clock: _Clock, tmp_path: Path) -> None:
    route = respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    cache = FileCache(tmp_path, clock=clock)
    provider = _provider(clock, cache)

    first = provider.fetch_risk_free()
    assert first.provenance.cache_state is CacheState.MISS
    clock.advance(hours=3)
    second = provider.fetch_risk_free()

    assert second.provenance.cache_state is CacheState.HIT
    age = second.provenance.cache_age
    assert age is not None
    assert age.total_seconds() == 3 * 3600
    assert route.call_count == 1  # the network was hit once, not twice


@respx.mock
def test_use_cache_false_bypasses_cache(clock: _Clock, tmp_path: Path) -> None:
    route = respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    envelope = provider.fetch_risk_free(use_cache=False)
    assert envelope.provenance.cache_state is CacheState.BYPASS
    provider.fetch_risk_free(use_cache=False)
    assert route.call_count == 2  # never consulted the cache


@respx.mock
def test_offline_without_cache_raises(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    with pytest.raises(ProviderUnavailableError, match="offline"):
        provider.fetch_risk_free(offline=True)


@respx.mock
def test_offline_served_from_cache(clock: _Clock, tmp_path: Path) -> None:
    route = respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    cache = FileCache(tmp_path, clock=clock)
    provider = _provider(clock, cache)

    provider.fetch_risk_free()  # populate the cache online
    clock.advance(days=1)
    offline = provider.fetch_risk_free(offline=True)

    assert offline.provenance.cache_state is CacheState.OFFLINE
    assert offline.provenance.cache_age == pd.Timedelta(days=1)
    assert route.call_count == 1  # offline never called the network


@respx.mock
def test_provider_with_no_cache_bypasses(clock: _Clock) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, cache=None)
    envelope = provider.fetch_risk_free()
    assert envelope.provenance.cache_state is CacheState.BYPASS


@respx.mock
def test_no_cache_offline_raises(clock: _Clock) -> None:
    provider = _provider(clock, cache=None)
    with pytest.raises(ProviderUnavailableError):
        provider.fetch_risk_free(offline=True)


@respx.mock
def test_date_bounds_reach_the_query(clock: _Clock, tmp_path: Path) -> None:
    route = respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    provider.fetch_risk_free(
        start=pd.Timestamp("2024-01-01"), end=pd.Timestamp("2024-02-29")
    )
    sent = str(route.calls[0].request.url)
    assert "record_date%3Agte%3A2024-01-01" in sent
    assert "record_date%3Alte%3A2024-02-29" in sent


@respx.mock
def test_malformed_json_raises_response_error(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, content=b"not json")
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    with pytest.raises(ProviderResponseError, match="schema"):
        provider.fetch_risk_free()


@respx.mock
def test_empty_data_raises_response_error(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    with pytest.raises(ProviderResponseError, match="no rows"):
        provider.fetch_risk_free()


@respx.mock
def test_row_missing_field_raises_response_error(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json={"data": [{"record_date": "2024-01-31"}]})
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    with pytest.raises(ProviderResponseError, match="row shape"):
        provider.fetch_risk_free()


@respx.mock
def test_non_200_raises_response_error(clock: _Clock, tmp_path: Path) -> None:
    respx.get(url__startswith=ENDPOINT).mock(return_value=httpx.Response(404))
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    with pytest.raises(ProviderResponseError, match="404"):
        provider.fetch_risk_free()


@respx.mock
def test_default_clock_is_utc(tmp_path: Path) -> None:
    # Exercises the module default clock (no injection).
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = TreasuryFiscalDataProvider(
        RetryingTransport(httpx.Client(), sleep=lambda _s: None),
        cache=FileCache(tmp_path),
    )
    prov = provider.fetch_risk_free().provenance
    assert prov.retrieved_at.tz is not None


@respx.mock
def test_output_feeds_a_ratio(clock: _Clock, tmp_path: Path) -> None:
    """The whole point: a fetched series aligns into a Sharpe ratio safely."""
    respx.get(url__startswith=ENDPOINT).mock(
        return_value=httpx.Response(200, json=_RESPONSE)
    )
    provider = _provider(clock, FileCache(tmp_path, clock=clock))
    rf = provider.fetch_risk_free().data

    idx = pd.date_range("2024-03-31", periods=12, freq="ME")
    returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 3, index=idx)
    rf_periodic = rf.to_period_returns(idx, 12)  # backward as-of, no look-ahead
    result = cx.sharpe_ratio(returns, risk_free=rf_periodic, periods_per_year=12)
    assert np.isfinite(result)
