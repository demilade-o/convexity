"""Risk-adjusted performance ratios.

Every ratio here separates three things that are frequently conflated: the
annualisation convention, the risk-free or target convention, and the treatment
of a zero denominator. All three are parameters or documented policy, never
silent defaults.

Zero-denominator policy
-----------------------
These ratios return ``inf`` or ``nan`` rather than raising, because a series with
no downside is a legitimate sample rather than a caller error:

* denominator ``0`` and numerator ``> 0`` -> ``+inf``
* denominator ``0`` and numerator ``< 0`` -> ``-inf``
* denominator ``0`` and numerator ``0`` -> ``nan`` (genuinely indeterminate)

Callers who prefer an exception can test with :func:`math.isfinite`.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from convexity.alignment import align_asof
from convexity.conventions import Compounding, Frequency, annual_to_period_rate
from convexity.exceptions import NoOverlapError
from convexity.returns import annualised_return
from convexity.risk import (
    DownsideConvention,
    downside_deviation,
    exact_std,
    max_drawdown,
)
from convexity.validation import NaNPolicy, validate_returns

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "calmar_ratio",
    "rolling_calmar",
    "rolling_sharpe",
    "rolling_sortino",
    "sharpe_ratio",
    "sortino_ratio",
]

#: The classic Calmar ratio measures drawdown over a trailing 36 months.
CALMAR_CLASSIC_LOOKBACK_MONTHS: int = 36


def sharpe_ratio(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    risk_free: float | pd.Series = 0.0,
    risk_free_is_annual: bool = True,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    compounding: Compounding = Compounding.SIMPLE,
    ddof: int = 1,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Annualised Sharpe ratio.

    .. math::

        S = \frac{m \cdot \overline{(r_t - f_t)}}
                 {\sigma(r_t - f_t) \cdot \sqrt{m}}

    The excess return is computed per period and *then* annualised, so a
    time-varying risk-free series is handled correctly rather than being reduced
    to its mean.

    Parameters
    ----------
    returns
        Simple periodic returns.
    risk_free
        Risk-free rate. A scalar is an annual rate by default; a Series is
        aligned to ``returns`` with a backward as-of join, so no future rate
        informs a past date.
    risk_free_is_annual
        Whether ``risk_free`` is quoted annually and needs conversion to a period
        rate. Set ``False`` when supplying periodic risk-free *returns* directly.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    compounding
        Convention for converting an annual rate to a period rate.
    ddof
        Delta degrees of freedom for the excess-return standard deviation.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Annualised Sharpe ratio. See the module docstring for zero-denominator
        policy.

    Notes
    -----
    This is the arithmetic Sharpe ratio: the numerator is a mean excess return
    scaled by :math:`m`, not a geometric annualised excess. The two differ by
    roughly half the variance and the arithmetic form is the one Sharpe defined.

    Examples
    --------
    >>> import pandas as pd
    >>> r = pd.Series([0.01, 0.02, -0.01, 0.03] * 3)
    >>> round(sharpe_ratio(r, periods_per_year=12), 6)
    2.80306
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=2)
    ppy = _resolve_ppy(series, periods_per_year, frequency)
    target = _periodic_target(
        series, risk_free, risk_free_is_annual, ppy, compounding, name="risk_free"
    )

    excess = series.to_numpy() - target
    numerator = float(np.mean(excess)) * ppy
    denominator = exact_std(excess, ddof=ddof) * float(np.sqrt(ppy))
    return _safe_ratio(numerator, denominator)


def sortino_ratio(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    mar: float | pd.Series = 0.0,
    mar_is_annual: bool = True,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    compounding: Compounding = Compounding.SIMPLE,
    convention: DownsideConvention = DownsideConvention.FULL,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Annualised Sortino ratio.

    .. math::

        \text{Sortino} = \frac{m \cdot \overline{(r_t - \text{MAR}_t)}}
                              {\text{DD} \cdot \sqrt{m}}

    where :math:`\text{DD}` is the downside deviation about the same target. The
    denominator convention is explicit: see :class:`~convexity.risk.DownsideConvention`.

    Parameters
    ----------
    returns
        Simple periodic returns.
    mar
        Minimum acceptable return. A scalar is an annual figure by default; a
        Series is aligned with a backward as-of join for a time-varying target.
    mar_is_annual
        Whether ``mar`` is quoted annually. Set ``False`` to supply a per-period
        target directly.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    compounding
        Convention for converting an annual target to a period target.
    convention
        Downside-deviation denominator convention. Defaults to
        :attr:`~convexity.risk.DownsideConvention.FULL`, matching Sortino and
        Price (1994).
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Annualised Sortino ratio. Returns ``+inf`` when there is no downside and
        the mean excess is positive; ``nan`` when there is no downside and the
        mean excess is exactly zero.

    See Also
    --------
    convexity.risk.downside_deviation : The denominator, and its conventions.

    References
    ----------
    Sortino, F. A. and Price, L. N. (1994). "Performance Measurement in a Downside
    Risk Framework". *The Journal of Investing*, 3(3), 59-64.

    Examples
    --------
    >>> import pandas as pd
    >>> r = pd.Series([0.01, 0.02, -0.01, 0.03] * 3)
    >>> round(sortino_ratio(r, periods_per_year=12), 6)
    8.660254

    A series that never falls below its target has no downside deviation, so the
    ratio is unbounded rather than merely large:

    >>> sortino_ratio(pd.Series([0.01] * 12), mar=0.0, periods_per_year=12)
    inf
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    ppy = _resolve_ppy(series, periods_per_year, frequency)
    target = _periodic_target(series, mar, mar_is_annual, ppy, compounding, name="mar")

    excess = series.to_numpy() - target
    numerator = float(np.mean(excess)) * ppy

    dd = downside_deviation(
        series,
        mar=pd.Series(target, index=series.index),
        convention=convention,
        annualise=False,
        nan_policy=NaNPolicy.PROPAGATE,
    )
    denominator = dd * float(np.sqrt(ppy))
    return _safe_ratio(numerator, denominator)


def calmar_ratio(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    risk_free: float | pd.Series = 0.0,
    risk_free_is_annual: bool = True,
    lookback_periods: int | None = None,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    compounding: Compounding = Compounding.SIMPLE,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Calmar ratio: annualised excess return over maximum drawdown.

    .. math:: \text{Calmar} = \frac{R_{ann} - f_{ann}}{|\text{MDD}|}

    Parameters
    ----------
    returns
        Simple periodic returns.
    risk_free
        Risk-free rate, scalar (annual by default) or aligned Series. The
        classic Calmar definition uses a raw return with no risk-free deduction;
        that is the default here (``0.0``), and any non-zero value is the
        caller's explicit choice.
    risk_free_is_annual
        Whether ``risk_free`` is quoted annually.
    lookback_periods
        Restrict both the return and the drawdown to the trailing
        ``lookback_periods`` observations. The classic definition uses a trailing
        36 months; pass ``int(3 * periods_per_year)`` to reproduce it. ``None``
        (default) uses the full sample, which makes this the MAR ratio.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    compounding
        Convention for converting an annual rate to a period rate.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Calmar ratio. Returns ``+inf`` when the series never draws down and the
        annualised return is positive; ``nan`` when it never draws down and the
        return is exactly zero.

    Notes
    -----
    The numerator is a *geometric* annualised return, unlike Sharpe and Sortino
    which use arithmetic means. This follows the ratio's origin as a
    return-over-worst-loss measure for managed futures, where the compounded
    outcome is the quantity of interest.

    The lookback is applied before the drawdown is computed, so the maximum
    drawdown is the worst decline *within the window*, not an earlier decline
    that the window excludes.

    Examples
    --------
    >>> import pandas as pd
    >>> r = pd.Series([0.02] * 11 + [-0.05])
    >>> round(calmar_ratio(r, periods_per_year=12), 6)
    3.624112

    A series that never draws down has an unbounded Calmar ratio:

    >>> calmar_ratio(pd.Series([0.01] * 12), periods_per_year=12)
    inf
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)

    if lookback_periods is not None:
        if lookback_periods < 1:
            msg = f"lookback_periods must be >= 1, got {lookback_periods}."
            raise ValueError(msg)
        series = series.iloc[-lookback_periods:]

    ppy = _resolve_ppy(series, periods_per_year, frequency)
    target = _periodic_target(
        series, risk_free, risk_free_is_annual, ppy, compounding, name="risk_free"
    )

    gross = annualised_return(
        series, periods_per_year=ppy, nan_policy=NaNPolicy.PROPAGATE
    )
    # Deduct the risk-free leg on an annualised basis so the numerator is a true
    # annualised excess even when the rate varies through the window.
    risk_free_annual = float(np.mean(target)) * ppy
    numerator = gross - risk_free_annual

    mdd = max_drawdown(series, nan_policy=NaNPolicy.PROPAGATE)
    return _safe_ratio(numerator, abs(mdd))


def rolling_sharpe(
    returns: pd.Series,
    window: int,
    *,
    risk_free: float | pd.Series = 0.0,
    risk_free_is_annual: bool = True,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    min_periods: int | None = None,
) -> pd.Series:
    """Sharpe ratio computed over a rolling window.

    Parameters
    ----------
    returns
        Simple periodic returns.
    window
        Number of observations per window.
    risk_free
        Scalar (annual by default) or aligned Series.
    risk_free_is_annual
        Whether ``risk_free`` is quoted annually.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    min_periods
        Minimum observations before a value is produced. Defaults to ``window``,
        so no partially-populated window yields a number.

    Returns
    -------
    pandas.Series
        Rolling Sharpe ratio indexed like ``returns``, with ``nan`` before the
        first complete window.
    """
    return _rolling_apply(
        returns,
        window,
        min_periods,
        lambda w: sharpe_ratio(
            w,
            risk_free=_window_slice(risk_free, w),
            risk_free_is_annual=risk_free_is_annual,
            periods_per_year=periods_per_year,
            frequency=frequency,
            nan_policy=NaNPolicy.PROPAGATE,
        ),
    )


def rolling_sortino(
    returns: pd.Series,
    window: int,
    *,
    mar: float | pd.Series = 0.0,
    mar_is_annual: bool = True,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    convention: DownsideConvention = DownsideConvention.FULL,
    min_periods: int | None = None,
) -> pd.Series:
    """Sortino ratio computed over a rolling window.

    Parameters
    ----------
    returns
        Simple periodic returns.
    window
        Number of observations per window.
    mar
        Scalar (annual by default) or aligned Series target.
    mar_is_annual
        Whether ``mar`` is quoted annually.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    convention
        Downside-deviation denominator convention.
    min_periods
        Minimum observations before a value is produced. Defaults to ``window``.

    Returns
    -------
    pandas.Series
        Rolling Sortino ratio indexed like ``returns``.
    """
    return _rolling_apply(
        returns,
        window,
        min_periods,
        lambda w: sortino_ratio(
            w,
            mar=_window_slice(mar, w),
            mar_is_annual=mar_is_annual,
            periods_per_year=periods_per_year,
            frequency=frequency,
            convention=convention,
            nan_policy=NaNPolicy.PROPAGATE,
        ),
    )


def rolling_calmar(
    returns: pd.Series,
    window: int,
    *,
    risk_free: float | pd.Series = 0.0,
    risk_free_is_annual: bool = True,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    min_periods: int | None = None,
) -> pd.Series:
    """Calmar ratio computed over a rolling window.

    Parameters
    ----------
    returns
        Simple periodic returns.
    window
        Number of observations per window. This *is* the Calmar lookback.
    risk_free
        Scalar (annual by default) or aligned Series.
    risk_free_is_annual
        Whether ``risk_free`` is quoted annually.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    min_periods
        Minimum observations before a value is produced. Defaults to ``window``.

    Returns
    -------
    pandas.Series
        Rolling Calmar ratio indexed like ``returns``.
    """
    return _rolling_apply(
        returns,
        window,
        min_periods,
        lambda w: calmar_ratio(
            w,
            risk_free=_window_slice(risk_free, w),
            risk_free_is_annual=risk_free_is_annual,
            periods_per_year=periods_per_year,
            frequency=frequency,
            nan_policy=NaNPolicy.PROPAGATE,
        ),
    )


# --------------------------------------------------------------------------- #
# Internals
# --------------------------------------------------------------------------- #


def _safe_ratio(numerator: float, denominator: float) -> float:
    """Apply the documented zero-denominator policy."""
    if denominator > 0:
        return numerator / denominator
    if numerator > 0:
        return float("inf")
    if numerator < 0:
        return float("-inf")
    return float("nan")


def _resolve_ppy(
    series: pd.Series,
    periods_per_year: float | None,
    frequency: Frequency | None,
) -> float:
    from convexity.conventions import resolve_annualisation

    index = series.index if isinstance(series.index, pd.DatetimeIndex) else None
    return resolve_annualisation(
        periods_per_year=periods_per_year, frequency=frequency, index=index
    ).periods_per_year


def _periodic_target(
    series: pd.Series,
    value: float | pd.Series,
    is_annual: bool,
    periods_per_year: float,
    compounding: Compounding,
    *,
    name: str,
) -> np.ndarray:
    """Resolve a scalar or Series rate/target to a per-period array.

    A Series is aligned with a backward as-of join, never a plain index join, so
    a rate published after a measurement date cannot inform it.
    """
    if isinstance(value, pd.Series):
        if isinstance(series.index, pd.DatetimeIndex) and isinstance(
            value.index, pd.DatetimeIndex
        ):
            aligned = align_asof(series.index, value, name=name)
        else:
            common = series.index.intersection(value.index)
            if len(common) == 0:
                msg = (
                    f"{name} shares no index entries with returns and neither has a "
                    f"DatetimeIndex, so no as-of alignment is possible."
                )
                raise NoOverlapError(msg)
            aligned = value.reindex(series.index)
        raw = np.asarray(aligned.to_numpy(), dtype=float)
    else:
        raw = np.full(len(series), float(value), dtype=float)

    if not is_annual:
        return raw

    converted = annual_to_period_rate(raw, periods_per_year, compounding)
    return np.asarray(converted, dtype=float)


def _window_slice(value: float | pd.Series, window: pd.Series) -> float | pd.Series:
    """Pass a rate through to a rolling window unchanged.

    Deliberately does *not* reindex onto the window. A rate series is typically
    sparse relative to the returns it is measured against -- a handful of quotes
    covering months of observations -- so reindexing would replace every quote
    that does not land exactly on a window date with NaN. The as-of alignment in
    :func:`_periodic_target` selects the correct prior quote for each date in the
    window, and remains backward-looking, so passing the full series leaks no
    future information.
    """
    return value


def _rolling_apply(
    returns: pd.Series,
    window: int,
    min_periods: int | None,
    func: object,
) -> pd.Series:
    if window < 1:
        msg = f"window must be >= 1, got {window}."
        raise ValueError(msg)

    series = validate_returns(returns, nan_policy=NaNPolicy.PROPAGATE)
    effective_min = window if min_periods is None else min_periods

    values: list[float] = []
    for i in range(len(series)):
        start = max(0, i - window + 1)
        chunk = series.iloc[start : i + 1]
        if len(chunk) < effective_min or chunk.notna().sum() < 1:
            values.append(float("nan"))
            continue
        values.append(float(func(chunk)))  # type: ignore[operator]

    return pd.Series(values, index=series.index, name=series.name)
