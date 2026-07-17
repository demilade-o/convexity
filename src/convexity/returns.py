"""Returns, wealth, and annualisation.

Conventions
-----------
Returns are decimals: ``0.01`` is 1%. Simple returns compound multiplicatively;
log returns compound additively. The two are never mixed silently -- every
function states which it expects.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from convexity.conventions import Annualisation, Frequency, resolve_annualisation
from convexity.exceptions import DataQualityError, InsufficientDataError
from convexity.validation import NaNPolicy, validate_datetime_index, validate_returns

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "annualised_return",
    "arithmetic_annualised_return",
    "cagr",
    "cumulative_return",
    "log_returns",
    "simple_returns",
    "to_log_returns",
    "to_simple_returns",
    "wealth_index",
]


def simple_returns(
    prices: pd.Series,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> pd.Series:
    r"""Compute simple (arithmetic) returns from a price series.

    .. math:: r_t = \frac{P_t}{P_{t-1}} - 1

    Parameters
    ----------
    prices
        Price levels. Must be strictly positive: a zero or negative price makes
        the ratio meaningless rather than merely extreme.
    nan_policy
        How to treat missing prices.

    Returns
    -------
    pandas.Series
        Returns with one fewer observation than ``prices``; the first date has no
        predecessor and is dropped rather than filled with zero.

    Raises
    ------
    DataQualityError
        If any price is non-positive.
    InsufficientDataError
        If fewer than two prices are supplied.

    Examples
    --------
    >>> import pandas as pd
    >>> simple_returns(pd.Series([100.0, 110.0, 99.0])).round(6).tolist()
    [0.1, -0.1]
    """
    series = _validate_prices(prices, nan_policy=nan_policy)
    return series.pct_change().iloc[1:]


def log_returns(
    prices: pd.Series,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> pd.Series:
    r"""Compute continuously compounded (log) returns from a price series.

    .. math:: r_t = \ln\left(\frac{P_t}{P_{t-1}}\right)

    Parameters
    ----------
    prices
        Strictly positive price levels.
    nan_policy
        How to treat missing prices.

    Returns
    -------
    pandas.Series
        Log returns, one fewer observation than ``prices``.

    Raises
    ------
    DataQualityError
        If any price is non-positive; the logarithm is undefined there.

    Examples
    --------
    >>> import pandas as pd
    >>> log_returns(pd.Series([100.0, 110.0])).round(8).tolist()
    [0.09531018]
    """
    series = _validate_prices(prices, nan_policy=nan_policy)
    return pd.Series(
        np.log(series.to_numpy()[1:] / series.to_numpy()[:-1]),
        index=series.index[1:],
        name=series.name,
    )


def to_log_returns(returns: pd.Series) -> pd.Series:
    r"""Convert simple returns to log returns.

    .. math:: r^{\log}_t = \ln(1 + r_t)

    Parameters
    ----------
    returns
        Simple returns, strictly above ``-1.0``.

    Returns
    -------
    pandas.Series
        Log returns.

    Raises
    ------
    DataQualityError
        If any return is at or below ``-1.0``, where the logarithm diverges.

    Examples
    --------
    >>> import pandas as pd
    >>> to_log_returns(pd.Series([0.1])).round(8).tolist()
    [0.09531018]
    """
    series = validate_returns(returns, allow_total_loss=False)
    return pd.Series(np.log1p(series.to_numpy()), index=series.index, name=series.name)


def to_simple_returns(log_rets: pd.Series) -> pd.Series:
    r"""Convert log returns to simple returns.

    .. math:: r_t = e^{r^{\log}_t} - 1

    Parameters
    ----------
    log_rets
        Log returns.

    Returns
    -------
    pandas.Series
        Simple returns.

    Examples
    --------
    >>> import pandas as pd
    >>> to_simple_returns(pd.Series([0.09531018])).round(6).tolist()
    [0.1]
    """
    series = pd.Series(log_rets).astype(float)
    return pd.Series(
        np.expm1(series.to_numpy()), index=series.index, name=series.name
    )


def wealth_index(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    initial: float = 1.0,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> pd.Series:
    r"""Compound simple returns into a wealth index.

    .. math:: W_t = W_0 \prod_{i=1}^{t}(1 + r_i)

    Parameters
    ----------
    returns
        Simple periodic returns.
    initial
        Starting wealth. Must be finite and positive.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    pandas.Series
        Wealth level at each observation. A return of exactly ``-1.0`` drives the
        index to zero and it remains zero thereafter -- correct behaviour, since
        wealth cannot recover from a total loss.

    Examples
    --------
    >>> import pandas as pd
    >>> wealth_index(pd.Series([0.1, -0.1])).round(6).tolist()
    [1.1, 0.99]
    """
    if not np.isfinite(initial) or initial <= 0:
        msg = f"initial wealth must be finite and positive, got {initial!r}."
        raise DataQualityError(msg)

    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    return initial * (1.0 + series).cumprod()


def cumulative_return(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Total compounded return over the whole sample.

    .. math:: R = \prod_{i=1}^{n}(1 + r_i) - 1

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Holding-period return as a decimal.

    Examples
    --------
    >>> import pandas as pd
    >>> round(cumulative_return(pd.Series([0.1, -0.1])), 10)
    -0.01
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    return float((1.0 + series).prod() - 1.0)


def annualised_return(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Geometric annualised return (CAGR) from periodic returns.

    .. math:: R_{ann} = \left(\prod_{i=1}^{n}(1 + r_i)\right)^{m/n} - 1

    where :math:`m` is ``periods_per_year`` and :math:`n` the observation count.
    This compounds; it is not the arithmetic mean scaled by :math:`m`. See
    :func:`arithmetic_annualised_return` for that, and note the two differ by
    roughly half the variance.

    Parameters
    ----------
    returns
        Simple periodic returns.
    periods_per_year
        Explicit annualisation factor; takes precedence over ``frequency`` and
        over inference from the index.
    frequency
        Explicit frequency. Used when ``periods_per_year`` is not given.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Annualised return as a decimal. Returns ``-1.0`` when terminal wealth is
        zero (a total loss annualises to -100%, exactly).

    Raises
    ------
    FrequencyInferenceError
        If no annualisation factor can be resolved. Never assumes 252.

    Examples
    --------
    Twelve monthly returns of 1% compound to 12.68% a year:

    >>> import pandas as pd
    >>> r = pd.Series([0.01] * 12)
    >>> round(annualised_return(r, periods_per_year=12), 6)
    0.126825
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    ann = _resolve(series, periods_per_year, frequency)

    growth = float((1.0 + series).prod())
    n = len(series)

    if growth <= 0.0:
        # A total loss (or worse) annualises to -100%; the fractional power of a
        # non-positive number is not real, so this is handled explicitly.
        return -1.0

    return float(growth ** (ann.periods_per_year / n) - 1.0)


def cagr(
    returns: pd.Series,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Compound annual growth rate using actual elapsed calendar time.

    .. math:: \text{CAGR} = W_T^{365.25 / \Delta} - 1

    where :math:`\Delta` is the actual number of days between the first and last
    observation. Unlike :func:`annualised_return` this needs no periods-per-year
    convention: it measures elapsed time directly, so it is the honest choice for
    irregularly spaced observations.

    Parameters
    ----------
    returns
        Simple periodic returns with a ``DatetimeIndex``.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Annualised growth rate as a decimal.

    Raises
    ------
    IndexValidationError
        If the index is not a valid ``DatetimeIndex``.
    InsufficientDataError
        If the observations span zero days, where a growth rate is undefined.

    Notes
    -----
    The 365.25-day year accounts for leap years over long horizons.

    Examples
    --------
    >>> import pandas as pd
    >>> idx = pd.to_datetime(["2023-01-01", "2024-01-01"])
    >>> round(cagr(pd.Series([0.0, 0.10], index=idx)), 6)
    0.100072
    """
    series = validate_returns(
        returns, nan_policy=nan_policy, min_observations=2, require_datetime_index=True
    )
    index = validate_datetime_index(series.index)

    elapsed_days = (index[-1] - index[0]).total_seconds() / 86_400.0
    if elapsed_days <= 0:
        msg = (
            "CAGR requires a positive elapsed period between the first and last "
            "observation; the supplied index spans zero days."
        )
        raise InsufficientDataError(msg)

    growth = float((1.0 + series).prod())
    if growth <= 0.0:
        return -1.0

    return float(growth ** (365.25 / elapsed_days) - 1.0)


def arithmetic_annualised_return(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Arithmetic mean return scaled to a year.

    .. math:: R_{arith} = m \cdot \bar{r}

    This is *not* the return an investor earns; it exceeds the geometric
    annualised return by approximately half the variance. It is reported because
    several risk-adjusted ratios are defined on arithmetic means, and mixing the
    two conventions silently is a common source of inflated figures.

    Parameters
    ----------
    returns
        Simple periodic returns.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Annualised arithmetic mean return as a decimal.

    Examples
    --------
    >>> import pandas as pd
    >>> round(arithmetic_annualised_return(pd.Series([0.01] * 12), periods_per_year=12), 6)
    0.12
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    ann = _resolve(series, periods_per_year, frequency)
    return float(series.mean() * ann.periods_per_year)


def _validate_prices(prices: pd.Series, *, nan_policy: NaNPolicy) -> pd.Series:
    series = pd.Series(prices).astype(float).copy()

    if len(series) < 2:
        msg = (
            f"At least 2 prices are required to compute a return, got {len(series)}."
        )
        raise InsufficientDataError(msg)

    from convexity.validation import apply_nan_policy

    series = apply_nan_policy(series, nan_policy, name="prices")

    finite = series.dropna().to_numpy()
    if finite.size and bool((finite <= 0).any()):
        msg = (
            "prices contains non-positive value(s); returns and logarithms are "
            "undefined there. Check for zero-filled gaps or sentinel values."
        )
        raise DataQualityError(msg)

    return series


def _resolve(
    series: pd.Series,
    periods_per_year: float | None,
    frequency: Frequency | None,
) -> Annualisation:
    index = series.index if isinstance(series.index, pd.DatetimeIndex) else None
    return resolve_annualisation(
        periods_per_year=periods_per_year, frequency=frequency, index=index
    )
