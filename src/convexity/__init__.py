"""Explicit, well-tested quantitative finance analytics.

``convexity`` computes performance, risk, and rate analytics with documented
formulas, explicit conventions, and honest failure modes.

Three properties define the library:

**Nothing is inferred silently.** Annualisation, compounding, day count, the
risk-free convention, and the missing-data policy are parameters. Where a
convention cannot be resolved, the library raises with diagnostics instead of
assuming one.

**Analytics never touch the network.** Importing this package or calling any
metric performs no I/O. Data retrieval lives behind explicit provider objects in
:mod:`convexity.data`, which are optional dependencies.

**Returns are decimals.** ``0.01`` is 1%, everywhere, without exception.

Examples
--------
>>> import pandas as pd
>>> import convexity as cx
>>> returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 3)
>>> round(cx.sortino_ratio(returns, periods_per_year=12), 4)
8.6603

This library is a research and analysis tool. It is not investment advice.
"""

from __future__ import annotations

import logging

from convexity import registry
from convexity._diagnostics import show_versions, versions
from convexity._version import __version__
from convexity.alignment import align_asof, align_series
from convexity.conventions import (
    Annualisation,
    Compounding,
    DayCount,
    Frequency,
    FrequencyInference,
    annual_to_period_rate,
    infer_frequency,
    period_to_annual_rate,
    resolve_annualisation,
    year_fraction,
)
from convexity.exceptions import (
    AlignmentError,
    ConventionError,
    ConvexityError,
    CurrencyMismatchError,
    DataQualityError,
    FrequencyInferenceError,
    IndexValidationError,
    InsufficientDataError,
    LookAheadError,
    NoOverlapError,
    ProviderError,
    ProviderResponseError,
    ProviderUnavailableError,
    RateLimitError,
    StaleDataError,
    UndefinedMetricError,
    ValidationError,
)
from convexity.performance import (
    calmar_ratio,
    rolling_calmar,
    rolling_sharpe,
    rolling_sortino,
    sharpe_ratio,
    sortino_ratio,
)
from convexity.returns import (
    annualised_return,
    arithmetic_annualised_return,
    cagr,
    cumulative_return,
    log_returns,
    simple_returns,
    to_log_returns,
    to_simple_returns,
    wealth_index,
)
from convexity.risk import (
    DownsideConvention,
    DrawdownEpisode,
    average_drawdown,
    downside_deviation,
    drawdown_episodes,
    drawdown_series,
    kurtosis,
    max_drawdown,
    pain_index,
    skewness,
    tracking_error,
    ulcer_index,
    upside_deviation,
    volatility,
)
from convexity.validation import NaNPolicy

# A library must never configure the application's logging. NullHandler keeps
# "No handlers could be found" warnings away without imposing any policy.
logging.getLogger(__name__).addHandler(logging.NullHandler())

__all__ = [
    "AlignmentError",
    "Annualisation",
    "Compounding",
    "ConventionError",
    "ConvexityError",
    "CurrencyMismatchError",
    "DataQualityError",
    "DayCount",
    "DownsideConvention",
    "DrawdownEpisode",
    "Frequency",
    "FrequencyInference",
    "FrequencyInferenceError",
    "IndexValidationError",
    "InsufficientDataError",
    "LookAheadError",
    "NaNPolicy",
    "NoOverlapError",
    "ProviderError",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "RateLimitError",
    "StaleDataError",
    "UndefinedMetricError",
    "ValidationError",
    "__version__",
    "align_asof",
    "align_series",
    "annual_to_period_rate",
    "annualised_return",
    "arithmetic_annualised_return",
    "average_drawdown",
    "cagr",
    "calmar_ratio",
    "cumulative_return",
    "downside_deviation",
    "drawdown_episodes",
    "drawdown_series",
    "infer_frequency",
    "kurtosis",
    "log_returns",
    "max_drawdown",
    "pain_index",
    "period_to_annual_rate",
    "registry",
    "resolve_annualisation",
    "rolling_calmar",
    "rolling_sharpe",
    "rolling_sortino",
    "sharpe_ratio",
    "show_versions",
    "simple_returns",
    "skewness",
    "sortino_ratio",
    "to_log_returns",
    "to_simple_returns",
    "tracking_error",
    "ulcer_index",
    "upside_deviation",
    "versions",
    "volatility",
    "wealth_index",
    "year_fraction",
]
