"""Property-based invariants.

Hand-worked fixtures prove a formula on inputs the author chose. These tests
prove structural properties on inputs Hypothesis chooses, which is where the
author's blind spots live -- the constant series, the all-negative series, the
single observation, the value exactly at a boundary.

Every property here is a mathematical identity or a documented guarantee, not a
recorded output, so none of them can silently agree with a bug.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest
from hypothesis import HealthCheck, assume, given, settings
from hypothesis import strategies as st

import convexity as cx

# Returns strictly above -1.0: a simple return at or below -100% implies
# non-positive wealth and is rejected by validation, so it is out of domain here.
returns_strategy = st.lists(
    st.floats(
        min_value=-0.95,
        max_value=2.0,
        allow_nan=False,
        allow_infinity=False,
        width=64,
    ),
    min_size=2,
    max_size=60,
)

positive_prices = st.lists(
    st.floats(min_value=0.01, max_value=1e6, allow_nan=False, allow_infinity=False),
    min_size=2,
    max_size=60,
)

SETTINGS = settings(
    max_examples=200,
    deadline=None,
    suppress_health_check=[HealthCheck.function_scoped_fixture],
)


class TestReturnConversionRoundTrips:
    @given(returns_strategy)
    @SETTINGS
    def test_simple_to_log_and_back_is_identity(self, values: list[float]) -> None:
        series = pd.Series(values)
        recovered = cx.to_simple_returns(cx.to_log_returns(series))
        np.testing.assert_allclose(
            recovered.to_numpy(), series.to_numpy(), rtol=1e-9, atol=1e-12
        )

    @given(positive_prices)
    @SETTINGS
    def test_log_returns_sum_to_total_log_growth(self, prices: list[float]) -> None:
        """Log returns are additive; that is their defining property."""
        series = pd.Series(prices)
        total = float(cx.log_returns(series).sum())
        expected = math.log(prices[-1] / prices[0])
        assert total == pytest.approx(expected, rel=1e-9, abs=1e-9)

    @given(positive_prices)
    @SETTINGS
    def test_prices_reconstruct_from_simple_returns(self, prices: list[float]) -> None:
        series = pd.Series(prices)
        rebuilt = cx.wealth_index(cx.simple_returns(series), initial=prices[0])
        np.testing.assert_allclose(
            rebuilt.to_numpy(), np.array(prices[1:]), rtol=1e-8, atol=1e-8
        )


class TestWealthAndReturnConsistency:
    @given(returns_strategy)
    @SETTINGS
    def test_cumulative_return_equals_terminal_wealth_minus_one(
        self, values: list[float]
    ) -> None:
        series = pd.Series(values)
        terminal = float(cx.wealth_index(series).iloc[-1])
        assert cx.cumulative_return(series) == pytest.approx(
            terminal - 1.0, rel=1e-9, abs=1e-12
        )

    @given(returns_strategy)
    @SETTINGS
    def test_wealth_index_is_positive(self, values: list[float]) -> None:
        assert (cx.wealth_index(pd.Series(values)) > 0).all()

    @given(returns_strategy)
    @SETTINGS
    def test_periodic_geometric_never_exceeds_periodic_arithmetic(
        self, values: list[float]
    ) -> None:
        """Volatility drag: the AM-GM inequality, restated for returns.

        This holds for the *periodic* means. It does not hold for annualised
        figures: annualising raises growth to the power m/n, which extrapolates
        a short sample. Two observations of [0.0, 1.0] annualise geometrically
        to 2^6 - 1 = 63 at m=12 against an arithmetic 6 -- not a violation of
        AM-GM but of the assumption that extrapolation preserves an inequality
        between means. periods_per_year=1 removes the extrapolation.
        """
        series = pd.Series(values)
        geometric = cx.annualised_return(series, periods_per_year=1)
        arithmetic = cx.arithmetic_annualised_return(series, periods_per_year=1)
        assert geometric <= arithmetic + 1e-9


class TestDrawdownInvariants:
    @given(returns_strategy)
    @SETTINGS
    def test_drawdown_is_never_positive(self, values: list[float]) -> None:
        assert (cx.drawdown_series(pd.Series(values)) <= 1e-12).all()

    @given(returns_strategy)
    @SETTINGS
    def test_drawdown_never_below_minus_one(self, values: list[float]) -> None:
        """Wealth cannot fall more than 100% below its peak."""
        assert (cx.drawdown_series(pd.Series(values)) >= -1.0 - 1e-12).all()

    @given(returns_strategy)
    @SETTINGS
    def test_max_drawdown_is_the_minimum_of_the_curve(
        self, values: list[float]
    ) -> None:
        series = pd.Series(values)
        assert cx.max_drawdown(series) == pytest.approx(
            float(cx.drawdown_series(series).min()), abs=1e-12
        )

    @given(returns_strategy)
    @SETTINGS
    def test_ulcer_never_below_pain(self, values: list[float]) -> None:
        """Power-mean inequality: quadratic mean dominates arithmetic mean."""
        series = pd.Series(values)
        assert cx.ulcer_index(series) >= cx.pain_index(series) - 1e-12

    @given(returns_strategy)
    @SETTINGS
    def test_all_gains_means_no_drawdown(self, values: list[float]) -> None:
        gains = pd.Series([abs(v) for v in values])
        assert cx.max_drawdown(gains) == pytest.approx(0.0, abs=1e-12)


class TestDispersionInvariants:
    @given(returns_strategy)
    @SETTINGS
    def test_volatility_is_non_negative(self, values: list[float]) -> None:
        assert cx.volatility(pd.Series(values), annualise=False) >= 0.0

    @given(returns_strategy)
    @SETTINGS
    def test_volatility_is_translation_invariant(self, values: list[float]) -> None:
        """Adding a constant shifts the mean, never the dispersion."""
        series = pd.Series(values)
        shifted = series + 0.01
        assert cx.volatility(shifted, annualise=False) == pytest.approx(
            cx.volatility(series, annualise=False), rel=1e-7, abs=1e-12
        )

    @given(returns_strategy, st.floats(min_value=0.1, max_value=10.0))
    @SETTINGS
    def test_volatility_scales_with_magnitude(
        self, values: list[float], scale: float
    ) -> None:
        series = pd.Series(values)
        # Scaling can push a return below -1.0, which is out of domain.
        assume(all(v * scale > -0.99 for v in values))
        assert cx.volatility(series * scale, annualise=False) == pytest.approx(
            cx.volatility(series, annualise=False) * scale, rel=1e-7, abs=1e-12
        )

    @given(returns_strategy)
    @SETTINGS
    def test_downside_deviation_is_non_negative(self, values: list[float]) -> None:
        assert cx.downside_deviation(pd.Series(values), mar=0.0) >= 0.0

    @given(returns_strategy)
    @SETTINGS
    def test_downside_deviation_rises_with_the_target(
        self, values: list[float]
    ) -> None:
        """A higher bar can only create shortfalls, never remove them."""
        series = pd.Series(values)
        low = cx.downside_deviation(series, mar=0.0)
        high = cx.downside_deviation(series, mar=0.05)
        assert high >= low - 1e-12

    @given(returns_strategy)
    @SETTINGS
    def test_downside_only_never_below_full(self, values: list[float]) -> None:
        """Dividing by n_below <= n cannot produce a smaller deviation."""
        series = pd.Series(values)
        full = cx.downside_deviation(
            series, mar=0.0, convention=cx.DownsideConvention.FULL
        )
        only = cx.downside_deviation(
            series, mar=0.0, convention=cx.DownsideConvention.DOWNSIDE_ONLY
        )
        assert only >= full - 1e-12

    @given(returns_strategy)
    @SETTINGS
    def test_upside_mirrors_downside_under_negation(self, values: list[float]) -> None:
        series = pd.Series(values)
        assume(all(v > -1.0 for v in (-series).tolist()))
        assert cx.upside_deviation(series, mar=0.0) == pytest.approx(
            cx.downside_deviation(-series, mar=0.0), rel=1e-9, abs=1e-12
        )


class TestRatioInvariants:
    @given(returns_strategy)
    @SETTINGS
    def test_sortino_never_below_sharpe_for_zero_target(
        self, values: list[float]
    ) -> None:
        """Downside deviation cannot exceed total deviation about the same mean.

        Both ratios share a numerator here, so the ordering follows from the
        denominators alone.
        """
        series = pd.Series(values)
        assume(cx.volatility(series, annualise=False) > 1e-6)

        sharpe = cx.sharpe_ratio(series, periods_per_year=12, ddof=0)
        sortino = cx.sortino_ratio(
            series, mar=0.0, mar_is_annual=False, periods_per_year=12
        )
        assume(math.isfinite(sharpe) and math.isfinite(sortino))
        assume(sharpe > 0)
        assert sortino >= sharpe - 1e-6

    @given(returns_strategy)
    @SETTINGS
    def test_ratios_are_deterministic(self, values: list[float]) -> None:
        """Identical inputs must give bit-identical outputs, always."""
        series = pd.Series(values)
        first = cx.sortino_ratio(series, periods_per_year=12)
        second = cx.sortino_ratio(series, periods_per_year=12)
        assert (first == second) or (math.isnan(first) and math.isnan(second))

    @given(returns_strategy, st.floats(min_value=1.0, max_value=365.0))
    @SETTINGS
    def test_sortino_annualisation_scales_by_sqrt_m(
        self, values: list[float], ppy: float
    ) -> None:
        series = pd.Series(values)
        base = cx.sortino_ratio(
            series, mar=0.0, mar_is_annual=False, periods_per_year=1
        )
        scaled = cx.sortino_ratio(
            series, mar=0.0, mar_is_annual=False, periods_per_year=ppy
        )
        assume(math.isfinite(base) and math.isfinite(scaled))
        assume(abs(base) > 1e-9)
        assert scaled == pytest.approx(base * math.sqrt(ppy), rel=1e-6)

    @given(returns_strategy)
    @SETTINGS
    def test_higher_risk_free_never_raises_sharpe(self, values: list[float]) -> None:
        series = pd.Series(values)
        low = cx.sharpe_ratio(series, risk_free=0.0, periods_per_year=12)
        high = cx.sharpe_ratio(series, risk_free=0.10, periods_per_year=12)
        assume(math.isfinite(low) and math.isfinite(high))
        assert high <= low + 1e-9


class TestCompoundingRoundTrips:
    @given(
        st.floats(min_value=-0.5, max_value=1.0, allow_nan=False),
        st.sampled_from([1.0, 4.0, 12.0, 52.0, 252.0, 365.0]),
        st.sampled_from(list(cx.Compounding)),
    )
    @SETTINGS
    def test_annual_to_period_round_trips(
        self, rate: float, ppy: float, compounding: cx.Compounding
    ) -> None:
        period = cx.annual_to_period_rate(rate, ppy, compounding)
        recovered = cx.period_to_annual_rate(period, ppy, compounding)
        assert recovered == pytest.approx(rate, rel=1e-9, abs=1e-12)

    @given(
        st.floats(min_value=-0.5, max_value=1.0, allow_nan=False),
        st.sampled_from([1.0, 4.0, 12.0, 252.0]),
    )
    @SETTINGS
    def test_compounded_period_rate_recovers_the_annual_rate(
        self, rate: float, ppy: float
    ) -> None:
        """The defining property of COMPOUNDED: (1+r_p)^m - 1 == r_a."""
        period = cx.annual_to_period_rate(rate, ppy, cx.Compounding.COMPOUNDED)
        assert (1 + period) ** ppy - 1 == pytest.approx(rate, rel=1e-8, abs=1e-12)

    @given(st.floats(min_value=0.0, max_value=1.0, allow_nan=False))
    @SETTINGS
    def test_convention_ordering_holds_for_any_positive_rate(self, rate: float) -> None:
        assume(rate > 1e-6)
        simple = cx.annual_to_period_rate(rate, 12, cx.Compounding.SIMPLE)
        continuous = cx.annual_to_period_rate(rate, 12, cx.Compounding.CONTINUOUS)
        compounded = cx.annual_to_period_rate(rate, 12, cx.Compounding.COMPOUNDED)
        assert continuous >= simple >= compounded


class TestNonMutation:
    @given(returns_strategy)
    @SETTINGS
    def test_no_metric_mutates_its_input(self, values: list[float]) -> None:
        index = pd.date_range("2024-01-31", periods=len(values), freq="ME")
        series = pd.Series(values, index=index)
        before = series.copy(deep=True)

        cx.wealth_index(series)
        cx.cumulative_return(series)
        cx.drawdown_series(series)
        cx.max_drawdown(series)
        cx.volatility(series, periods_per_year=12)
        cx.downside_deviation(series)
        cx.ulcer_index(series)
        cx.sortino_ratio(series, periods_per_year=12)
        cx.calmar_ratio(series, periods_per_year=12)

        pd.testing.assert_series_equal(series, before)


class TestAlignmentInvariants:
    @given(
        st.integers(min_value=1, max_value=40),
        st.integers(min_value=1, max_value=40),
    )
    @SETTINGS
    def test_asof_never_returns_a_future_value(
        self, n_targets: int, n_sources: int
    ) -> None:
        """The core point-in-time guarantee, on arbitrary shapes."""
        targets = pd.date_range("2024-01-01", periods=n_targets, freq="D")
        sources = pd.date_range("2023-12-01", periods=n_sources, freq="D")
        values = pd.Series(np.arange(len(sources), dtype=float), index=sources)

        aligned = cx.align_asof(targets, values)

        for position, got in enumerate(aligned.to_numpy()):
            if np.isnan(got):
                continue
            # The matched value's own observation date must not be after the
            # target date it informed.
            observed_at = sources[int(got)]
            assert observed_at <= targets[position]
