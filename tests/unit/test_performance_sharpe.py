"""Sharpe ratio: hand-worked validation, risk-free conventions, and edge cases.

Independent validation strategy
-------------------------------
The core assertion is a hand derivation. For ``r = [0.01, 0.02, -0.01, 0.03]``
repeated three times, with a zero risk-free rate and ``m = 12``:

    mean            = 0.05 / 4 = 0.0125
    numerator       = 0.0125 x 12 = 0.15                     exactly

    Each four-observation block contributes the same squared deviations about
    0.0125, so the sum of squares is 3 x 8.75e-4 = 2.625e-3 and the sample
    variance is 2.625e-3 / 11.

    denominator     = sqrt(2.625e-3 / 11) x sqrt(12)
    Sharpe          = 0.15 / denominator = 2.80306...
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import convexity as cx
from convexity.exceptions import DataQualityError, InsufficientDataError


def _expected_sharpe() -> float:
    values = np.array([0.01, 0.02, -0.01, 0.03] * 3)
    numerator = float(values.mean()) * 12
    denominator = float(values.std(ddof=1)) * math.sqrt(12)
    return numerator / denominator


class TestHandWorkedDerivation:
    def test_matches_hand_derivation(self, mixed_returns: pd.Series) -> None:
        assert cx.sharpe_ratio(mixed_returns, periods_per_year=12) == pytest.approx(
            _expected_sharpe(), rel=1e-12
        )

    def test_numerator_is_the_arithmetic_annualised_mean(
        self, mixed_returns: pd.Series
    ) -> None:
        assert cx.arithmetic_annualised_return(
            mixed_returns, periods_per_year=12
        ) == pytest.approx(0.15, rel=1e-12)

    def test_denominator_is_annualised_volatility_of_excess(
        self, mixed_returns: pd.Series
    ) -> None:
        assert cx.sharpe_ratio(mixed_returns, periods_per_year=12) == pytest.approx(
            cx.arithmetic_annualised_return(mixed_returns, periods_per_year=12)
            / cx.volatility(mixed_returns, periods_per_year=12),
            rel=1e-12,
        )

    def test_uses_arithmetic_not_geometric_numerator(
        self, mixed_returns: pd.Series
    ) -> None:
        """Sharpe defined it on the arithmetic mean; the two differ materially."""
        geometric = cx.annualised_return(mixed_returns, periods_per_year=12)
        arithmetic = cx.arithmetic_annualised_return(mixed_returns, periods_per_year=12)
        assert geometric != pytest.approx(arithmetic, rel=1e-9)
        assert cx.sharpe_ratio(mixed_returns, periods_per_year=12) == pytest.approx(
            arithmetic / cx.volatility(mixed_returns, periods_per_year=12), rel=1e-12
        )


class TestRiskFree:
    def test_zero_risk_free_is_the_default(self, mixed_returns: pd.Series) -> None:
        assert cx.sharpe_ratio(mixed_returns, periods_per_year=12) == pytest.approx(
            cx.sharpe_ratio(mixed_returns, risk_free=0.0, periods_per_year=12)
        )

    def test_positive_rate_lowers_the_ratio(self, mixed_returns: pd.Series) -> None:
        assert cx.sharpe_ratio(
            mixed_returns, risk_free=0.05, periods_per_year=12
        ) < cx.sharpe_ratio(mixed_returns, periods_per_year=12)

    def test_constant_rate_does_not_change_the_denominator(
        self, mixed_returns: pd.Series
    ) -> None:
        """Subtracting a constant shifts the mean but not the dispersion."""
        gross = cx.sharpe_ratio(mixed_returns, periods_per_year=12)
        net = cx.sharpe_ratio(mixed_returns, risk_free=0.12, periods_per_year=12)
        vol = cx.volatility(mixed_returns, periods_per_year=12)
        # Numerator falls by exactly 12% p.a.; denominator is unchanged.
        assert gross - net == pytest.approx(0.12 / vol, rel=1e-9)

    def test_annual_flag_matters_enormously(self, mixed_returns: pd.Series) -> None:
        """Treating 12% p.a. as 12% per period is the classic inflation bug."""
        as_annual = cx.sharpe_ratio(
            mixed_returns, risk_free=0.12, risk_free_is_annual=True, periods_per_year=12
        )
        as_period = cx.sharpe_ratio(
            mixed_returns,
            risk_free=0.12,
            risk_free_is_annual=False,
            periods_per_year=12,
        )
        assert as_annual > 0
        assert as_period < 0

    def test_annual_and_equivalent_period_rate_agree(
        self, mixed_returns: pd.Series
    ) -> None:
        assert cx.sharpe_ratio(
            mixed_returns, risk_free=0.12, risk_free_is_annual=True, periods_per_year=12
        ) == pytest.approx(
            cx.sharpe_ratio(
                mixed_returns,
                risk_free=0.01,
                risk_free_is_annual=False,
                periods_per_year=12,
            ),
            rel=1e-12,
        )

    def test_compounding_convention_changes_the_result(
        self, mixed_returns: pd.Series
    ) -> None:
        simple = cx.sharpe_ratio(
            mixed_returns,
            risk_free=0.05,
            periods_per_year=12,
            compounding=cx.Compounding.SIMPLE,
        )
        compounded = cx.sharpe_ratio(
            mixed_returns,
            risk_free=0.05,
            periods_per_year=12,
            compounding=cx.Compounding.COMPOUNDED,
        )
        assert simple != pytest.approx(compounded, rel=1e-9)

    def test_time_varying_rate_matches_equivalent_constant(
        self, mixed_returns: pd.Series
    ) -> None:
        varying = pd.Series(0.05, index=mixed_returns.index)
        assert cx.sharpe_ratio(
            mixed_returns, risk_free=varying, periods_per_year=12
        ) == pytest.approx(
            cx.sharpe_ratio(mixed_returns, risk_free=0.05, periods_per_year=12),
            rel=1e-12,
        )

    def test_varying_rate_affects_the_denominator(
        self, mixed_returns: pd.Series
    ) -> None:
        """A varying rate changes excess dispersion; a constant one cannot."""
        varying = pd.Series(
            np.linspace(0.01, 0.20, len(mixed_returns)), index=mixed_returns.index
        )
        constant = cx.sharpe_ratio(mixed_returns, risk_free=0.105, periods_per_year=12)
        varied = cx.sharpe_ratio(mixed_returns, risk_free=varying, periods_per_year=12)
        assert constant != pytest.approx(varied, rel=1e-6)

    def test_sparse_rate_carried_forward_as_of(self, mixed_returns: pd.Series) -> None:
        quotes = pd.Series(
            [0.05, 0.01], index=pd.to_datetime(["2023-12-01", "2024-07-01"])
        )
        explicit = pd.Series([0.05] * 6 + [0.01] * 6, index=mixed_returns.index)
        assert cx.sharpe_ratio(
            mixed_returns, risk_free=quotes, periods_per_year=12
        ) == pytest.approx(
            cx.sharpe_ratio(mixed_returns, risk_free=explicit, periods_per_year=12),
            rel=1e-12,
        )

    def test_future_rate_does_not_leak_backwards(
        self, mixed_returns: pd.Series
    ) -> None:
        base = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
        with_future = pd.Series(
            [0.05, 0.99], index=pd.to_datetime(["2023-12-01", "2032-01-01"])
        )
        assert cx.sharpe_ratio(
            mixed_returns, risk_free=base, periods_per_year=12
        ) == pytest.approx(
            cx.sharpe_ratio(mixed_returns, risk_free=with_future, periods_per_year=12),
            rel=1e-12,
        )


class TestZeroDenominatorPolicy:
    def test_constant_positive_returns_give_positive_infinity(
        self, all_positive: pd.Series
    ) -> None:
        """Zero excess dispersion with a positive mean: unbounded, by policy."""
        assert cx.sharpe_ratio(all_positive, periods_per_year=12) == math.inf

    def test_constant_zero_returns_give_nan(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        flat = pd.Series([0.0] * 12, index=monthly_index)
        assert math.isnan(cx.sharpe_ratio(flat, periods_per_year=12))

    def test_constant_negative_excess_gives_negative_infinity(
        self, all_positive: pd.Series
    ) -> None:
        result = cx.sharpe_ratio(all_positive, risk_free=0.50, periods_per_year=12)
        assert result == -math.inf


class TestFrequencyAndData:
    def test_annualisation_scales_by_sqrt_m(self, mixed_returns: pd.Series) -> None:
        at_12 = cx.sharpe_ratio(mixed_returns, periods_per_year=12)
        at_48 = cx.sharpe_ratio(mixed_returns, periods_per_year=48)
        assert at_48 / at_12 == pytest.approx(2.0, rel=1e-12)

    def test_ddof_changes_the_denominator(self, mixed_returns: pd.Series) -> None:
        sample = cx.sharpe_ratio(mixed_returns, periods_per_year=12, ddof=1)
        population = cx.sharpe_ratio(mixed_returns, periods_per_year=12, ddof=0)
        assert population > sample

    def test_frequency_enum_route(self, mixed_returns: pd.Series) -> None:
        assert cx.sharpe_ratio(
            mixed_returns, frequency=cx.Frequency.MONTHLY
        ) == pytest.approx(cx.sharpe_ratio(mixed_returns, periods_per_year=12))

    def test_needs_two_observations(self) -> None:
        with pytest.raises(InsufficientDataError):
            cx.sharpe_ratio(pd.Series([0.01]), periods_per_year=12)

    def test_nan_raises_by_default(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.01] * 11 + [float("nan")], index=monthly_index)
        with pytest.raises(DataQualityError, match="missing value"):
            cx.sharpe_ratio(returns, periods_per_year=12)

    def test_drop_matches_manually_cleaned(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        with_gap = pd.Series([0.01, 0.02, float("nan"), 0.03] * 3, index=monthly_index)
        assert cx.sharpe_ratio(
            with_gap, periods_per_year=12, nan_policy=cx.NaNPolicy.DROP
        ) == pytest.approx(
            cx.sharpe_ratio(with_gap.dropna(), periods_per_year=12), rel=1e-12
        )

    def test_input_not_mutated(self, mixed_returns: pd.Series) -> None:
        before = mixed_returns.copy(deep=True)
        cx.sharpe_ratio(mixed_returns, periods_per_year=12)
        pd.testing.assert_series_equal(mixed_returns, before)


class TestRollingSharpe:
    def test_length_and_index_preserved(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_sharpe(mixed_returns, window=6, periods_per_year=12)
        assert len(result) == len(mixed_returns)
        assert result.index.equals(mixed_returns.index)

    def test_incomplete_windows_are_nan(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_sharpe(mixed_returns, window=6, periods_per_year=12)
        assert result.iloc[:5].isna().all()
        assert result.iloc[5:].notna().all()

    def test_final_window_equals_direct_call(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_sharpe(mixed_returns, window=6, periods_per_year=12)
        direct = cx.sharpe_ratio(mixed_returns.iloc[-6:], periods_per_year=12)
        assert result.iloc[-1] == pytest.approx(direct, rel=1e-12)

    def test_full_window_equals_static(self, mixed_returns: pd.Series) -> None:
        n = len(mixed_returns)
        result = cx.rolling_sharpe(mixed_returns, window=n, periods_per_year=12)
        assert result.iloc[-1] == pytest.approx(
            cx.sharpe_ratio(mixed_returns, periods_per_year=12), rel=1e-12
        )

    def test_min_periods_allows_partial_windows(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_sharpe(
            mixed_returns, window=6, min_periods=3, periods_per_year=12
        )
        assert result.iloc[:2].isna().all()
        assert result.iloc[2:].notna().all()

    def test_rejects_zero_window(self, mixed_returns: pd.Series) -> None:
        with pytest.raises(ValueError, match="window must be >= 1"):
            cx.rolling_sharpe(mixed_returns, window=0, periods_per_year=12)

    def test_accepts_time_varying_rate(self, mixed_returns: pd.Series) -> None:
        quotes = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
        result = cx.rolling_sharpe(
            mixed_returns, window=6, risk_free=quotes, periods_per_year=12
        )
        assert result.iloc[5:].notna().all()
