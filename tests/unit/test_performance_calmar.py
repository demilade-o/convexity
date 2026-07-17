"""Calmar ratio: hand-worked validation, lookback semantics, and edge cases.

Independent validation strategy
-------------------------------
The core assertion is a hand derivation. For ``r = [0.02] * 11 + [-0.05]`` with
``m = 12`` and ``n = 12``:

    terminal wealth = 1.02^11 x 0.95
    annualised      = wealth^(m/n) - 1 = wealth^1 - 1        (m == n, so no root)

    The peak is 1.02^11, reached at t=11; the final month takes wealth to
    1.02^11 x 0.95, so the drawdown from that peak is exactly 0.95 - 1 = -0.05
    and no earlier decline exists.

    Calmar = (1.02^11 x 0.95 - 1) / 0.05

Because m == n the annualisation exponent is 1, which removes the fractional
power and leaves a value checkable against elementary arithmetic.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

import convexity as cx
from convexity.exceptions import DataQualityError


def _expected_calmar() -> float:
    wealth = 1.02**11 * 0.95
    return (wealth - 1.0) / 0.05


class TestHandWorkedDerivation:
    def test_matches_hand_derivation(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        result = cx.calmar_ratio(returns, periods_per_year=12)
        assert result == pytest.approx(_expected_calmar(), rel=1e-12)

    def test_components_are_separately_verifiable(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        assert cx.max_drawdown(returns) == pytest.approx(-0.05, abs=1e-12)
        assert cx.annualised_return(returns, periods_per_year=12) == pytest.approx(
            1.02**11 * 0.95 - 1.0, rel=1e-12
        )

    def test_uses_geometric_not_arithmetic_numerator(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        """Calmar compounds; conflating it with the arithmetic mean inflates it."""
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        geometric = cx.annualised_return(returns, periods_per_year=12)
        arithmetic = cx.arithmetic_annualised_return(returns, periods_per_year=12)
        assert geometric != pytest.approx(arithmetic, rel=1e-9)
        assert cx.calmar_ratio(returns, periods_per_year=12) == pytest.approx(
            geometric / 0.05, rel=1e-12
        )


class TestLookback:
    def test_full_sample_by_default(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        assert cx.calmar_ratio(returns, periods_per_year=12) == pytest.approx(
            cx.calmar_ratio(returns, lookback_periods=12, periods_per_year=12),
            rel=1e-12,
        )

    def test_lookback_excludes_an_earlier_deeper_drawdown(self) -> None:
        """The drawdown must be the worst *within the window*, not before it."""
        idx = pd.date_range("2023-01-31", periods=24, freq="ME")
        # A 30% crash in month 2, then a calm year.
        returns = pd.Series([0.01, -0.30] + [0.01] * 22, index=idx)

        full = cx.calmar_ratio(returns, periods_per_year=12)
        recent = cx.calmar_ratio(returns, lookback_periods=12, periods_per_year=12)

        # The full sample sees the crash; the trailing 12 months do not.
        assert cx.max_drawdown(returns) == pytest.approx(-0.30, abs=1e-9)
        assert cx.max_drawdown(returns.iloc[-12:]) == pytest.approx(0.0, abs=1e-12)
        assert math.isfinite(full)
        assert recent == math.inf

    def test_lookback_longer_than_sample_uses_whole_sample(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        assert cx.calmar_ratio(
            returns, lookback_periods=999, periods_per_year=12
        ) == pytest.approx(cx.calmar_ratio(returns, periods_per_year=12), rel=1e-12)

    def test_classic_36_month_lookback_constant_is_exposed(self) -> None:
        from convexity.performance import CALMAR_CLASSIC_LOOKBACK_MONTHS

        assert CALMAR_CLASSIC_LOOKBACK_MONTHS == 36

    def test_zero_or_negative_lookback_rejected(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 12, index=monthly_index)
        with pytest.raises(ValueError, match="lookback_periods must be >= 1"):
            cx.calmar_ratio(returns, lookback_periods=0, periods_per_year=12)


class TestRiskFree:
    def test_scalar_annual_rate_reduces_the_numerator(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        gross = cx.calmar_ratio(returns, periods_per_year=12)
        net = cx.calmar_ratio(returns, risk_free=0.05, periods_per_year=12)
        assert net < gross
        # Numerator falls by exactly the annual rate; denominator is unchanged.
        assert gross - net == pytest.approx(0.05 / 0.05, rel=1e-9)

    def test_default_risk_free_is_zero(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        assert cx.calmar_ratio(returns, periods_per_year=12) == pytest.approx(
            cx.calmar_ratio(returns, risk_free=0.0, periods_per_year=12), rel=1e-12
        )

    def test_time_varying_rate_matches_equivalent_constant(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        varying = pd.Series(0.05, index=monthly_index)
        assert cx.calmar_ratio(
            returns, risk_free=varying, periods_per_year=12
        ) == pytest.approx(
            cx.calmar_ratio(returns, risk_free=0.05, periods_per_year=12), rel=1e-12
        )

    def test_sparse_rate_series_carried_forward_as_of(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        quotes = pd.Series(
            [0.05, 0.01], index=pd.to_datetime(["2023-12-01", "2024-07-01"])
        )
        explicit = pd.Series([0.05] * 6 + [0.01] * 6, index=monthly_index)
        assert cx.calmar_ratio(
            returns, risk_free=quotes, periods_per_year=12
        ) == pytest.approx(
            cx.calmar_ratio(returns, risk_free=explicit, periods_per_year=12),
            rel=1e-12,
        )

    def test_future_rate_does_not_leak_backwards(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        base = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
        with_future = pd.Series(
            [0.05, 0.99], index=pd.to_datetime(["2023-12-01", "2031-01-01"])
        )
        assert cx.calmar_ratio(
            returns, risk_free=base, periods_per_year=12
        ) == pytest.approx(
            cx.calmar_ratio(returns, risk_free=with_future, periods_per_year=12),
            rel=1e-12,
        )

    def test_periodic_rate_flag(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        as_annual = cx.calmar_ratio(
            returns, risk_free=0.12, risk_free_is_annual=True, periods_per_year=12
        )
        as_period = cx.calmar_ratio(
            returns, risk_free=0.01, risk_free_is_annual=False, periods_per_year=12
        )
        # 12% p.a. simple == 1% per month.
        assert as_annual == pytest.approx(as_period, rel=1e-12)


class TestZeroDenominatorPolicy:
    def test_no_drawdown_and_positive_return_is_positive_infinity(
        self, all_positive: pd.Series
    ) -> None:
        assert cx.max_drawdown(all_positive) == 0.0
        assert cx.calmar_ratio(all_positive, periods_per_year=12) == math.inf

    def test_no_drawdown_and_zero_return_is_nan(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        flat = pd.Series([0.0] * 12, index=monthly_index)
        assert math.isnan(cx.calmar_ratio(flat, periods_per_year=12))

    def test_no_drawdown_but_negative_excess_is_negative_infinity(
        self, all_positive: pd.Series
    ) -> None:
        """A high risk-free rate can make the excess negative with no drawdown."""
        result = cx.calmar_ratio(all_positive, risk_free=0.50, periods_per_year=12)
        assert result == -math.inf

    def test_unrecovered_drawdown_is_finite(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.01] * 6 + [-0.10] * 6, index=monthly_index)
        result = cx.calmar_ratio(returns, periods_per_year=12)
        assert math.isfinite(result)
        assert result < 0

    def test_total_loss_annualises_to_minus_one(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.01] * 11 + [-1.0], index=monthly_index)
        assert cx.annualised_return(returns, periods_per_year=12) == -1.0
        assert cx.calmar_ratio(returns, periods_per_year=12) == pytest.approx(
            -1.0 / 1.0, rel=1e-12
        )


class TestFrequencyAndData:
    def test_frequency_enum_matches_periods_per_year(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        assert cx.calmar_ratio(
            returns, frequency=cx.Frequency.MONTHLY
        ) == pytest.approx(cx.calmar_ratio(returns, periods_per_year=12), rel=1e-12)

    def test_nan_raises_by_default(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.02] * 11 + [float("nan")], index=monthly_index)
        with pytest.raises(DataQualityError, match="missing value"):
            cx.calmar_ratio(returns, periods_per_year=12)

    def test_drop_matches_manually_cleaned(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        with_gap = pd.Series(
            [0.02] * 5 + [float("nan")] + [0.02] * 5 + [-0.05], index=monthly_index
        )
        assert cx.calmar_ratio(
            with_gap, periods_per_year=12, nan_policy=cx.NaNPolicy.DROP
        ) == pytest.approx(
            cx.calmar_ratio(with_gap.dropna(), periods_per_year=12), rel=1e-12
        )

    def test_input_not_mutated(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.02] * 11 + [-0.05], index=monthly_index)
        before = returns.copy(deep=True)
        cx.calmar_ratio(returns, periods_per_year=12)
        pd.testing.assert_series_equal(returns, before)


class TestRollingCalmar:
    def test_length_and_index_preserved(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_calmar(mixed_returns, window=6, periods_per_year=12)
        assert len(result) == len(mixed_returns)
        assert result.index.equals(mixed_returns.index)

    def test_incomplete_windows_are_nan(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_calmar(mixed_returns, window=6, periods_per_year=12)
        assert result.iloc[:5].isna().all()

    def test_final_window_equals_direct_call(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_calmar(mixed_returns, window=6, periods_per_year=12)
        direct = cx.calmar_ratio(mixed_returns.iloc[-6:], periods_per_year=12)
        assert result.iloc[-1] == pytest.approx(direct, rel=1e-12)

    def test_window_is_the_lookback(self, mixed_returns: pd.Series) -> None:
        rolling = cx.rolling_calmar(mixed_returns, window=6, periods_per_year=12)
        lookback = cx.calmar_ratio(
            mixed_returns, lookback_periods=6, periods_per_year=12
        )
        assert rolling.iloc[-1] == pytest.approx(lookback, rel=1e-12)

    def test_rejects_zero_window(self, mixed_returns: pd.Series) -> None:
        with pytest.raises(ValueError, match="window must be >= 1"):
            cx.rolling_calmar(mixed_returns, window=0, periods_per_year=12)

    def test_accepts_time_varying_rate(self, mixed_returns: pd.Series) -> None:
        quotes = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
        result = cx.rolling_calmar(
            mixed_returns, window=6, risk_free=quotes, periods_per_year=12
        )
        assert result.iloc[5:].notna().all()
