"""Input validation and missing-data policy."""

from __future__ import annotations

import re

import numpy as np
import pandas as pd
import pytest

from convexity.exceptions import (
    DataQualityError,
    IndexValidationError,
    InsufficientDataError,
)
from convexity.validation import (
    NaNPolicy,
    apply_nan_policy,
    validate_datetime_index,
    validate_returns,
)


class TestValidateDatetimeIndex:
    def test_accepts_valid_index(self) -> None:
        index = pd.date_range("2024-01-01", periods=3)
        assert validate_datetime_index(index) is index

    def test_rejects_non_datetime_index(self) -> None:
        with pytest.raises(IndexValidationError, match="DatetimeIndex is required"):
            validate_datetime_index(pd.Index([1, 2, 3]))

    def test_rejects_duplicates_rather_than_dropping_them(self) -> None:
        """A repeated timestamp is ambiguous; only the caller knows what it means."""
        index = pd.to_datetime(["2024-01-01", "2024-01-01", "2024-01-02"])
        with pytest.raises(IndexValidationError, match="duplicated timestamp"):
            validate_datetime_index(index)

    def test_duplicate_message_names_the_offender(self) -> None:
        index = pd.to_datetime(["2024-01-01", "2024-01-01"])
        with pytest.raises(IndexValidationError, match="2024-01-01"):
            validate_datetime_index(index)

    def test_rejects_non_monotonic_rather_than_sorting(self) -> None:
        """Sorting could fabricate results if order carried meaning."""
        index = pd.to_datetime(["2024-01-03", "2024-01-01", "2024-01-02"])
        with pytest.raises(IndexValidationError, match="not monotonic increasing"):
            validate_datetime_index(index)

    def test_monotonic_check_can_be_disabled(self) -> None:
        index = pd.to_datetime(["2024-01-03", "2024-01-01"])
        assert validate_datetime_index(index, require_monotonic=False) is index

    def test_unique_check_can_be_disabled(self) -> None:
        index = pd.to_datetime(["2024-01-01", "2024-01-01"])
        assert validate_datetime_index(index, require_unique=False) is index


class TestValidateReturns:
    def test_passes_clean_series(self) -> None:
        result = validate_returns(pd.Series([0.01, -0.02, 0.03]))
        assert result.tolist() == pytest.approx([0.01, -0.02, 0.03])

    def test_accepts_list_and_ndarray(self) -> None:
        assert validate_returns([0.01, 0.02]).tolist() == pytest.approx([0.01, 0.02])
        assert validate_returns(np.array([0.01, 0.02])).tolist() == pytest.approx(
            [0.01, 0.02]
        )

    def test_returns_a_new_object(self) -> None:
        original = pd.Series([0.01, 0.02])
        result = validate_returns(original)
        result.iloc[0] = 99.0
        assert original.iloc[0] == 0.01

    def test_integer_series_cast_to_float(self) -> None:
        assert validate_returns(pd.Series([0, 1])).dtype == float

    def test_non_numeric_rejected(self) -> None:
        with pytest.raises(DataQualityError, match="must be numeric"):
            validate_returns(pd.Series(["a", "b"]))

    @pytest.mark.parametrize("bad", [float("inf"), float("-inf")])
    def test_infinities_always_rejected(self, bad: float) -> None:
        with pytest.raises(DataQualityError, match="infinite value"):
            validate_returns(pd.Series([0.01, bad]))

    def test_return_below_minus_one_rejected(self) -> None:
        with pytest.raises(DataQualityError, match=re.escape("below -1.0")):
            validate_returns(pd.Series([0.01, -1.5]))

    def test_error_names_the_worst_offender(self) -> None:
        with pytest.raises(DataQualityError, match="-2"):
            validate_returns(pd.Series([0.01, -2.0]))

    def test_total_loss_allowed_by_default(self) -> None:
        assert validate_returns(pd.Series([-1.0])).tolist() == [-1.0]

    def test_total_loss_rejected_when_disallowed(self) -> None:
        with pytest.raises(DataQualityError, match=re.escape("at or below -1.0")):
            validate_returns(pd.Series([-1.0]), allow_total_loss=False)

    def test_percentage_mistake_is_not_second_guessed(self) -> None:
        """5 means 500%, not 5%. The library cannot tell, so it does not guess."""
        assert validate_returns(pd.Series([5.0])).tolist() == [5.0]

    def test_min_observations_enforced(self) -> None:
        with pytest.raises(InsufficientDataError, match="at least 3"):
            validate_returns(pd.Series([0.01, 0.02]), min_observations=3)

    def test_min_observations_counts_after_dropping(self) -> None:
        series = pd.Series([0.01, float("nan"), 0.02])
        with pytest.raises(InsufficientDataError, match="at least 3"):
            validate_returns(series, min_observations=3, nan_policy=NaNPolicy.DROP)

    def test_empty_series_rejected(self) -> None:
        with pytest.raises(InsufficientDataError):
            validate_returns(pd.Series([], dtype=float), min_observations=1)

    def test_custom_name_appears_in_errors(self) -> None:
        with pytest.raises(DataQualityError, match="benchmark contains"):
            validate_returns(pd.Series([float("inf")]), name="benchmark")

    def test_datetime_index_required_when_requested(self) -> None:
        with pytest.raises(IndexValidationError):
            validate_returns(pd.Series([0.01, 0.02]), require_datetime_index=True)

    def test_datetime_index_accepted_when_valid(self) -> None:
        series = pd.Series([0.01, 0.02], index=pd.date_range("2024-01-01", periods=2))
        assert len(validate_returns(series, require_datetime_index=True)) == 2


class TestNaNPolicy:
    def test_raise_is_the_default(self) -> None:
        with pytest.raises(DataQualityError, match="missing value"):
            validate_returns(pd.Series([0.01, float("nan")]))

    def test_raise_message_locates_the_first_gap(self) -> None:
        with pytest.raises(DataQualityError, match="first at"):
            validate_returns(pd.Series([0.01, float("nan")]))

    def test_raise_message_suggests_alternatives(self) -> None:
        with pytest.raises(DataQualityError, match=re.escape("NaNPolicy.DROP")):
            validate_returns(pd.Series([0.01, float("nan")]))

    def test_drop_removes_missing(self) -> None:
        result = validate_returns(
            pd.Series([0.01, float("nan"), 0.02]), nan_policy=NaNPolicy.DROP
        )
        assert result.tolist() == pytest.approx([0.01, 0.02])

    def test_propagate_keeps_missing(self) -> None:
        result = validate_returns(
            pd.Series([0.01, float("nan")]), nan_policy=NaNPolicy.PROPAGATE
        )
        assert len(result) == 2
        assert bool(result.isna().iloc[1])

    def test_clean_series_unaffected_by_policy(self) -> None:
        series = pd.Series([0.01, 0.02])
        for policy in NaNPolicy:
            assert apply_nan_policy(series, policy).tolist() == pytest.approx(
                [0.01, 0.02]
            )

    def test_apply_policy_does_not_mutate(self) -> None:
        series = pd.Series([0.01, float("nan")])
        before = series.copy(deep=True)
        apply_nan_policy(series, NaNPolicy.DROP)
        pd.testing.assert_series_equal(series, before)

    def test_all_nan_under_drop_leaves_nothing(self) -> None:
        result = apply_nan_policy(pd.Series([float("nan")] * 3), NaNPolicy.DROP)
        assert len(result) == 0

    def test_all_nan_under_raise(self) -> None:
        with pytest.raises(DataQualityError, match="3 missing value"):
            validate_returns(pd.Series([float("nan")] * 3))

    def test_all_nan_under_drop_fails_min_observations(self) -> None:
        with pytest.raises(InsufficientDataError, match="0 usable"):
            validate_returns(pd.Series([float("nan")] * 3), nan_policy=NaNPolicy.DROP)

    def test_infinity_rejected_even_under_propagate(self) -> None:
        """Infinity is never a meaningful return, whatever the NaN policy."""
        with pytest.raises(DataQualityError, match="infinite"):
            validate_returns(
                pd.Series([0.01, float("inf")]), nan_policy=NaNPolicy.PROPAGATE
            )
