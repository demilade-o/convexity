"""Conventions: inference, annualisation precedence, compounding, day counts."""

from __future__ import annotations

import datetime as dt
import re

import numpy as np
import pandas as pd
import pytest

from convexity.conventions import (
    MIN_CONFIDENCE,
    Annualisation,
    Compounding,
    DayCount,
    Frequency,
    annual_to_period_rate,
    infer_frequency,
    period_to_annual_rate,
    resolve_annualisation,
    year_fraction,
)
from convexity.conventions.daycount import year_fraction_array
from convexity.exceptions import (
    ConventionError,
    FrequencyInferenceError,
    IndexValidationError,
)


class TestFrequencyEnum:
    @pytest.mark.parametrize(
        ("frequency", "expected"),
        [
            (Frequency.BUSINESS_DAILY, 252.0),
            (Frequency.CALENDAR_DAILY, 365.0),
            (Frequency.WEEKLY, 52.0),
            (Frequency.MONTHLY, 12.0),
            (Frequency.QUARTERLY, 4.0),
            (Frequency.ANNUAL, 1.0),
        ],
    )
    def test_documented_annualisation_factors(
        self, frequency: Frequency, expected: float
    ) -> None:
        assert frequency.periods_per_year == expected


class TestInference:
    @pytest.mark.parametrize(
        ("freq", "expected"),
        [
            ("B", Frequency.BUSINESS_DAILY),
            ("D", Frequency.CALENDAR_DAILY),
            ("W", Frequency.WEEKLY),
            ("ME", Frequency.MONTHLY),
            ("QE", Frequency.QUARTERLY),
            ("YE", Frequency.ANNUAL),
        ],
    )
    def test_recognises_regular_frequencies(
        self, freq: str, expected: Frequency
    ) -> None:
        index = pd.date_range("2020-01-01", periods=40, freq=freq)
        result = infer_frequency(index)
        assert result.frequency is expected
        assert result.confidence >= MIN_CONFIDENCE
        assert result.is_confident

    def test_business_daily_distinguished_from_calendar_daily(self) -> None:
        """Both have a ~1-day median gap; only weekend presence separates them."""
        business = infer_frequency(pd.date_range("2024-01-01", periods=60, freq="B"))
        calendar = infer_frequency(pd.date_range("2024-01-01", periods=60, freq="D"))
        assert business.frequency is Frequency.BUSINESS_DAILY
        assert calendar.frequency is Frequency.CALENDAR_DAILY
        assert business.diagnostics["weekend_share"] == 0.0
        assert calendar.diagnostics["weekend_share"] > 0.2

    def test_reports_evidence_not_just_a_verdict(self) -> None:
        result = infer_frequency(pd.date_range("2024-01-31", periods=24, freq="ME"))
        assert result.diagnostics["n_observations"] == 24
        assert 27.0 <= result.diagnostics["median_gap_days"] <= 32.0
        assert "min_gap_days" in result.diagnostics
        assert "max_gap_days" in result.diagnostics

    def test_too_few_observations_is_not_confident(self) -> None:
        result = infer_frequency(pd.date_range("2024-01-01", periods=2))
        assert result.frequency is None
        assert result.confidence == 0.0
        assert not result.is_confident
        assert "fewer than 3" in result.diagnostics["reason"]

    def test_unrecognisable_spacing_returns_none_rather_than_rounding(self) -> None:
        # 100-day gaps match no supported band; the nearest is quarterly (88-93).
        index = pd.to_datetime(["2024-01-01", "2024-04-10", "2024-07-19"])
        result = infer_frequency(index)
        assert result.frequency is None
        assert "matches no supported frequency band" in result.diagnostics["reason"]

    def test_irregular_data_has_low_confidence(self) -> None:
        index = pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-03-01", "2024-09-01"]
        )
        result = infer_frequency(index)
        assert not result.is_confident

    def test_non_datetime_index_raises(self) -> None:
        with pytest.raises(IndexValidationError, match="Expected a DatetimeIndex"):
            infer_frequency(pd.Index([1, 2, 3]))

    def test_resolution_independent(self) -> None:
        """Gaps must not depend on the index's underlying datetime unit.

        Regression: an earlier implementation divided the raw i8 view by a
        hardcoded nanosecond constant, which scaled every gap by 1/1000 once
        pandas began defaulting to microsecond resolution.
        """
        base = pd.date_range("2024-01-01", periods=30, freq="D")
        for unit in ("s", "ms", "us", "ns"):
            index = base.as_unit(unit)
            result = infer_frequency(index)
            assert result.frequency is Frequency.CALENDAR_DAILY, f"failed for {unit}"
            assert result.diagnostics["median_gap_days"] == pytest.approx(1.0)


class TestAnnualisationPrecedence:
    def test_explicit_periods_per_year_wins_over_everything(self) -> None:
        index = pd.date_range("2024-01-01", periods=60, freq="B")
        result = resolve_annualisation(
            periods_per_year=7.0, frequency=Frequency.MONTHLY, index=index
        )
        assert result.periods_per_year == 7.0
        assert result.source == "explicit"

    def test_frequency_wins_over_index(self) -> None:
        index = pd.date_range("2024-01-01", periods=60, freq="B")
        result = resolve_annualisation(frequency=Frequency.MONTHLY, index=index)
        assert result.periods_per_year == 12.0
        assert result.source == "frequency"

    def test_index_used_only_as_last_resort(self) -> None:
        index = pd.date_range("2024-01-01", periods=60, freq="B")
        result = resolve_annualisation(index=index)
        assert result.periods_per_year == 252.0
        assert result.source == "inferred"
        assert result.confidence == pytest.approx(1.0)

    def test_no_route_raises_and_does_not_assume_252(self) -> None:
        with pytest.raises(FrequencyInferenceError, match="does not assume a default"):
            resolve_annualisation()

    def test_low_confidence_inference_raises_with_diagnostics(self) -> None:
        index = pd.to_datetime(
            ["2024-01-01", "2024-01-02", "2024-01-03", "2024-06-01", "2025-01-01"]
        )
        with pytest.raises(FrequencyInferenceError) as excinfo:
            resolve_annualisation(index=index)
        message = str(excinfo.value)
        assert "confidence" in message
        assert "Pass periods_per_year explicitly" in message

    @pytest.mark.parametrize("bad", [0.0, -1.0, float("nan"), float("inf")])
    def test_invalid_periods_per_year_rejected(self, bad: float) -> None:
        with pytest.raises(FrequencyInferenceError, match="finite and positive"):
            Annualisation(periods_per_year=bad, source="explicit")


class TestCompounding:
    def test_simple_is_pro_rata(self) -> None:
        assert annual_to_period_rate(0.12, 12, Compounding.SIMPLE) == pytest.approx(
            0.01, rel=1e-15
        )

    def test_compounded_recovers_the_annual_rate_exactly(self) -> None:
        """The defining property: compounding the period rate m times gives back r."""
        period = annual_to_period_rate(0.05, 12, Compounding.COMPOUNDED)
        assert (1 + period) ** 12 - 1 == pytest.approx(0.05, rel=1e-12)

    def test_continuous_matches_exponential_definition(self) -> None:
        assert annual_to_period_rate(
            0.05, 252, Compounding.CONTINUOUS
        ) == pytest.approx(np.expm1(0.05 / 252), rel=1e-15)

    def test_conventions_are_ordered_continuous_gt_simple_gt_compounded(self) -> None:
        """For a positive rate the three conventions have a fixed ordering.

        CONTINUOUS is largest: exp(r/m) - 1 exceeds the linear r/m by the
        second-order term. COMPOUNDED is smallest: it must compound back to
        exactly r over m periods, so each period must contribute less than the
        pro-rata share. SIMPLE sits between them.

        The gap is the whole reason the convention is a parameter. Choosing
        wrongly here misstates every excess return built on it.
        """
        simple = annual_to_period_rate(0.05, 12, Compounding.SIMPLE)
        continuous = annual_to_period_rate(0.05, 12, Compounding.CONTINUOUS)
        compounded = annual_to_period_rate(0.05, 12, Compounding.COMPOUNDED)
        assert continuous > simple > compounded

    @pytest.mark.parametrize("compounding", list(Compounding))
    @pytest.mark.parametrize("rate", [0.05, 0.0, -0.005, 0.25])
    @pytest.mark.parametrize("ppy", [1.0, 4.0, 12.0, 252.0])
    def test_round_trip(
        self, compounding: Compounding, rate: float, ppy: float
    ) -> None:
        period = annual_to_period_rate(rate, ppy, compounding)
        assert period_to_annual_rate(period, ppy, compounding) == pytest.approx(
            rate, abs=1e-12
        )

    def test_array_input_returns_array(self) -> None:
        rates = np.array([0.01, 0.05, 0.10])
        result = annual_to_period_rate(rates, 12, Compounding.SIMPLE)
        assert isinstance(result, np.ndarray)
        np.testing.assert_allclose(result, rates / 12)

    def test_compounded_rejects_rate_at_or_below_minus_one(self) -> None:
        with pytest.raises(
            ConventionError, match=re.escape("requires annual_rate > -1.0")
        ):
            annual_to_period_rate(-1.0, 12, Compounding.COMPOUNDED)

    def test_compounded_inverse_rejects_period_rate_below_minus_one(self) -> None:
        with pytest.raises(
            ConventionError, match=re.escape("requires period_rate > -1.0")
        ):
            period_to_annual_rate(-1.5, 12, Compounding.COMPOUNDED)

    @pytest.mark.parametrize("bad", [0.0, -12.0, float("nan"), float("inf")])
    def test_invalid_periods_per_year_rejected(self, bad: float) -> None:
        with pytest.raises(ConventionError, match="finite and positive"):
            annual_to_period_rate(0.05, bad)
        with pytest.raises(ConventionError, match="finite and positive"):
            period_to_annual_rate(0.05, bad)


class TestDayCount:
    def test_act_360_reference_example(self) -> None:
        # 90 actual days / 360 == exactly a quarter.
        assert year_fraction(
            dt.date(2024, 1, 1), dt.date(2024, 3, 31), DayCount.ACT_360
        ) == pytest.approx(0.25, abs=1e-15)

    def test_act_365f_reference_example(self) -> None:
        assert year_fraction(
            dt.date(2024, 1, 1), dt.date(2024, 3, 31), DayCount.ACT_365F
        ) == pytest.approx(90 / 365, abs=1e-15)

    def test_leap_year_exceeds_one_under_act_365f(self) -> None:
        """2024 has 366 days; ACT/365F's denominator ignores the leap day."""
        assert year_fraction(
            dt.date(2024, 1, 1), dt.date(2025, 1, 1), DayCount.ACT_365F
        ) == pytest.approx(366 / 365, abs=1e-15)

    def test_leap_day_boundary_is_counted(self) -> None:
        assert year_fraction(
            dt.date(2024, 2, 28), dt.date(2024, 3, 1), DayCount.ACT_360
        ) == pytest.approx(2 / 360, abs=1e-15)
        # 2023 is not a leap year, so the same calendar span is one day shorter.
        assert year_fraction(
            dt.date(2023, 2, 28), dt.date(2023, 3, 1), DayCount.ACT_360
        ) == pytest.approx(1 / 360, abs=1e-15)

    def test_denominators(self) -> None:
        assert DayCount.ACT_360.denominator == 360.0
        assert DayCount.ACT_365F.denominator == 365.0

    def test_conventions_differ_by_exactly_the_denominator_ratio(self) -> None:
        start, end = dt.date(2024, 1, 1), dt.date(2024, 7, 1)
        ratio = year_fraction(start, end, DayCount.ACT_360) / year_fraction(
            start, end, DayCount.ACT_365F
        )
        assert ratio == pytest.approx(365 / 360, rel=1e-12)

    def test_zero_length_interval(self) -> None:
        assert year_fraction(dt.date(2024, 1, 1), dt.date(2024, 1, 1)) == 0.0

    def test_reversed_dates_raise_rather_than_return_negative(self) -> None:
        with pytest.raises(ConventionError, match="precedes start"):
            year_fraction(dt.date(2024, 3, 1), dt.date(2024, 1, 1))

    def test_accepts_timestamps(self) -> None:
        assert year_fraction(
            pd.Timestamp("2024-01-01"), pd.Timestamp("2024-03-31"), DayCount.ACT_360
        ) == pytest.approx(0.25, abs=1e-15)

    def test_intraday_times_normalised_to_dates(self) -> None:
        """Day count is a calendar-day convention; time of day must not leak in."""
        assert year_fraction(
            pd.Timestamp("2024-01-01 23:59"), pd.Timestamp("2024-03-31 00:01")
        ) == pytest.approx(0.25, abs=1e-15)


class TestDayCountArray:
    def test_matches_scalar_elementwise(self) -> None:
        starts = pd.DatetimeIndex(["2024-01-01", "2024-02-01", "2024-03-01"])
        ends = pd.DatetimeIndex(["2024-04-01", "2024-05-01", "2024-06-01"])
        result = year_fraction_array(starts, ends, DayCount.ACT_360)
        expected = [
            year_fraction(s, e, DayCount.ACT_360)
            for s, e in zip(starts, ends, strict=True)
        ]
        np.testing.assert_allclose(result, expected, atol=1e-15)

    def test_resolution_independent(self) -> None:
        starts = pd.DatetimeIndex(["2024-01-01"]).as_unit("s")
        ends = pd.DatetimeIndex(["2024-03-31"]).as_unit("s")
        np.testing.assert_allclose(
            year_fraction_array(starts, ends, DayCount.ACT_360), [0.25], atol=1e-15
        )

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ConventionError, match="equal length"):
            year_fraction_array(
                pd.DatetimeIndex(["2024-01-01"]),
                pd.DatetimeIndex(["2024-02-01", "2024-03-01"]),
            )

    def test_negative_interval_raises(self) -> None:
        with pytest.raises(ConventionError, match="end before start"):
            year_fraction_array(
                pd.DatetimeIndex(["2024-06-01"]), pd.DatetimeIndex(["2024-01-01"])
            )
