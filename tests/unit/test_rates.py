"""Risk-free-rate models: conventions, alignment, curves, and policy.

Every numeric assertion is a hand derivation, not a recorded output: a flat rate
converts to a known period return, a flat continuous curve discounts as
``exp(-rt)``, and a forward on a flat curve equals the zero rate. Alignment is
tested for the one property that matters most -- that a rate never informs an
earlier date.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import convexity as cx
from convexity.conventions import Compounding, DayCount
from convexity.exceptions import (
    ConventionError,
    CurrencyMismatchError,
    DataQualityError,
    StaleDataError,
    ValidationError,
)
from convexity.rates import (
    InterpolationMethod,
    RateInstrument,
    RateQuote,
    RiskFreePolicy,
    RiskFreeSeries,
    ZeroCurve,
)


@pytest.fixture
def monthly_rates() -> RiskFreeSeries:
    """Two monthly USD observations: 5% then 4.5%."""
    idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
    return RiskFreeSeries(pd.Series([0.05, 0.045], index=idx), currency="USD")


class TestCurrencyValidation:
    def test_lowercase_is_normalised(self) -> None:
        assert RateQuote(0.05, pd.Timestamp("2024-01-01"), "usd").currency == "USD"

    def test_whitespace_stripped(self) -> None:
        assert RateQuote(0.05, pd.Timestamp("2024-01-01"), " eur ").currency == "EUR"

    @pytest.mark.parametrize("bad", ["US", "USDX", "US1", "12"])
    def test_invalid_code_raises(self, bad: str) -> None:
        with pytest.raises(ValidationError, match="ISO 4217"):
            RateQuote(0.05, pd.Timestamp("2024-01-01"), bad)


class TestRateQuote:
    def test_non_finite_value_raises(self) -> None:
        with pytest.raises(ValidationError, match="finite"):
            RateQuote(float("nan"), pd.Timestamp("2024-01-01"))

    def test_quote_date_coerced_to_timestamp(self) -> None:
        q = RateQuote(0.05, "2024-01-31")  # type: ignore[arg-type]
        assert q.quote_date == pd.Timestamp("2024-01-31")

    def test_period_return_simple_hand_worked(self) -> None:
        # 12% annual, simple, monthly -> exactly 1% per month.
        q = RateQuote(0.12, pd.Timestamp("2024-01-31"))
        assert q.period_return(12) == pytest.approx(0.01)

    def test_period_return_honours_compounding(self) -> None:
        q = RateQuote(
            0.05, pd.Timestamp("2024-01-31"), compounding=Compounding.COMPOUNDED
        )
        # (1.05)^(1/12) - 1
        assert q.period_return(12) == pytest.approx(1.05 ** (1 / 12) - 1)

    def test_period_return_override_beats_quote_convention(self) -> None:
        q = RateQuote(0.05, pd.Timestamp("2024-01-31"), compounding=Compounding.SIMPLE)
        overridden = q.period_return(12, compounding=Compounding.CONTINUOUS)
        assert overridden == pytest.approx(math.expm1(0.05 / 12))

    def test_staleness_is_signed(self) -> None:
        q = RateQuote(0.05, pd.Timestamp("2024-01-31"))
        assert q.staleness(pd.Timestamp("2024-02-10")) == pd.Timedelta(days=10)
        assert q.staleness(pd.Timestamp("2024-01-20")) == pd.Timedelta(days=-11)

    def test_future_dated_detected(self) -> None:
        q = RateQuote(0.05, pd.Timestamp("2024-02-15"))
        assert q.is_future_dated(pd.Timestamp("2024-02-01"))
        assert not q.is_future_dated(pd.Timestamp("2024-02-15"))

    def test_frozen(self) -> None:
        q = RateQuote(0.05, pd.Timestamp("2024-01-31"))
        with pytest.raises((AttributeError, TypeError)):
            q.value = 0.06  # type: ignore[misc]


class TestRiskFreeSeriesConstruction:
    def test_empty_raises(self) -> None:
        with pytest.raises(ValidationError, match="at least one"):
            RiskFreeSeries(pd.Series([], dtype=float, index=pd.DatetimeIndex([])))

    def test_non_finite_raises(self) -> None:
        idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
        with pytest.raises(DataQualityError, match="non-finite"):
            RiskFreeSeries(pd.Series([0.05, np.inf], index=idx))

    def test_non_datetime_index_raises(self) -> None:
        with pytest.raises(cx.IndexValidationError):
            RiskFreeSeries(pd.Series([0.05, 0.04], index=[0, 1]))

    def test_input_series_not_mutated(self, monthly_rates: RiskFreeSeries) -> None:
        idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
        original = pd.Series([0.05, 0.045], index=idx)
        snapshot = original.copy()
        RiskFreeSeries(original)
        pd.testing.assert_series_equal(original, snapshot)


class TestRiskFreeSeriesAlignment:
    def test_backward_only_no_lookahead(self, monthly_rates: RiskFreeSeries) -> None:
        target = pd.to_datetime(["2024-02-15", "2024-03-15"])
        aligned = monthly_rates.align_to(target)
        # 2024-02-15 must see the January rate, never the (later) February one.
        assert aligned.tolist() == [0.05, 0.045]

    def test_date_before_first_observation_is_nan(
        self, monthly_rates: RiskFreeSeries
    ) -> None:
        target = pd.to_datetime(["2023-12-31", "2024-02-15"])
        aligned = monthly_rates.align_to(target)
        assert math.isnan(aligned.iloc[0])
        assert aligned.iloc[1] == 0.05

    def test_staleness_enforced(self, monthly_rates: RiskFreeSeries) -> None:
        target = pd.to_datetime(["2024-06-30"])  # 4 months after the last obs
        with pytest.raises(StaleDataError, match="staleness"):
            monthly_rates.align_to(target, max_staleness=pd.Timedelta(days=45))

    def test_publication_lag_delays_availability(self) -> None:
        idx = pd.to_datetime(["2024-01-31"])
        series = RiskFreeSeries(pd.Series([0.05], index=idx))
        # With a 5-day lag the value is usable only from 2024-02-05.
        target = pd.to_datetime(["2024-02-03", "2024-02-10"])
        aligned = series.align_to(target, publication_lag=pd.Timedelta(days=5))
        assert math.isnan(aligned.iloc[0])
        assert aligned.iloc[1] == 0.05

    def test_to_period_returns_hand_worked(self) -> None:
        idx = pd.to_datetime(["2024-01-31"])
        series = RiskFreeSeries(pd.Series([0.12], index=idx))  # 12% annual simple
        target = pd.to_datetime(["2024-02-29", "2024-03-31"])
        period = series.to_period_returns(target, 12)
        assert period.round(10).tolist() == [0.01, 0.01]

    def test_latest_returns_a_full_quote(self, monthly_rates: RiskFreeSeries) -> None:
        quote = monthly_rates.latest(pd.Timestamp("2024-02-15"))
        assert isinstance(quote, RateQuote)
        assert quote.value == 0.05
        assert quote.quote_date == pd.Timestamp("2024-01-31")
        assert quote.currency == "USD"

    def test_latest_before_series_start_raises(
        self, monthly_rates: RiskFreeSeries
    ) -> None:
        with pytest.raises(ValidationError, match="on or before"):
            monthly_rates.latest(pd.Timestamp("2023-01-01"))


class TestZeroCurveConstruction:
    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ConventionError, match="equal-length"):
            ZeroCurve([1.0, 2.0], [0.03])

    def test_empty_raises(self) -> None:
        with pytest.raises(ConventionError):
            ZeroCurve([], [])

    def test_non_increasing_tenors_raise(self) -> None:
        with pytest.raises(ConventionError, match="strictly increasing"):
            ZeroCurve([2.0, 1.0], [0.03, 0.04])

    def test_non_positive_first_tenor_raises(self) -> None:
        with pytest.raises(ConventionError, match="strictly increasing"):
            ZeroCurve([0.0, 1.0], [0.03, 0.04])

    def test_non_finite_rate_raises(self) -> None:
        with pytest.raises(DataQualityError):
            ZeroCurve([1.0, 2.0], [0.03, np.nan])


class TestZeroCurveMath:
    def test_discount_factor_at_zero_is_one(self) -> None:
        curve = ZeroCurve([1.0, 5.0], [0.03, 0.04])
        assert curve.discount_factor(0.0) == pytest.approx(1.0)

    def test_flat_curve_discounts_as_exp(self) -> None:
        curve = ZeroCurve([1.0, 5.0], [0.04, 0.04])
        assert curve.discount_factor(2.0) == pytest.approx(math.exp(-0.08))

    def test_linear_zero_interpolation(self) -> None:
        curve = ZeroCurve([1.0, 2.0], [0.03, 0.04])
        assert curve.zero_rate(1.5) == pytest.approx(0.035)

    def test_flat_extrapolation_beyond_pillars(self) -> None:
        curve = ZeroCurve([1.0, 2.0], [0.03, 0.04])
        assert curve.zero_rate(10.0) == pytest.approx(0.04)  # clamps to last
        assert curve.zero_rate(0.1) == pytest.approx(0.03)  # clamps to first

    def test_log_df_interpolation_differs_from_linear_zero(self) -> None:
        pillars, rates = [1.0, 2.0], [0.02, 0.04]
        linear = ZeroCurve(
            pillars, rates, interpolation=InterpolationMethod.LINEAR_ZERO
        )
        logdf = ZeroCurve(
            pillars, rates, interpolation=InterpolationMethod.LINEAR_LOG_DF
        )
        # rate*tenor interp at 1.5 = 0.05, so zero = 0.05/1.5.
        assert logdf.zero_rate(1.5) == pytest.approx(0.05 / 1.5)
        assert linear.zero_rate(1.5) == pytest.approx(0.03)
        assert logdf.zero_rate(1.5) != pytest.approx(linear.zero_rate(1.5))

    def test_log_df_zero_tenor_uses_shortest_pillar(self) -> None:
        curve = ZeroCurve(
            [1.0, 2.0], [0.02, 0.04], interpolation=InterpolationMethod.LINEAR_LOG_DF
        )
        assert curve.zero_rate(0.0) == pytest.approx(0.02)

    def test_forward_on_flat_curve_equals_zero_rate(self) -> None:
        curve = ZeroCurve([1.0, 5.0], [0.03, 0.03])
        assert curve.forward_rate(1.0, 4.0) == pytest.approx(0.03)

    def test_forward_hand_worked(self) -> None:
        curve = ZeroCurve([1.0, 2.0], [0.03, 0.04])
        # (0.04*2 - 0.03*1) / (2 - 1) = 0.05
        assert curve.forward_rate(1.0, 2.0) == pytest.approx(0.05)

    def test_forward_requires_ordered_tenors(self) -> None:
        curve = ZeroCurve([1.0, 2.0], [0.03, 0.04])
        with pytest.raises(ConventionError, match="t2 > t1"):
            curve.forward_rate(2.0, 1.0)

    def test_negative_tenor_raises(self) -> None:
        curve = ZeroCurve([1.0, 2.0], [0.03, 0.04])
        with pytest.raises(ConventionError, match="non-negative"):
            curve.zero_rate(-1.0)

    def test_discount_factor_round_trips_to_zero_rate(self) -> None:
        curve = ZeroCurve([1.0, 3.0, 5.0], [0.02, 0.03, 0.035])
        for t in (1.5, 2.0, 4.0):
            df = curve.discount_factor(t)
            implied = -math.log(df) / t
            assert implied == pytest.approx(curve.zero_rate(t))


class TestRiskFreePolicy:
    def test_resolve_aligns_without_lookahead(
        self, monthly_rates: RiskFreeSeries
    ) -> None:
        policy = RiskFreePolicy(currency="USD")
        target = pd.to_datetime(["2024-02-15", "2024-03-10"])
        assert policy.resolve(monthly_rates, target).tolist() == [0.05, 0.045]

    def test_currency_mismatch_raises(self, monthly_rates: RiskFreeSeries) -> None:
        policy = RiskFreePolicy(currency="EUR")
        with pytest.raises(CurrencyMismatchError, match="never converted"):
            policy.resolve(monthly_rates, pd.to_datetime(["2024-02-15"]))

    def test_instrument_mismatch_raises_by_default(self) -> None:
        idx = pd.to_datetime(["2024-01-31"])
        series = RiskFreeSeries(
            pd.Series([0.05], index=idx), instrument=RateInstrument.TREASURY_BILL
        )
        policy = RiskFreePolicy(instrument=RateInstrument.OVERNIGHT)
        with pytest.raises(ConventionError, match="prefers"):
            policy.resolve(series, pd.to_datetime(["2024-02-15"]))

    def test_instrument_mismatch_allowed_when_disabled(self) -> None:
        idx = pd.to_datetime(["2024-01-31"])
        series = RiskFreeSeries(
            pd.Series([0.05], index=idx), instrument=RateInstrument.TREASURY_BILL
        )
        policy = RiskFreePolicy(
            instrument=RateInstrument.OVERNIGHT, require_instrument_match=False
        )
        assert policy.resolve(series, pd.to_datetime(["2024-02-15"])).tolist() == [0.05]

    def test_policy_staleness_enforced(self, monthly_rates: RiskFreeSeries) -> None:
        policy = RiskFreePolicy(currency="USD", max_staleness=pd.Timedelta(days=45))
        with pytest.raises(StaleDataError):
            policy.resolve(monthly_rates, pd.to_datetime(["2024-06-30"]))

    def test_default_daycount_is_recorded(self) -> None:
        q = RateQuote(0.05, pd.Timestamp("2024-01-31"))
        assert q.day_count is DayCount.ACT_360


class TestSharpeAcceptsRiskFreeSeriesOutput:
    """The rate subsystem exists to feed the ratios; prove the wiring end to end."""

    def test_period_returns_feed_sharpe(self) -> None:
        idx = pd.date_range("2024-01-31", periods=12, freq="ME")
        returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 3, index=idx)
        rf = RiskFreeSeries(pd.Series([0.024], index=idx[:1]))  # 2.4% annual simple
        rf_periodic = rf.to_period_returns(idx, 12)  # 0.2% per month, flat
        # Sharpe accepts an aligned per-period risk-free Series directly.
        result = cx.sharpe_ratio(returns, risk_free=rf_periodic, periods_per_year=12)
        assert np.isfinite(result)
