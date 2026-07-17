"""Series alignment and point-in-time integrity.

The tests that matter most here are the look-ahead ones. Pandas will happily
broadcast a future value onto a past date, and a rate that leaks backwards
inflates every excess return computed from it -- silently, and in the direction
that makes results look better.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from convexity.alignment import DatetimeUnit, align_asof, align_series
from convexity.exceptions import (
    DataQualityError,
    IndexValidationError,
    NoOverlapError,
    StaleDataError,
)
from convexity.validation import NaNPolicy


class TestAlignSeries:
    def test_inner_join_on_common_dates(self) -> None:
        a = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2024-01-01", periods=3))
        b = pd.Series([4.0, 5.0, 6.0], index=pd.date_range("2024-01-02", periods=3))
        left, right = align_series(a, b)
        assert len(left) == len(right) == 2
        assert left.index.equals(right.index)

    def test_identical_indexes_unchanged(self) -> None:
        index = pd.date_range("2024-01-01", periods=3)
        a = pd.Series([1.0, 2.0, 3.0], index=index)
        left, _ = align_series(a, a)
        assert left.index.equals(index)

    def test_no_overlap_raises_rather_than_returning_empty(self) -> None:
        """An empty result makes every downstream metric a misleading nan."""
        a = pd.Series([1.0], index=pd.to_datetime(["2024-01-01"]))
        b = pd.Series([1.0], index=pd.to_datetime(["2030-01-01"]))
        with pytest.raises(NoOverlapError, match="share no common index"):
            align_series(a, b)

    def test_no_overlap_message_reports_both_spans(self) -> None:
        a = pd.Series([1.0], index=pd.to_datetime(["2024-01-01"]))
        b = pd.Series([1.0], index=pd.to_datetime(["2030-01-01"]))
        with pytest.raises(NoOverlapError, match="2030-01-01"):
            align_series(a, b)

    def test_no_value_is_borrowed_from_a_neighbour(self) -> None:
        """A gap removes the date; it does not forward-fill."""
        a = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2024-01-01", periods=3))
        b = pd.Series([4.0, 6.0], index=pd.to_datetime(["2024-01-01", "2024-01-03"]))
        left, right = align_series(a, b)
        assert len(left) == 2
        assert right.tolist() == [4.0, 6.0]

    def test_drop_policy_keeps_the_pair_synchronised(self) -> None:
        """Dropping each side independently would desynchronise them."""
        index = pd.date_range("2024-01-01", periods=4)
        a = pd.Series([1.0, float("nan"), 3.0, 4.0], index=index)
        b = pd.Series([1.0, 2.0, float("nan"), 4.0], index=index)
        left, right = align_series(a, b, nan_policy=NaNPolicy.DROP)
        assert left.index.equals(right.index)
        assert len(left) == 2

    def test_raise_policy_propagates(self) -> None:
        index = pd.date_range("2024-01-01", periods=2)
        a = pd.Series([1.0, float("nan")], index=index)
        b = pd.Series([1.0, 2.0], index=index)
        with pytest.raises(DataQualityError):
            align_series(a, b, nan_policy=NaNPolicy.RAISE)

    def test_inputs_not_mutated(self) -> None:
        index = pd.date_range("2024-01-01", periods=3)
        a = pd.Series([1.0, 2.0, 3.0], index=index)
        b = pd.Series([4.0, 5.0, 6.0], index=index)
        before_a, before_b = a.copy(deep=True), b.copy(deep=True)
        align_series(a, b)
        pd.testing.assert_series_equal(a, before_a)
        pd.testing.assert_series_equal(b, before_b)


class TestAlignAsof:
    def test_carries_the_most_recent_prior_observation_forward(self) -> None:
        rates = pd.Series(
            [0.05, 0.04], index=pd.to_datetime(["2024-01-01", "2024-02-01"])
        )
        targets = pd.to_datetime(["2024-01-15", "2024-02-15"])
        assert align_asof(targets, rates).tolist() == pytest.approx([0.05, 0.04])

    def test_target_before_any_observation_is_nan_not_backfilled(self) -> None:
        """An as-of join never looks forward, even to fill a leading gap."""
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        result = align_asof(pd.to_datetime(["2023-12-01", "2024-01-15"]), rates)
        assert bool(np.isnan(result.iloc[0]))
        assert result.iloc[1] == pytest.approx(0.05)

    def test_future_observation_never_informs_an_earlier_date(self) -> None:
        base = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        with_future = pd.Series(
            [0.05, 0.99], index=pd.to_datetime(["2024-01-01", "2024-06-01"])
        )
        targets = pd.to_datetime(["2024-02-01", "2024-03-01"])
        np.testing.assert_allclose(
            align_asof(targets, base).to_numpy(),
            align_asof(targets, with_future).to_numpy(),
        )

    def test_exact_date_match_uses_that_observation(self) -> None:
        rates = pd.Series(
            [0.05, 0.04], index=pd.to_datetime(["2024-01-01", "2024-02-01"])
        )
        result = align_asof(pd.to_datetime(["2024-02-01"]), rates)
        assert result.iloc[0] == pytest.approx(0.04)

    def test_result_carries_the_target_index(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        targets = pd.to_datetime(["2024-02-01", "2024-03-01"])
        assert align_asof(targets, rates).index.equals(targets)

    def test_no_prior_observation_at_all_raises(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2030-01-01"]))
        with pytest.raises(NoOverlapError, match="never looks forward"):
            align_asof(pd.to_datetime(["2024-01-01"]), rates)

    def test_unsorted_source_raises_rather_than_matching_arbitrarily(self) -> None:
        """An unordered source would make the backward match non-deterministic."""
        rates = pd.Series(
            [0.05, 0.04], index=pd.to_datetime(["2024-02-01", "2024-01-01"])
        )
        with pytest.raises(IndexValidationError, match="not monotonic increasing"):
            align_asof(pd.to_datetime(["2024-03-01"]), rates)

    @pytest.mark.parametrize("target_unit", ["s", "ms", "us", "ns"])
    @pytest.mark.parametrize("source_unit", ["s", "ms", "us", "ns"])
    def test_mixed_datetime_resolutions_align(
        self, target_unit: DatetimeUnit, source_unit: DatetimeUnit
    ) -> None:
        """merge_asof needs identical key dtypes; pandas does not guarantee one.

        Regression: a publication lag promoted the source index to nanoseconds
        while the target stayed at the pandas 3.0 microsecond default, and the
        merge raised MergeError on incompatible keys.
        """
        rates = pd.Series(
            [0.05], index=pd.DatetimeIndex(["2024-01-01"]).as_unit(source_unit)
        )
        targets = pd.DatetimeIndex(["2024-02-01"]).as_unit(target_unit)
        assert align_asof(targets, rates).iloc[0] == pytest.approx(0.05)

    def test_input_not_mutated(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        before = rates.copy(deep=True)
        align_asof(pd.to_datetime(["2024-02-01"]), rates)
        pd.testing.assert_series_equal(rates, before)


class TestStaleness:
    def test_within_limit_passes(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        result = align_asof(
            pd.to_datetime(["2024-01-05"]), rates, max_staleness=pd.Timedelta(days=7)
        )
        assert result.iloc[0] == pytest.approx(0.05)

    def test_beyond_limit_raises_rather_than_carrying_forever(self) -> None:
        """A rate from months ago must not silently stand in for today's."""
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        with pytest.raises(StaleDataError, match="exceeded the permitted staleness"):
            align_asof(
                pd.to_datetime(["2024-06-01"]),
                rates,
                max_staleness=pd.Timedelta(days=7),
            )

    def test_unbounded_by_default(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2020-01-01"]))
        result = align_asof(pd.to_datetime(["2024-06-01"]), rates)
        assert result.iloc[0] == pytest.approx(0.05)

    def test_message_reports_the_worst_age(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        with pytest.raises(StaleDataError, match="old"):
            align_asof(
                pd.to_datetime(["2024-06-01"]),
                rates,
                max_staleness=pd.Timedelta(days=7),
            )


class TestPublicationLag:
    def test_lag_delays_availability(self) -> None:
        """A figure stamped for a date is often not published until later.

        The 1 January observation carries a five-day lag, so it is unusable on
        3 January and usable by 10 January. Without the lag, 3 January would
        wrongly see it -- which is precisely the look-ahead this models away.
        """
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        targets = pd.to_datetime(["2024-01-03", "2024-01-10"])

        lagged = align_asof(targets, rates, publication_lag=pd.Timedelta(days=5))
        assert bool(np.isnan(lagged.iloc[0]))
        assert lagged.iloc[1] == pytest.approx(0.05)

        # Without a lag the same observation is visible on both dates.
        unlagged = align_asof(targets, rates)
        assert unlagged.iloc[0] == pytest.approx(0.05)

    def test_available_once_the_lag_elapses(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        result = align_asof(
            pd.to_datetime(["2024-01-10"]), rates, publication_lag=pd.Timedelta(days=5)
        )
        assert result.iloc[0] == pytest.approx(0.05)

    def test_zero_lag_matches_no_lag(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        targets = pd.to_datetime(["2024-01-10"])
        np.testing.assert_allclose(
            align_asof(targets, rates, publication_lag=pd.Timedelta(0)).to_numpy(),
            align_asof(targets, rates).to_numpy(),
        )

    def test_lag_can_remove_all_availability(self) -> None:
        rates = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
        with pytest.raises(NoOverlapError):
            align_asof(
                pd.to_datetime(["2024-01-02"]),
                rates,
                publication_lag=pd.Timedelta(days=365),
            )
