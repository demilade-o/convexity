"""Compounding conventions and rate conversions.

A quoted annual rate is not a period return. Converting between them requires a
declared compounding convention, and getting this wrong is one of the most common
sources of silently incorrect risk-adjusted performance figures -- treating a 5%
annual bill yield as a 5% daily return inflates a Sharpe ratio beyond recognition.

Every conversion here is explicit about its convention and every pair of
conversions round-trips to within floating-point tolerance.
"""

from __future__ import annotations

import enum

import numpy as np

from convexity.exceptions import ConventionError

__all__ = [
    "Compounding",
    "annual_to_period_rate",
    "period_to_annual_rate",
]


class Compounding(enum.Enum):
    """How an annual rate accumulates into a period rate.

    Attributes
    ----------
    SIMPLE
        Pro-rata, no interest on interest: ``r_period = r_annual / m``.
        The money-market convention; correct for overnight and bill quotes.
    COMPOUNDED
        Geometric: ``r_period = (1 + r_annual)**(1/m) - 1``. Correct when the
        annual figure is an effective annual rate (EAR/APY).
    CONTINUOUS
        ``r_period = exp(r_annual / m) - 1``. Common in derivatives pricing.
    """

    SIMPLE = "simple"
    COMPOUNDED = "compounded"
    CONTINUOUS = "continuous"


def annual_to_period_rate(
    annual_rate: float | np.ndarray,
    periods_per_year: float,
    compounding: Compounding = Compounding.SIMPLE,
) -> float | np.ndarray:
    """Convert an annual rate to the return earned over one period.

    Parameters
    ----------
    annual_rate
        Annualised rate as a decimal (``0.05`` is 5%, never ``5``).
    periods_per_year
        Number of periods per year; must be finite and positive.
    compounding
        Convention to apply. Defaults to :attr:`Compounding.SIMPLE`, which matches
        how money-market rates such as Treasury bills and the euro short-term rate
        are quoted.

    Returns
    -------
    float or numpy.ndarray
        Period rate as a decimal, matching the shape of ``annual_rate``.

    Raises
    ------
    ConventionError
        If ``periods_per_year`` is not finite and positive, or if
        :attr:`Compounding.COMPOUNDED` is requested for a rate at or below
        ``-100%``, where the geometric root is not real.

    Examples
    --------
    A 5% annual rate over 252 business days, quoted simple:

    >>> round(annual_to_period_rate(0.05, 252), 10)
    0.0001984127

    The same rate treated as an effective annual rate compounds to slightly less,
    because compounding the period rate must recover exactly 5%:

    >>> round(annual_to_period_rate(0.05, 252, Compounding.COMPOUNDED), 10)
    0.0001936305
    """
    _check_periods_per_year(periods_per_year)
    rate = np.asarray(annual_rate, dtype=float)

    match compounding:
        case Compounding.SIMPLE:
            result = rate / periods_per_year
        case Compounding.COMPOUNDED:
            if bool(np.any(rate <= -1.0)):
                msg = (
                    "COMPOUNDED conversion requires annual_rate > -1.0; a rate at or "
                    "below -100% has no real geometric root. Use SIMPLE compounding "
                    "if the quote is a money-market rate."
                )
                raise ConventionError(msg)
            result = np.power(1.0 + rate, 1.0 / periods_per_year) - 1.0
        case Compounding.CONTINUOUS:
            result = np.expm1(rate / periods_per_year)

    return float(result) if np.isscalar(annual_rate) or result.ndim == 0 else result


def period_to_annual_rate(
    period_rate: float | np.ndarray,
    periods_per_year: float,
    compounding: Compounding = Compounding.SIMPLE,
) -> float | np.ndarray:
    """Convert a period rate back to an annual rate.

    Exact inverse of :func:`annual_to_period_rate` under the same convention.

    Parameters
    ----------
    period_rate
        Rate earned over one period, as a decimal.
    periods_per_year
        Number of periods per year; must be finite and positive.
    compounding
        Convention to apply.

    Returns
    -------
    float or numpy.ndarray
        Annualised rate as a decimal.

    Raises
    ------
    ConventionError
        If ``periods_per_year`` is invalid, or the conversion is not real-valued.

    Examples
    --------
    >>> round(period_to_annual_rate(0.0001984127, 252), 6)
    0.05
    """
    _check_periods_per_year(periods_per_year)
    rate = np.asarray(period_rate, dtype=float)

    match compounding:
        case Compounding.SIMPLE:
            result = rate * periods_per_year
        case Compounding.COMPOUNDED:
            if bool(np.any(rate <= -1.0)):
                msg = (
                    "COMPOUNDED conversion requires period_rate > -1.0; a period rate "
                    "at or below -100% cannot be compounded to an annual figure."
                )
                raise ConventionError(msg)
            result = np.power(1.0 + rate, periods_per_year) - 1.0
        case Compounding.CONTINUOUS:
            result = np.log1p(rate) * periods_per_year

    return float(result) if np.isscalar(period_rate) or result.ndim == 0 else result


def _check_periods_per_year(periods_per_year: float) -> None:
    if not np.isfinite(periods_per_year) or periods_per_year <= 0:
        msg = f"periods_per_year must be finite and positive, got {periods_per_year!r}."
        raise ConventionError(msg)
