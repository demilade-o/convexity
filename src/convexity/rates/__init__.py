"""Risk-free-rate subsystem.

A risk-free rate is both data and convention. Passing an unexplained ``0.05``
into a Sharpe ratio hides five decisions -- the currency, the tenor, the quote
date, the compounding, the day count, and whether the figure was even current on
the measurement date. This subsystem models those decisions explicitly.

Nothing here touches the network. These are value objects: a provider (see
:mod:`convexity.data`) retrieves the numbers, and these types carry them with
their conventions and provenance intact so that a downstream metric knows exactly
what it was handed.

The four models mirror the four things a caller actually has:

- :class:`RateQuote` -- a single dated rate with its full convention.
- :class:`RiskFreeSeries` -- a history of such quotes, one convention throughout.
- :class:`ZeroCurve` -- a term structure for discounting and forward rates.
- :class:`RiskFreePolicy` -- the rules for turning any of the above into the
  per-period risk-free series a metric consumes, without look-ahead.
"""

from __future__ import annotations

from convexity.rates.models import (
    InterpolationMethod,
    RateInstrument,
    RateQuote,
    RiskFreePolicy,
    RiskFreeSeries,
    ZeroCurve,
)

__all__ = [
    "InterpolationMethod",
    "RateInstrument",
    "RateQuote",
    "RiskFreePolicy",
    "RiskFreeSeries",
    "ZeroCurve",
]
