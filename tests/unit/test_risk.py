"""Dispersion, downside, and drawdown risk."""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

import convexity as cx
from convexity.exceptions import InsufficientDataError, NoOverlapError


class TestDrawdownSeries:
    def test_hand_worked(self) -> None:
        # wealth: 1.10, 0.88, 0.924; running peak 1.10 throughout.
        result = cx.drawdown_series(pd.Series([0.1, -0.2, 0.05]))
        assert result.tolist() == pytest.approx([0.0, -0.2, -0.16])

    def test_never_positive(self) -> None:
        returns = pd.Series([0.05, 0.03, -0.01, 0.02])
        assert (cx.drawdown_series(returns) <= 1e-15).all()

    def test_first_period_loss_is_a_real_drawdown(self) -> None:
        """The running peak includes starting wealth of 1.0."""
        result = cx.drawdown_series(pd.Series([-0.1, 0.05]))
        assert result.iloc[0] == pytest.approx(-0.1)

    def test_monotonic_gains_never_draw_down(self) -> None:
        assert (cx.drawdown_series(pd.Series([0.01] * 10)) == 0.0).all()

    def test_index_preserved(self) -> None:
        index = pd.date_range("2024-01-31", periods=3, freq="ME")
        result = cx.drawdown_series(pd.Series([0.1, -0.2, 0.05], index=index))
        assert result.index.equals(index)


class TestMaxDrawdown:
    def test_hand_worked(self) -> None:
        assert cx.max_drawdown(pd.Series([0.1, -0.2, 0.05])) == pytest.approx(-0.2)

    def test_no_drawdown_is_exactly_zero_not_nan(self) -> None:
        """A series that never falls has a real MDD of 0, not a missing one."""
        assert cx.max_drawdown(pd.Series([0.01, 0.02])) == 0.0

    def test_total_loss_is_minus_one(self) -> None:
        assert cx.max_drawdown(pd.Series([-1.0])) == pytest.approx(-1.0)

    def test_equals_minimum_of_drawdown_series(self) -> None:
        returns = pd.Series([0.02, -0.05, 0.01, -0.08, 0.03])
        assert cx.max_drawdown(returns) == pytest.approx(
            float(cx.drawdown_series(returns).min())
        )

    def test_deepest_of_multiple_episodes_wins(self) -> None:
        returns = pd.Series([0.1, -0.05, 0.05, -0.20, 0.30])
        # Depth is measured from the running peak of 1.1, not from the interim
        # level of 1.045: 1.1 x 0.95 x 1.05 x 0.80 / 1.1 - 1 = -0.202.
        assert cx.max_drawdown(returns) == pytest.approx(-0.202, abs=1e-12)


class TestDrawdownEpisodes:
    def test_single_recovered_episode(self) -> None:
        index = pd.date_range("2024-01-31", periods=4, freq="ME")
        episodes = cx.drawdown_episodes(pd.Series([0.1, -0.2, 0.3, 0.0], index=index))
        assert len(episodes) == 1
        episode = episodes[0]
        assert episode.depth == pytest.approx(-0.2)
        assert episode.is_recovered
        assert episode.recovery is not None
        assert episode.trough == index[1]

    def test_no_episodes_when_never_underwater(self) -> None:
        assert cx.drawdown_episodes(pd.Series([0.01] * 5)) == []

    def test_unrecovered_episode_reports_none_rather_than_imputing(self) -> None:
        index = pd.date_range("2024-01-31", periods=3, freq="ME")
        episodes = cx.drawdown_episodes(pd.Series([0.1, -0.2, -0.05], index=index))
        assert len(episodes) == 1
        assert not episodes[0].is_recovered
        assert episodes[0].recovery is None
        assert episodes[0].time_to_recovery is None

    def test_multiple_distinct_episodes(self) -> None:
        index = pd.date_range("2024-01-31", periods=6, freq="ME")
        returns = pd.Series([0.1, -0.05, 0.10, -0.08, 0.15, 0.0], index=index)
        episodes = cx.drawdown_episodes(returns)
        assert len(episodes) == 2
        assert all(e.is_recovered for e in episodes)

    def test_trough_is_the_deepest_point_not_the_first_decline(self) -> None:
        index = pd.date_range("2024-01-31", periods=5, freq="ME")
        returns = pd.Series([0.1, -0.05, -0.10, 0.30, 0.0], index=index)
        episode = cx.drawdown_episodes(returns)[0]
        assert episode.trough == index[2]

    def test_episode_is_frozen(self) -> None:
        episodes = cx.drawdown_episodes(
            pd.Series(
                [0.1, -0.2, 0.3],
                index=pd.date_range("2024-01-31", periods=3, freq="ME"),
            )
        )
        with pytest.raises((AttributeError, TypeError)):
            episodes[0].depth = 0.0  # type: ignore[misc]


class TestAverageDrawdown:
    def test_averages_over_episodes_not_observations(self) -> None:
        index = pd.date_range("2024-01-31", periods=6, freq="ME")
        returns = pd.Series([0.1, -0.10, 0.15, -0.20, 0.40, 0.0], index=index)
        episodes = cx.drawdown_episodes(returns)
        expected = float(np.mean([e.depth for e in episodes]))
        assert cx.average_drawdown(returns) == pytest.approx(expected)

    def test_zero_when_no_episodes(self) -> None:
        assert cx.average_drawdown(pd.Series([0.01] * 5)) == 0.0


class TestUlcerAndPain:
    def test_ulcer_index_hand_worked(self) -> None:
        # drawdowns: 0, -0.2, -0.16  -> sqrt(mean of squares)
        returns = pd.Series([0.1, -0.2, 0.05])
        dd = cx.drawdown_series(returns).to_numpy()
        assert cx.ulcer_index(returns) == pytest.approx(
            math.sqrt(float(np.mean(dd**2))), abs=1e-15
        )

    def test_pain_index_hand_worked(self) -> None:
        returns = pd.Series([0.1, -0.2, 0.05])
        dd = cx.drawdown_series(returns).to_numpy()
        assert cx.pain_index(returns) == pytest.approx(
            float(np.mean(np.abs(dd))), abs=1e-15
        )

    def test_both_zero_when_never_underwater(self) -> None:
        returns = pd.Series([0.01] * 5)
        assert cx.ulcer_index(returns) == 0.0
        assert cx.pain_index(returns) == 0.0

    @pytest.mark.parametrize(
        "values",
        [
            [-0.4, 0.0, 0.0, 0.0],
            [-0.1, -0.1, -0.1, -0.1],
            [0.02, -0.05, 0.01, -0.08],
            [0.01, 0.01, 0.01],
        ],
    )
    def test_ulcer_never_below_pain(self, values: list[float]) -> None:
        """Quadratic mean dominates arithmetic mean (power-mean inequality).

        This is the formal sense in which the Ulcer index penalises depth more
        than the pain index: squaring weights deep drawdowns disproportionately,
        so UI >= PI for every series, with equality only when the underwater
        curve is flat.
        """
        returns = pd.Series(values)
        assert cx.ulcer_index(returns) >= cx.pain_index(returns) - 1e-15

    def test_ulcer_equals_pain_for_a_flat_underwater_curve(self) -> None:
        # A single total decline held flat: every drawdown observation is -0.4.
        returns = pd.Series([-0.4, 0.0, 0.0, 0.0])
        assert cx.ulcer_index(returns) == pytest.approx(cx.pain_index(returns))

    def test_both_increase_with_severity(self) -> None:
        mild = pd.Series([-0.05, 0.0, 0.0])
        severe = pd.Series([-0.25, 0.0, 0.0])
        assert cx.ulcer_index(severe) > cx.ulcer_index(mild)
        assert cx.pain_index(severe) > cx.pain_index(mild)

    def test_both_non_negative(self) -> None:
        returns = pd.Series([0.02, -0.05, 0.01, -0.08])
        assert cx.ulcer_index(returns) >= 0
        assert cx.pain_index(returns) >= 0


class TestVolatility:
    def test_hand_worked_periodic(self) -> None:
        returns = pd.Series([0.01, -0.01, 0.02, -0.02])
        assert cx.volatility(returns, annualise=False) == pytest.approx(
            float(np.std(returns.to_numpy(), ddof=1)), abs=1e-15
        )

    def test_annualisation_scales_by_sqrt_m(self) -> None:
        returns = pd.Series([0.01, -0.01, 0.02, -0.02])
        periodic = cx.volatility(returns, annualise=False)
        annual = cx.volatility(returns, periods_per_year=12)
        assert annual == pytest.approx(periodic * math.sqrt(12), rel=1e-12)

    def test_ddof_changes_the_answer(self) -> None:
        returns = pd.Series([0.01, -0.01, 0.02, -0.02])
        sample = cx.volatility(returns, annualise=False, ddof=1)
        population = cx.volatility(returns, annualise=False, ddof=0)
        assert sample > population
        assert population == pytest.approx(
            float(np.std(returns.to_numpy(), ddof=0)), abs=1e-15
        )

    def test_constant_series_has_exactly_zero_volatility(self) -> None:
        """Exactly zero, not merely close to it.

        np.std over identical floats leaves ~1e-18 of rounding dust. Any ratio
        dividing by that dust reports a meaningless finite number (~1e16) in
        place of the documented infinity, so exactness here is load-bearing.
        """
        assert cx.volatility(pd.Series([0.01] * 10), annualise=False) == 0.0
        assert cx.volatility(pd.Series([0.01] * 10), periods_per_year=12) == 0.0

    def test_exact_std_returns_nan_for_empty(self) -> None:
        from convexity.risk import exact_std

        assert math.isnan(exact_std(np.array([]), ddof=1))

    def test_single_observation_rejected_for_sample_std(self) -> None:
        with pytest.raises(InsufficientDataError):
            cx.volatility(pd.Series([0.01]), annualise=False, ddof=1)

    def test_annualise_requires_a_frequency_route(self) -> None:
        from convexity.exceptions import FrequencyInferenceError

        with pytest.raises(FrequencyInferenceError):
            cx.volatility(pd.Series([0.01, 0.02]))


class TestDownsideDeviation:
    def test_hand_worked_full_convention(self) -> None:
        returns = pd.Series([0.01] * 11 + [-0.03])
        assert cx.downside_deviation(returns, mar=0.0) == pytest.approx(
            math.sqrt(0.0009 / 12), abs=1e-15
        )

    def test_zero_when_nothing_below_target(self) -> None:
        """A true statement about the sample, not a missing value."""
        assert cx.downside_deviation(pd.Series([0.01] * 12), mar=0.0) == 0.0

    def test_downside_only_zero_when_nothing_below_target(self) -> None:
        assert (
            cx.downside_deviation(
                pd.Series([0.01] * 12),
                mar=0.0,
                convention=cx.DownsideConvention.DOWNSIDE_ONLY,
            )
            == 0.0
        )

    def test_ignores_upside_entirely(self) -> None:
        """Only shortfalls contribute; a bigger gain must not change the result."""
        base = pd.Series([0.01, -0.02, 0.03])
        bigger = pd.Series([0.01, -0.02, 0.50])
        assert cx.downside_deviation(base, mar=0.0) == pytest.approx(
            cx.downside_deviation(bigger, mar=0.0)
        )

    def test_higher_target_increases_deviation(self) -> None:
        returns = pd.Series([0.01, 0.02, -0.01])
        assert cx.downside_deviation(returns, mar=0.05) > cx.downside_deviation(
            returns, mar=0.0
        )

    def test_time_varying_target(self) -> None:
        index = pd.date_range("2024-01-31", periods=4, freq="ME")
        returns = pd.Series([0.01, 0.02, -0.01, 0.03], index=index)
        constant = pd.Series(0.015, index=index)
        assert cx.downside_deviation(returns, mar=constant) == pytest.approx(
            cx.downside_deviation(returns, mar=0.015)
        )

    def test_annualisation(self) -> None:
        returns = pd.Series([0.01] * 11 + [-0.03])
        periodic = cx.downside_deviation(returns, mar=0.0, annualise=False)
        annual = cx.downside_deviation(
            returns, mar=0.0, annualise=True, periods_per_year=12
        )
        assert annual == pytest.approx(periodic * math.sqrt(12), rel=1e-12)

    def test_non_finite_target_rejected(self) -> None:
        with pytest.raises(InsufficientDataError, match="must be finite"):
            cx.downside_deviation(pd.Series([0.01]), mar=float("nan"))

    def test_all_below_target(self) -> None:
        returns = pd.Series([-0.01] * 4)
        assert cx.downside_deviation(returns, mar=0.0) == pytest.approx(0.01)


class TestUpsideDeviation:
    def test_mirrors_downside_for_negated_series(self) -> None:
        returns = pd.Series([0.01, -0.02, 0.03, -0.01])
        assert cx.upside_deviation(returns, mar=0.0) == pytest.approx(
            cx.downside_deviation(-returns, mar=0.0)
        )

    def test_zero_when_nothing_above_target(self) -> None:
        assert cx.upside_deviation(pd.Series([-0.01] * 5), mar=0.0) == 0.0

    def test_downside_only_convention(self) -> None:
        returns = pd.Series([0.01] * 11 + [-0.03])
        assert cx.upside_deviation(
            returns, mar=0.0, convention=cx.DownsideConvention.DOWNSIDE_ONLY
        ) == pytest.approx(0.01)

    def test_downside_only_zero_when_nothing_above(self) -> None:
        assert (
            cx.upside_deviation(
                pd.Series([-0.01] * 5),
                mar=0.0,
                convention=cx.DownsideConvention.DOWNSIDE_ONLY,
            )
            == 0.0
        )


class TestSkewness:
    def test_known_value(self) -> None:
        # 2/sqrt(3) for this three-equal-plus-one shape.
        assert cx.skewness(pd.Series([0.0, 0.0, 0.0, 0.3])) == pytest.approx(
            2 / math.sqrt(3), rel=1e-9
        )

    def test_symmetric_distribution_has_zero_skew(self) -> None:
        assert cx.skewness(pd.Series([-0.2, -0.1, 0.1, 0.2])) == pytest.approx(
            0.0, abs=1e-12
        )

    def test_sign_flips_with_the_series(self) -> None:
        returns = pd.Series([0.0, 0.0, 0.0, 0.3])
        assert cx.skewness(-returns) == pytest.approx(-cx.skewness(returns), rel=1e-12)

    def test_zero_variance_is_nan_not_zero(self) -> None:
        """0/0 is indeterminate; reporting 0 would imply symmetry we cannot know."""
        assert math.isnan(cx.skewness(pd.Series([0.01] * 5)))

    def test_unbiased_differs_from_biased(self) -> None:
        returns = pd.Series([0.0, 0.0, 0.0, 0.3])
        assert cx.skewness(returns, bias=False) != pytest.approx(
            cx.skewness(returns, bias=True)
        )

    def test_unbiased_needs_three_observations(self) -> None:
        with pytest.raises(InsufficientDataError, match="at least 3"):
            cx.skewness(pd.Series([0.1, 0.2]), bias=False)


class TestKurtosis:
    def test_known_value_fisher(self) -> None:
        assert cx.kurtosis(pd.Series([-0.1, 0.0, 0.0, 0.1])) == pytest.approx(-1.0)

    def test_pearson_is_fisher_plus_three(self) -> None:
        returns = pd.Series([-0.10, 0.0, 0.0, 0.10, 0.05, -0.05])
        assert cx.kurtosis(returns, fisher=False) == pytest.approx(
            cx.kurtosis(returns, fisher=True) + 3.0, rel=1e-12
        )

    def test_fat_tails_score_higher(self) -> None:
        normalish = pd.Series([-0.10, -0.05, 0.0, 0.05, 0.10])
        fat = pd.Series([-0.50, -0.01, 0.0, 0.01, 0.50])
        assert cx.kurtosis(fat) > cx.kurtosis(normalish)

    def test_zero_variance_is_nan(self) -> None:
        assert math.isnan(cx.kurtosis(pd.Series([0.01] * 5)))

    def test_unbiased_needs_four_observations(self) -> None:
        with pytest.raises(InsufficientDataError, match="at least 4"):
            cx.kurtosis(pd.Series([0.1, 0.2, 0.3]), bias=False)

    def test_unbiased_pearson_is_unbiased_fisher_plus_three(self) -> None:
        returns = pd.Series([-0.10, 0.0, 0.0, 0.10, 0.05, -0.05])
        assert cx.kurtosis(returns, fisher=False, bias=False) == pytest.approx(
            cx.kurtosis(returns, fisher=True, bias=False) + 3.0, rel=1e-12
        )


class TestTrackingError:
    def test_zero_against_itself(self) -> None:
        index = pd.date_range("2024-01-31", periods=12, freq="ME")
        returns = pd.Series([0.01, 0.02, -0.01] * 4, index=index)
        assert cx.tracking_error(
            returns, returns, periods_per_year=12
        ) == pytest.approx(0.0, abs=1e-15)

    def test_equals_volatility_of_active_return(self) -> None:
        index = pd.date_range("2024-01-31", periods=12, freq="ME")
        returns = pd.Series([0.01, 0.02, -0.01] * 4, index=index)
        benchmark = pd.Series([0.005, 0.01, -0.005] * 4, index=index)
        active = returns - benchmark
        assert cx.tracking_error(
            returns, benchmark, periods_per_year=12
        ) == pytest.approx(cx.volatility(active, periods_per_year=12), rel=1e-12)

    def test_constant_offset_has_zero_tracking_error(self) -> None:
        """Tracking error measures variability of the gap, not its level."""
        index = pd.date_range("2024-01-31", periods=12, freq="ME")
        returns = pd.Series([0.01, 0.02, -0.01] * 4, index=index)
        assert cx.tracking_error(
            returns + 0.05, returns, periods_per_year=12
        ) == pytest.approx(0.0, abs=1e-12)

    def test_no_overlap_raises(self) -> None:
        a = pd.Series(
            [0.01] * 3, index=pd.date_range("2024-01-31", periods=3, freq="ME")
        )
        b = pd.Series(
            [0.01] * 3, index=pd.date_range("2030-01-31", periods=3, freq="ME")
        )
        with pytest.raises(NoOverlapError, match="share no common index"):
            cx.tracking_error(a, b, periods_per_year=12)

    def test_aligns_on_overlap_only(self) -> None:
        index = pd.date_range("2024-01-31", periods=12, freq="ME")
        returns = pd.Series([0.01] * 12, index=index)
        benchmark = pd.Series([0.005] * 6, index=index[:6])
        assert np.isfinite(cx.tracking_error(returns, benchmark, periods_per_year=12))
