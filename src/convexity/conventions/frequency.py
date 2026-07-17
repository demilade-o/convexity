"""Observation frequency and annualisation.

Annualisation is a *convention*, never an inference the library makes quietly.
Three routes exist, in strict precedence order:

1. ``periods_per_year`` supplied by the caller wins outright.
2. An explicit :class:`Frequency` supplies its documented periods-per-year.
3. Inference from a :class:`~pandas.DatetimeIndex`, which is conservative,
   isolated, testable, and returns a confidence score plus diagnostics.

If none of the three yields an answer, a
:class:`~convexity.exceptions.FrequencyInferenceError` is raised. The library
does not fall back to 252.

References
----------
The 252-observation business-daily convention reflects the approximate number of
trading days in a year for major exchanges; it is a convention rather than a
derived constant, so it is stated explicitly here and in every result's metadata.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Final

import numpy as np
import pandas as pd

from convexity.exceptions import FrequencyInferenceError, IndexValidationError

if TYPE_CHECKING:
    from collections.abc import Mapping

__all__ = [
    "Annualisation",
    "Frequency",
    "FrequencyInference",
    "infer_frequency",
    "resolve_annualisation",
]


class Frequency(enum.Enum):
    """Supported observation frequencies and their annualisation factors."""

    BUSINESS_DAILY = "business_daily"
    CALENDAR_DAILY = "calendar_daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"

    @property
    def periods_per_year(self) -> float:
        """Observations per year implied by this frequency."""
        return _PERIODS_PER_YEAR[self]


_PERIODS_PER_YEAR: Final[dict[Frequency, float]] = {
    Frequency.BUSINESS_DAILY: 252.0,
    Frequency.CALENDAR_DAILY: 365.0,
    Frequency.WEEKLY: 52.0,
    Frequency.MONTHLY: 12.0,
    Frequency.QUARTERLY: 4.0,
    Frequency.ANNUAL: 1.0,
}

# Median spacing in calendar days -> candidate frequency. Bands are deliberately
# tight; anything outside them is reported as uninferable rather than rounded.
_SPACING_BANDS: Final[tuple[tuple[float, float, Frequency], ...]] = (
    (0.5, 1.5, Frequency.CALENDAR_DAILY),  # refined to BUSINESS_DAILY below
    (6.0, 8.0, Frequency.WEEKLY),
    (27.0, 32.0, Frequency.MONTHLY),
    (88.0, 93.0, Frequency.QUARTERLY),
    (360.0, 370.0, Frequency.ANNUAL),
)

#: Inference below this confidence will not silently produce an annualisation.
MIN_CONFIDENCE: Final[float] = 0.80


@dataclass(frozen=True, slots=True)
class FrequencyInference:
    """Outcome of inspecting an index, including why the library thinks so.

    Attributes
    ----------
    frequency
        Best candidate, or ``None`` when the index supports no confident answer.
    confidence
        Fraction of observed gaps consistent with ``frequency``, in ``[0, 1]``.
    diagnostics
        Human-readable evidence: median spacing, gap distribution, weekend share.
    """

    frequency: Frequency | None
    confidence: float
    diagnostics: Mapping[str, Any] = field(default_factory=dict)

    @property
    def is_confident(self) -> bool:
        """Whether the inference clears :data:`MIN_CONFIDENCE`."""
        return self.frequency is not None and self.confidence >= MIN_CONFIDENCE


@dataclass(frozen=True, slots=True)
class Annualisation:
    """A resolved annualisation factor and the provenance of that choice.

    ``source`` is one of ``"explicit"``, ``"frequency"``, or ``"inferred"`` and is
    surfaced in result metadata so a reader can always tell whether a number was
    annualised on the caller's authority or the library's inference.
    """

    periods_per_year: float
    source: str
    frequency: Frequency | None = None
    confidence: float | None = None

    def __post_init__(self) -> None:
        if not np.isfinite(self.periods_per_year) or self.periods_per_year <= 0:
            msg = (
                f"periods_per_year must be finite and positive, "
                f"got {self.periods_per_year!r}."
            )
            raise FrequencyInferenceError(msg)


def infer_frequency(index: pd.Index) -> FrequencyInference:
    """Infer observation frequency from a :class:`~pandas.DatetimeIndex`.

    The index must be monotonic increasing and free of duplicates; validate it
    with :func:`convexity.validation.validate_datetime_index` first.

    Parameters
    ----------
    index
        Index to inspect. Accepts any :class:`~pandas.Index` so that callers
        without type checking still get a clear error rather than an attribute
        failure, but only a ``DatetimeIndex`` can be inferred from. At least
        three observations are required to see two gaps, which is the minimum
        evidence for a regularity claim.

    Returns
    -------
    FrequencyInference
        Candidate frequency with confidence and diagnostics. Never raises for an
        unrecognisable-but-valid index; returns ``frequency=None`` instead.

    Examples
    --------
    >>> import pandas as pd
    >>> idx = pd.date_range("2024-01-01", periods=60, freq="B")
    >>> infer_frequency(idx).frequency
    <Frequency.BUSINESS_DAILY: 'business_daily'>
    """
    if not isinstance(index, pd.DatetimeIndex):
        msg = f"Expected a DatetimeIndex, got {type(index).__name__}."
        raise IndexValidationError(msg)

    n = len(index)
    if n < 3:
        return FrequencyInference(
            frequency=None,
            confidence=0.0,
            diagnostics={"reason": "fewer than 3 observations", "n_observations": n},
        )

    # Derive gaps via Timedelta rather than the raw i8 view: the underlying
    # resolution is not fixed (pandas 3.0 no longer guarantees nanoseconds), so
    # a hardcoded divisor would silently scale every gap by a power of 1000.
    gaps_days = _gap_days(index)
    median_gap = float(np.median(gaps_days))

    candidate: Frequency | None = None
    for low, high, freq in _SPACING_BANDS:
        if low <= median_gap <= high:
            candidate = freq
            break

    weekend_share = float(np.mean(index.dayofweek >= 5))

    if candidate is None:
        return FrequencyInference(
            frequency=None,
            confidence=0.0,
            diagnostics={
                "reason": "median spacing matches no supported frequency band",
                "median_gap_days": median_gap,
                "n_observations": n,
            },
        )

    # Distinguish business daily from calendar daily by weekend presence rather
    # than by gap size: both have a ~1-day median gap.
    if candidate is Frequency.CALENDAR_DAILY and weekend_share < 0.05:
        candidate = Frequency.BUSINESS_DAILY

    if candidate is Frequency.BUSINESS_DAILY:
        # Business-daily data legitimately shows 3-day gaps across weekends.
        consistent = np.mean((gaps_days >= 0.5) & (gaps_days <= 4.5))
    else:
        low, high = _band_for(candidate)
        consistent = np.mean((gaps_days >= low) & (gaps_days <= high))

    return FrequencyInference(
        frequency=candidate,
        confidence=float(consistent),
        diagnostics={
            "median_gap_days": median_gap,
            "weekend_share": weekend_share,
            "n_observations": n,
            "min_gap_days": float(np.min(gaps_days)),
            "max_gap_days": float(np.max(gaps_days)),
        },
    )


def _gap_days(index: pd.DatetimeIndex) -> np.ndarray:
    """Return consecutive gaps in calendar days, independent of index resolution."""
    deltas = index[1:] - index[:-1]
    return np.asarray(deltas.total_seconds(), dtype=float) / 86_400.0


def _band_for(frequency: Frequency) -> tuple[float, float]:
    for low, high, freq in _SPACING_BANDS:
        if freq is frequency:
            return low, high
    # BUSINESS_DAILY shares the calendar-daily band and is handled by its caller.
    return 0.5, 1.5


def resolve_annualisation(
    *,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    index: pd.DatetimeIndex | None = None,
) -> Annualisation:
    """Resolve an annualisation factor under the documented precedence rules.

    Precedence is ``periods_per_year`` > ``frequency`` > inference from ``index``.

    Parameters
    ----------
    periods_per_year
        Explicit observations per year. Takes precedence over everything else.
    frequency
        Explicit frequency whose documented factor is used.
    index
        Index to infer from, used only when neither of the above is supplied.

    Returns
    -------
    Annualisation
        Resolved factor tagged with the route that produced it.

    Raises
    ------
    FrequencyInferenceError
        If no route yields an answer, or inference is below :data:`MIN_CONFIDENCE`.
        The library never defaults to a business-daily assumption.

    Examples
    --------
    >>> resolve_annualisation(periods_per_year=12).source
    'explicit'
    >>> resolve_annualisation(frequency=Frequency.MONTHLY).periods_per_year
    12.0
    """
    if periods_per_year is not None:
        return Annualisation(
            periods_per_year=float(periods_per_year),
            source="explicit",
            frequency=frequency,
        )

    if frequency is not None:
        return Annualisation(
            periods_per_year=frequency.periods_per_year,
            source="frequency",
            frequency=frequency,
        )

    if index is None:
        msg = (
            "Cannot annualise: supply periods_per_year, a Frequency, or a "
            "DatetimeIndex to infer from. This library does not assume a default."
        )
        raise FrequencyInferenceError(msg)

    inference = infer_frequency(index)
    if not inference.is_confident:
        msg = (
            f"Frequency inference was not confident enough to annualise "
            f"(candidate={inference.frequency}, confidence={inference.confidence:.3f}, "
            f"required>={MIN_CONFIDENCE}). Diagnostics: {dict(inference.diagnostics)}. "
            f"Pass periods_per_year explicitly to proceed."
        )
        raise FrequencyInferenceError(msg)

    assert inference.frequency is not None  # noqa: S101 - guarded by is_confident
    return Annualisation(
        periods_per_year=inference.frequency.periods_per_year,
        source="inferred",
        frequency=inference.frequency,
        confidence=inference.confidence,
    )
