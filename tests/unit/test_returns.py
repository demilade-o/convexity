"""Returns, wealth, and annualisation."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

import convexity as cx
from convexity.exceptions import (
    DataQualityError,
    FrequencyInferenceError,
    IndexValidationError,
    InsufficientDataError,
)


class TestSimpleReturns:
    def test_hand_worked(self) -> None:
        prices = pd.Series([100.0, 110.0, 99.0])
        assert cx.simple_returns(prices).tolist() == pytest.approx([0.1, -0.1])

    def test_first_observation_dropped_not_zero_filled(self) -> None:
        """The first date has no predecessor; a zero there would be a fabrication."""
        prices = pd.Series([100.0, 110.0, 121.0])
        result = cx.simple_returns(prices)
        assert len(result) == len(prices) - 1
        assert result.index.tolist() == [1, 2]

    def test_index_preserved(self) -> None:
        index = pd.date_range("2024-01-01", periods=3)
        result = cx.simple_returns(pd.Series([100.0, 110.0, 99.0], index=index))
        assert result.index.equals(index[1:])

    def test_constant_prices_give_zero_returns(self) -> None:
        assert cx.simple_returns(pd.Series([100.0] * 5)).tolist() == [0.0] * 4

    @pytest.mark.parametrize("bad", [0.0, -1.0])
    def test_non_positive_price_rejected(self, bad: float) -> None:
        with pytest.raises(DataQualityError, match="non-positive"):
            cx.simple_returns(pd.Series([100.0, bad, 110.0]))

    def test_single_price_rejected(self) -> None:
        with pytest.raises(InsufficientDataError, match="At least 2 prices"):
            cx.simple_returns(pd.Series([100.0]))

    def test_nan_price_raises_by_default(self) -> None:
        with pytest.raises(DataQualityError, match="missing value"):
            cx.simple_returns(pd.Series([100.0, float("nan"), 110.0]))

    def test_input_not_mutated(self) -> None:
        prices = pd.Series([100.0, 110.0])
        before = prices.copy(deep=True)
        cx.simple_returns(prices)
        pd.testing.assert_series_equal(prices, before)


class TestLogReturns:
    def test_hand_worked(self) -> None:
        result = cx.log_returns(pd.Series([100.0, 110.0]))
        assert result.iloc[0] == pytest.approx(np.log(1.1), abs=1e-15)

    def test_additive_over_time(self) -> None:
        """The defining property of log returns: they sum where simple ones compound."""
        prices = pd.Series([100.0, 110.0, 99.0, 120.0])
        total = float(cx.log_returns(prices).sum())
        assert total == pytest.approx(np.log(120.0 / 100.0), abs=1e-12)

    def test_non_positive_price_rejected(self) -> None:
        with pytest.raises(DataQualityError, match="non-positive"):
            cx.log_returns(pd.Series([100.0, 0.0]))


class TestConversions:
    def test_round_trip_simple_to_log_and_back(self) -> None:
        simple = pd.Series([0.1, -0.05, 0.02, 0.0])
        recovered = cx.to_simple_returns(cx.to_log_returns(simple))
        np.testing.assert_allclose(recovered.to_numpy(), simple.to_numpy(), atol=1e-15)

    def test_log_of_total_loss_diverges_and_is_rejected(self) -> None:
        with pytest.raises(DataQualityError, match=re.escape("at or below -1.0")):
            cx.to_log_returns(pd.Series([-1.0]))

    def test_consistency_with_price_derived_log_returns(self) -> None:
        prices = pd.Series([100.0, 110.0, 99.0])
        from_prices = cx.log_returns(prices)
        from_simple = cx.to_log_returns(cx.simple_returns(prices))
        np.testing.assert_allclose(
            from_prices.to_numpy(), from_simple.to_numpy(), atol=1e-14
        )


class TestWealthIndex:
    def test_hand_worked(self) -> None:
        assert cx.wealth_index(pd.Series([0.1, -0.1])).tolist() == pytest.approx(
            [1.1, 0.99]
        )

    def test_initial_wealth_scales_linearly(self) -> None:
        base = cx.wealth_index(pd.Series([0.1, -0.1]))
        scaled = cx.wealth_index(pd.Series([0.1, -0.1]), initial=1000.0)
        np.testing.assert_allclose(scaled.to_numpy(), base.to_numpy() * 1000.0)

    def test_total_loss_drives_wealth_to_zero_and_it_stays(self) -> None:
        """Wealth cannot recover from -100%; later gains multiply zero."""
        result = cx.wealth_index(pd.Series([-1.0, 0.5, 2.0]))
        assert result.tolist() == [0.0, 0.0, 0.0]

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("nan")])
    def test_invalid_initial_wealth_rejected(self, bad: float) -> None:
        with pytest.raises(DataQualityError, match="finite and positive"):
            cx.wealth_index(pd.Series([0.1]), initial=bad)


class TestCumulativeReturn:
    def test_hand_worked(self) -> None:
        assert cx.cumulative_return(pd.Series([0.1, -0.1])) == pytest.approx(
            -0.01, abs=1e-12
        )

    def test_compounds_rather_than_sums(self) -> None:
        """+10% then -10% is -1%, not 0%. This is the whole point."""
        assert cx.cumulative_return(pd.Series([0.1, -0.1])) != 0.0

    def test_agrees_with_terminal_wealth(self) -> None:
        returns = pd.Series([0.02, -0.01, 0.03])
        terminal = float(cx.wealth_index(returns).iloc[-1])
        assert cx.cumulative_return(returns) == pytest.approx(terminal - 1.0, abs=1e-12)

    def test_single_observation(self) -> None:
        assert cx.cumulative_return(pd.Series([0.05])) == pytest.approx(0.05)


class TestAnnualisedReturn:
    def test_hand_worked_monthly(self) -> None:
        assert cx.annualised_return(
            pd.Series([0.01] * 12), periods_per_year=12
        ) == pytest.approx(1.01**12 - 1, rel=1e-12)

    def test_exactly_one_year_of_data_returns_the_holding_period_return(self) -> None:
        """With n == m the exponent is 1, so annualising is a no-op."""
        returns = pd.Series([0.01] * 12)
        assert cx.annualised_return(returns, periods_per_year=12) == pytest.approx(
            cx.cumulative_return(returns), rel=1e-12
        )

    def test_geometric_below_arithmetic_for_volatile_series(self) -> None:
        """Volatility drag: the gap is approximately half the variance."""
        returns = pd.Series([0.10, -0.08] * 6)
        geometric = cx.annualised_return(returns, periods_per_year=12)
        arithmetic = cx.arithmetic_annualised_return(returns, periods_per_year=12)
        assert geometric < arithmetic

    def test_total_loss_annualises_to_exactly_minus_one(self) -> None:
        returns = pd.Series([0.01] * 5 + [-1.0])
        assert cx.annualised_return(returns, periods_per_year=12) == -1.0

    def test_no_annualisation_route_raises(self) -> None:
        with pytest.raises(FrequencyInferenceError, match="does not assume a default"):
            cx.annualised_return(pd.Series([0.01, 0.02]))

    def test_frequency_enum_route(self) -> None:
        returns = pd.Series([0.01] * 12)
        assert cx.annualised_return(
            returns, frequency=cx.Frequency.MONTHLY
        ) == pytest.approx(cx.annualised_return(returns, periods_per_year=12))

    def test_inferred_from_index(self) -> None:
        index = pd.date_range("2024-01-31", periods=24, freq="ME")
        returns = pd.Series([0.01] * 24, index=index)
        assert cx.annualised_return(returns) == pytest.approx(
            cx.annualised_return(returns, periods_per_year=12), rel=1e-12
        )


class TestArithmeticAnnualisedReturn:
    def test_hand_worked(self) -> None:
        assert cx.arithmetic_annualised_return(
            pd.Series([0.01] * 12), periods_per_year=12
        ) == pytest.approx(0.12, rel=1e-12)

    def test_scales_linearly_with_periods_per_year(self) -> None:
        returns = pd.Series([0.01] * 12)
        at_12 = cx.arithmetic_annualised_return(returns, periods_per_year=12)
        at_24 = cx.arithmetic_annualised_return(returns, periods_per_year=24)
        assert at_24 == pytest.approx(2 * at_12, rel=1e-12)


class TestCagr:
    def test_hand_worked_using_elapsed_time(self) -> None:
        index = pd.to_datetime(["2023-01-01", "2024-01-01"])
        returns = pd.Series([0.0, 0.10], index=index)
        assert cx.cagr(returns) == pytest.approx(1.10 ** (365.25 / 365) - 1, rel=1e-12)

    def test_needs_no_periods_per_year(self) -> None:
        """CAGR measures elapsed time directly, so irregular spacing is fine."""
        index = pd.to_datetime(["2020-01-01", "2020-03-17", "2021-11-02", "2023-01-01"])
        returns = pd.Series([0.0, 0.05, -0.02, 0.08], index=index)
        assert np.isfinite(cx.cagr(returns))

    def test_requires_datetime_index(self) -> None:
        with pytest.raises(IndexValidationError, match="DatetimeIndex is required"):
            cx.cagr(pd.Series([0.0, 0.1]))

    def test_zero_elapsed_span_raises(self) -> None:
        index = pd.to_datetime(["2024-01-01", "2024-01-01"])
        # Duplicate timestamps are rejected before the span check.
        with pytest.raises(IndexValidationError, match="duplicated timestamp"):
            cx.cagr(pd.Series([0.0, 0.1], index=index))

    def test_total_loss(self) -> None:
        index = pd.to_datetime(["2023-01-01", "2024-01-01"])
        assert cx.cagr(pd.Series([0.0, -1.0], index=index)) == -1.0

    def test_longer_horizon_lowers_annualised_rate_for_same_total(self) -> None:
        one_year = pd.Series(
            [0.0, 0.21], index=pd.to_datetime(["2023-01-01", "2024-01-01"])
        )
        two_years = pd.Series(
            [0.0, 0.21], index=pd.to_datetime(["2022-01-01", "2024-01-01"])
        )
        assert cx.cagr(two_years) < cx.cagr(one_year)


class TestNonMutationAcrossReturns:
    def test_no_function_mutates_its_input(self) -> None:
        returns = pd.Series(
            [0.01, -0.02, 0.03], index=pd.date_range("2024-01-31", periods=3, freq="ME")
        )
        before = returns.copy(deep=True)
        cx.wealth_index(returns)
        cx.cumulative_return(returns)
        cx.annualised_return(returns, periods_per_year=12)
        cx.arithmetic_annualised_return(returns, periods_per_year=12)
        cx.cagr(returns)
        cx.to_log_returns(returns)
        pd.testing.assert_series_equal(returns, before)
