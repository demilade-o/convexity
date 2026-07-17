"""Sortino ratio: hand-worked validation, conventions, and edge cases.

Independent validation strategy
-------------------------------
The core assertion is a *hand derivation*, not a value recorded from this
implementation (which would only prove the code agrees with itself), and not a
value copied from another library (which would inherit its convention choices
and any bugs).

The working, for ``r = [0.01] * 11 + [-0.03]`` with ``MAR = 0`` per period and
``m = 12``:

    mean excess   = (11 x 0.01 + (-0.03)) / 12 = 0.08 / 12
    numerator     = (0.08 / 12) x 12          = 0.08          exactly

    sum of squared shortfalls = (-0.03)^2     = 0.0009        (one month below 0)
    DD (FULL, /n)             = sqrt(0.0009 / 12)
    denominator               = sqrt(0.0009 / 12) x sqrt(12)
                              = sqrt(0.0009)  = 0.03          exactly

    Sortino = 0.08 / 0.03 = 8/3

The sqrt(m) scaling cancels the 1/n in the FULL convention exactly, which is why
this fixture is a clean closed-form check rather than a decimal approximation.
"""

from __future__ import annotations

import math
import re

import numpy as np
import pandas as pd
import pytest

import convexity as cx
from convexity.exceptions import DataQualityError, FrequencyInferenceError


class TestHandWorkedDerivation:
    def test_matches_hand_derivation_exactly(
        self, hand_worked_returns: pd.Series
    ) -> None:
        result = cx.sortino_ratio(
            hand_worked_returns, mar=0.0, mar_is_annual=False, periods_per_year=12
        )
        assert result == pytest.approx(8.0 / 3.0, abs=1e-12)

    def test_numerator_and_denominator_are_separately_exact(
        self, hand_worked_returns: pd.Series
    ) -> None:
        # Denominator: annualised downside deviation is exactly 0.03.
        dd = cx.downside_deviation(hand_worked_returns, mar=0.0, annualise=False)
        assert dd == pytest.approx(math.sqrt(0.0009 / 12), abs=1e-15)
        assert dd * math.sqrt(12) == pytest.approx(0.03, abs=1e-15)

        # Numerator: annualised arithmetic excess is exactly 0.08.
        assert cx.arithmetic_annualised_return(
            hand_worked_returns, periods_per_year=12
        ) == pytest.approx(0.08, abs=1e-12)


class TestDownsideConvention:
    """The FULL vs DOWNSIDE_ONLY choice must change the answer, and be documented."""

    def test_full_convention_divides_by_total_observations(
        self, hand_worked_returns: pd.Series
    ) -> None:
        dd = cx.downside_deviation(
            hand_worked_returns, mar=0.0, convention=cx.DownsideConvention.FULL
        )
        assert dd == pytest.approx(math.sqrt(0.0009 / 12), abs=1e-15)

    def test_downside_only_divides_by_downside_count(
        self, hand_worked_returns: pd.Series
    ) -> None:
        dd = cx.downside_deviation(
            hand_worked_returns,
            mar=0.0,
            convention=cx.DownsideConvention.DOWNSIDE_ONLY,
        )
        # One observation below target, so the denominator is 1 and DD is |-0.03|.
        assert dd == pytest.approx(0.03, abs=1e-15)

    def test_conventions_differ_by_sqrt_n_over_n_below(
        self, hand_worked_returns: pd.Series
    ) -> None:
        full = cx.downside_deviation(
            hand_worked_returns, mar=0.0, convention=cx.DownsideConvention.FULL
        )
        only = cx.downside_deviation(
            hand_worked_returns,
            mar=0.0,
            convention=cx.DownsideConvention.DOWNSIDE_ONLY,
        )
        # With 1 of 12 below target the ratio is exactly sqrt(12/1).
        assert only / full == pytest.approx(math.sqrt(12.0), rel=1e-12)

    def test_default_is_full(self, hand_worked_returns: pd.Series) -> None:
        assert cx.downside_deviation(hand_worked_returns) == cx.downside_deviation(
            hand_worked_returns, convention=cx.DownsideConvention.FULL
        )

    def test_sortino_is_lower_under_downside_only(
        self, hand_worked_returns: pd.Series
    ) -> None:
        full = cx.sortino_ratio(
            hand_worked_returns, mar=0.0, mar_is_annual=False, periods_per_year=12
        )
        only = cx.sortino_ratio(
            hand_worked_returns,
            mar=0.0,
            mar_is_annual=False,
            periods_per_year=12,
            convention=cx.DownsideConvention.DOWNSIDE_ONLY,
        )
        assert only < full
        assert full / only == pytest.approx(math.sqrt(12.0), rel=1e-12)


class TestScalarTarget:
    def test_scalar_annual_mar_is_converted_to_period(
        self, hand_worked_returns: pd.Series
    ) -> None:
        # A 6% annual MAR under SIMPLE compounding is 0.5%/month.
        annual = cx.sortino_ratio(
            hand_worked_returns, mar=0.06, mar_is_annual=True, periods_per_year=12
        )
        explicit = cx.sortino_ratio(
            hand_worked_returns, mar=0.005, mar_is_annual=False, periods_per_year=12
        )
        assert annual == pytest.approx(explicit, rel=1e-12)

    def test_annual_flag_materially_changes_result(
        self, hand_worked_returns: pd.Series
    ) -> None:
        as_annual = cx.sortino_ratio(
            hand_worked_returns, mar=0.06, mar_is_annual=True, periods_per_year=12
        )
        as_period = cx.sortino_ratio(
            hand_worked_returns, mar=0.06, mar_is_annual=False, periods_per_year=12
        )
        # Treating 6% p.a. as 6% per month is catastrophically different; the
        # flag exists precisely so this cannot happen by accident.
        assert as_annual > 0
        assert as_period < 0

    def test_higher_mar_lowers_the_ratio(self, hand_worked_returns: pd.Series) -> None:
        low = cx.sortino_ratio(hand_worked_returns, mar=0.0, periods_per_year=12)
        high = cx.sortino_ratio(hand_worked_returns, mar=0.06, periods_per_year=12)
        assert high < low


class TestTimeVaryingTarget:
    def test_constant_series_matches_equivalent_scalar(
        self, hand_worked_returns: pd.Series
    ) -> None:
        varying = pd.Series(0.06, index=hand_worked_returns.index)
        assert cx.sortino_ratio(
            hand_worked_returns, mar=varying, periods_per_year=12
        ) == pytest.approx(
            cx.sortino_ratio(hand_worked_returns, mar=0.06, periods_per_year=12),
            rel=1e-12,
        )

    def test_sparse_rate_series_is_carried_forward_as_of(
        self, hand_worked_returns: pd.Series
    ) -> None:
        # Two quotes only; every month must resolve to the most recent prior one.
        quotes = pd.Series(
            [0.06, 0.02], index=pd.to_datetime(["2023-12-01", "2024-07-01"])
        )
        result = cx.sortino_ratio(hand_worked_returns, mar=quotes, periods_per_year=12)
        assert math.isfinite(result)

        # Equivalent explicit construction: 0.06 through June, 0.02 from July.
        expected_annual = pd.Series(
            [0.06] * 6 + [0.02] * 6, index=hand_worked_returns.index
        )
        assert result == pytest.approx(
            cx.sortino_ratio(
                hand_worked_returns, mar=expected_annual, periods_per_year=12
            ),
            rel=1e-12,
        )

    def test_future_rate_does_not_leak_backwards(
        self, hand_worked_returns: pd.Series
    ) -> None:
        """A rate published after the sample must not affect any observation."""
        base = pd.Series([0.06], index=pd.to_datetime(["2023-12-01"]))
        with_future = pd.Series(
            [0.06, 0.99], index=pd.to_datetime(["2023-12-01", "2030-01-01"])
        )
        assert cx.sortino_ratio(
            hand_worked_returns, mar=base, periods_per_year=12
        ) == pytest.approx(
            cx.sortino_ratio(hand_worked_returns, mar=with_future, periods_per_year=12),
            rel=1e-12,
        )


class TestZeroDenominatorPolicy:
    def test_no_downside_and_positive_excess_is_positive_infinity(
        self, all_positive: pd.Series
    ) -> None:
        assert cx.sortino_ratio(all_positive, mar=0.0, periods_per_year=12) == math.inf

    def test_no_downside_and_zero_excess_is_nan(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        """Every return exactly at target: 0/0 is indeterminate, not zero."""
        flat = pd.Series([0.0] * 12, index=monthly_index)
        assert math.isnan(
            cx.sortino_ratio(flat, mar=0.0, mar_is_annual=False, periods_per_year=12)
        )

    def test_all_below_target_is_negative_and_finite(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        losses = pd.Series([-0.01] * 12, index=monthly_index)
        result = cx.sortino_ratio(
            losses, mar=0.0, mar_is_annual=False, periods_per_year=12
        )
        assert result < 0
        assert math.isfinite(result)


class TestFrequency:
    def test_explicit_periods_per_year_takes_precedence_over_index(
        self, hand_worked_returns: pd.Series
    ) -> None:
        monthly = cx.sortino_ratio(hand_worked_returns, periods_per_year=12)
        daily = cx.sortino_ratio(hand_worked_returns, periods_per_year=252)
        assert monthly != daily

    def test_frequency_enum_matches_equivalent_periods_per_year(
        self, hand_worked_returns: pd.Series
    ) -> None:
        assert cx.sortino_ratio(
            hand_worked_returns, frequency=cx.Frequency.MONTHLY
        ) == pytest.approx(
            cx.sortino_ratio(hand_worked_returns, periods_per_year=12), rel=1e-12
        )

    def test_annualisation_scales_by_sqrt_m(
        self, hand_worked_returns: pd.Series
    ) -> None:
        """Numerator scales with m, denominator with sqrt(m): net sqrt(m)."""
        at_12 = cx.sortino_ratio(
            hand_worked_returns, mar=0.0, mar_is_annual=False, periods_per_year=12
        )
        at_48 = cx.sortino_ratio(
            hand_worked_returns, mar=0.0, mar_is_annual=False, periods_per_year=48
        )
        assert at_48 / at_12 == pytest.approx(math.sqrt(4.0), rel=1e-12)

    def test_no_annualisation_route_raises_rather_than_assuming_252(self) -> None:
        """A plain RangeIndex supports no inference; the library must not guess."""
        with pytest.raises(FrequencyInferenceError, match="does not assume a default"):
            cx.sortino_ratio(pd.Series([0.01, -0.02, 0.03]))

    def test_inference_from_index_is_used_when_confident(self) -> None:
        idx = pd.date_range("2024-01-01", periods=60, freq="B")
        rng = np.random.default_rng(42)
        returns = pd.Series(rng.normal(0.001, 0.01, 60), index=idx)
        # Inferred BUSINESS_DAILY (252) must equal the explicit equivalent.
        assert cx.sortino_ratio(returns) == pytest.approx(
            cx.sortino_ratio(returns, periods_per_year=252), rel=1e-12
        )


class TestMissingData:
    def test_nan_raises_by_default(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.01] * 11 + [float("nan")], index=monthly_index)
        with pytest.raises(DataQualityError, match="missing value"):
            cx.sortino_ratio(returns, periods_per_year=12)

    def test_drop_policy_computes_on_remaining_observations(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.01] * 11 + [float("nan")], index=monthly_index)
        result = cx.sortino_ratio(
            returns, periods_per_year=12, nan_policy=cx.NaNPolicy.DROP
        )
        # Eleven positive returns and no downside remain.
        assert result == math.inf

    def test_drop_matches_manually_cleaned_series(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        with_gap = pd.Series(
            [0.01] * 5 + [float("nan")] + [0.01] * 5 + [-0.03], index=monthly_index
        )
        cleaned = with_gap.dropna()
        assert cx.sortino_ratio(
            with_gap, periods_per_year=12, nan_policy=cx.NaNPolicy.DROP
        ) == pytest.approx(cx.sortino_ratio(cleaned, periods_per_year=12), rel=1e-12)

    def test_infinite_return_is_always_rejected(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.01] * 11 + [float("inf")], index=monthly_index)
        with pytest.raises(DataQualityError, match="infinite"):
            cx.sortino_ratio(returns, periods_per_year=12)

    def test_return_below_minus_one_is_rejected(
        self, monthly_index: pd.DatetimeIndex
    ) -> None:
        returns = pd.Series([0.01] * 11 + [-1.5], index=monthly_index)
        with pytest.raises(DataQualityError, match=re.escape("below -1.0")):
            cx.sortino_ratio(returns, periods_per_year=12)

    def test_total_loss_is_permitted(self, monthly_index: pd.DatetimeIndex) -> None:
        returns = pd.Series([0.01] * 11 + [-1.0], index=monthly_index)
        assert math.isfinite(cx.sortino_ratio(returns, periods_per_year=12))


class TestRollingWindows:
    def test_rolling_length_matches_input(self, mixed_returns: pd.Series) -> None:
        result = cx.rolling_sortino(mixed_returns, window=6, periods_per_year=12)
        assert len(result) == len(mixed_returns)
        assert result.index.equals(mixed_returns.index)

    def test_incomplete_windows_are_nan_not_fabricated(
        self, mixed_returns: pd.Series
    ) -> None:
        result = cx.rolling_sortino(mixed_returns, window=6, periods_per_year=12)
        assert result.iloc[:5].isna().all()
        assert result.iloc[5:].notna().all()

    def test_final_window_equals_direct_call_on_that_slice(
        self, mixed_returns: pd.Series
    ) -> None:
        window = 6
        result = cx.rolling_sortino(mixed_returns, window=window, periods_per_year=12)
        direct = cx.sortino_ratio(mixed_returns.iloc[-window:], periods_per_year=12)
        assert result.iloc[-1] == pytest.approx(direct, rel=1e-12)

    def test_full_window_equals_static_ratio(self, mixed_returns: pd.Series) -> None:
        n = len(mixed_returns)
        result = cx.rolling_sortino(mixed_returns, window=n, periods_per_year=12)
        assert result.iloc[-1] == pytest.approx(
            cx.sortino_ratio(mixed_returns, periods_per_year=12), rel=1e-12
        )

    def test_rolling_accepts_time_varying_target(
        self, mixed_returns: pd.Series
    ) -> None:
        quotes = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
        result = cx.rolling_sortino(
            mixed_returns, window=6, mar=quotes, periods_per_year=12
        )
        assert result.iloc[5:].notna().all()


class TestNonMutation:
    def test_input_series_is_not_modified(self, hand_worked_returns: pd.Series) -> None:
        before = hand_worked_returns.copy(deep=True)
        cx.sortino_ratio(hand_worked_returns, periods_per_year=12)
        pd.testing.assert_series_equal(hand_worked_returns, before)

    def test_target_series_is_not_modified(
        self, hand_worked_returns: pd.Series
    ) -> None:
        quotes = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
        before = quotes.copy(deep=True)
        cx.sortino_ratio(hand_worked_returns, mar=quotes, periods_per_year=12)
        pd.testing.assert_series_equal(quotes, before)
