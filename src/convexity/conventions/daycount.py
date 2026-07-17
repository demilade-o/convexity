"""Day-count conventions.

Scope
-----
This release ships the two money-market conventions the risk-free-rate subsystem
needs to interpret its own quotes: ACT/360 and ACT/365F. ACT/ACT ISDA, 30/360 US
and 30E/360 arrive alongside the fixed-income module that consumes them; see
``ROADMAP.md``. Nothing here silently stands in for those conventions -- a
convention that is not implemented is simply absent from :class:`DayCount`,
rather than approximated by a neighbouring one.

Why this matters for rates
--------------------------
The convention is part of the quote, not a detail. The euro short-term rate
(EUR STR) is quoted ACT/360, and US Treasury bill discount yields use an ACT/360
basis while the bond-equivalent yield uses ACT/365. Applying the wrong divisor
introduces an error of roughly 1.4% of the rate -- small enough to look plausible
and large enough to be wrong.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from convexity.exceptions import ConventionError

if TYPE_CHECKING:
    import datetime as dt

__all__ = ["DayCount", "year_fraction", "year_fraction_array"]


class DayCount(enum.Enum):
    """Day-count basis for converting a date interval to a year fraction.

    Attributes
    ----------
    ACT_360
        Actual days elapsed divided by 360. Money-market standard for USD, EUR
        and most floating-rate conventions.
    ACT_365F
        Actual days elapsed divided by a fixed 365, ignoring leap years. Used for
        GBP money markets and for bond-equivalent yield conversions.
    """

    ACT_360 = "ACT/360"
    ACT_365F = "ACT/365F"

    @property
    def denominator(self) -> float:
        """Fixed denominator applied to actual elapsed days."""
        return 360.0 if self is DayCount.ACT_360 else 365.0


def year_fraction(
    start: dt.date | pd.Timestamp,
    end: dt.date | pd.Timestamp,
    convention: DayCount = DayCount.ACT_360,
) -> float:
    """Return the year fraction between two dates under a day-count convention.

    Parameters
    ----------
    start
        Interval start (inclusive).
    end
        Interval end (exclusive). Must not precede ``start``.
    convention
        Day-count basis to apply.

    Returns
    -------
    float
        Year fraction. Zero when ``start == end``.

    Raises
    ------
    ConventionError
        If ``end`` precedes ``start``. Negative year fractions are never returned
        silently, as they usually indicate reversed arguments.

    Examples
    --------
    A 90-day interval under ACT/360 is exactly a quarter of a year:

    >>> import datetime as dt
    >>> start, end = dt.date(2024, 1, 1), dt.date(2024, 3, 31)
    >>> year_fraction(start, end, DayCount.ACT_360)
    0.25

    The same interval under ACT/365F is shorter, because the denominator is larger:

    >>> round(year_fraction(start, end, DayCount.ACT_365F), 10)
    0.2465753425

    ACT/365F ignores the leap day in its denominator, so a full leap year exceeds 1:

    >>> round(year_fraction(dt.date(2024, 1, 1), dt.date(2025, 1, 1),
    ...                     DayCount.ACT_365F), 10)
    1.002739726
    """
    start_ts = pd.Timestamp(start)
    end_ts = pd.Timestamp(end)

    if end_ts < start_ts:
        msg = (
            f"end ({end_ts.date()}) precedes start ({start_ts.date()}); "
            f"year_fraction does not return negative values. Check argument order."
        )
        raise ConventionError(msg)

    actual_days = float((end_ts.normalize() - start_ts.normalize()).days)
    return actual_days / convention.denominator


def year_fraction_array(
    start: pd.DatetimeIndex,
    end: pd.DatetimeIndex,
    convention: DayCount = DayCount.ACT_360,
) -> np.ndarray:
    """Vectorised :func:`year_fraction` over aligned date arrays.

    Parameters
    ----------
    start, end
        Equal-length indexes of interval bounds.
    convention
        Day-count basis to apply.

    Returns
    -------
    numpy.ndarray
        Year fractions, one per pair.

    Raises
    ------
    ConventionError
        If the inputs differ in length or any interval is negative.
    """
    if len(start) != len(end):
        msg = f"start and end must be equal length, got {len(start)} and {len(end)}."
        raise ConventionError(msg)

    # Use Timedelta arithmetic rather than the raw i8 view: the underlying
    # datetime resolution is not guaranteed across pandas versions, and a
    # hardcoded divisor would scale every interval by a power of 1000.
    deltas = end.normalize() - start.normalize()
    days = np.asarray(deltas.total_seconds(), dtype=float) / 86_400.0
    if bool(np.any(days < 0)):
        msg = "At least one interval has end before start; check argument order."
        raise ConventionError(msg)

    return np.asarray(days / convention.denominator, dtype=float)
