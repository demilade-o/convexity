"""Explicit market and measurement conventions.

Nothing in this package infers a convention silently. Every function either
receives its convention from the caller or reports, with diagnostics, that it
cannot proceed.
"""

from __future__ import annotations

from convexity.conventions.compounding import (
    Compounding,
    annual_to_period_rate,
    period_to_annual_rate,
)
from convexity.conventions.daycount import DayCount, year_fraction, year_fraction_array
from convexity.conventions.frequency import (
    MIN_CONFIDENCE,
    Annualisation,
    Frequency,
    FrequencyInference,
    infer_frequency,
    resolve_annualisation,
)

__all__ = [
    "MIN_CONFIDENCE",
    "Annualisation",
    "Compounding",
    "DayCount",
    "Frequency",
    "FrequencyInference",
    "annual_to_period_rate",
    "infer_frequency",
    "period_to_annual_rate",
    "resolve_annualisation",
    "year_fraction",
    "year_fraction_array",
]
