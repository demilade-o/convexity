"""Dispersion, downside, and drawdown risk.

Every metric here states its convention. Where competing definitions exist in the
literature -- most consequentially for downside deviation -- the variants are
exposed as named parameters rather than resolved by fiat, and the default is
documented with its reason.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from convexity.conventions import Frequency, resolve_annualisation
from convexity.exceptions import InsufficientDataError
from convexity.returns import wealth_index
from convexity.validation import NaNPolicy, validate_returns

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "DownsideConvention",
    "DrawdownEpisode",
    "average_drawdown",
    "downside_deviation",
    "drawdown_episodes",
    "drawdown_series",
    "kurtosis",
    "max_drawdown",
    "pain_index",
    "skewness",
    "tracking_error",
    "ulcer_index",
    "upside_deviation",
    "volatility",
]


class DownsideConvention(enum.Enum):
    r"""Denominator convention for downside and upside deviation.

    This choice materially changes the number, and libraries disagree, so it is
    surfaced rather than assumed.

    Attributes
    ----------
    FULL
        Divide the sum of squared shortfalls by the *total* observation count
        :math:`n`. This is the second lower partial moment as defined by Sortino
        and Price (1994), and is the default here.
    DOWNSIDE_ONLY
        Divide by the count of observations below the target only. This measures
        the average severity of a bad period given that it was bad, which is a
        different quantity, and inflates the deviation whenever most periods are
        above target -- thereby deflating any Sortino ratio built on it.

    Notes
    -----
    The distinction is the single most common source of disagreement between
    Sortino implementations. A series with one bad month in twelve has a downside
    deviation roughly :math:`\\sqrt{12}` times larger under ``DOWNSIDE_ONLY``.

    References
    ----------
    Sortino, F. A. and Price, L. N. (1994). "Performance Measurement in a Downside
    Risk Framework". *The Journal of Investing*, 3(3), 59-64.
    """

    FULL = "full"
    DOWNSIDE_ONLY = "downside_only"


@dataclass(frozen=True, slots=True)
class DrawdownEpisode:
    """A single peak-to-trough-to-recovery drawdown episode.

    Attributes
    ----------
    start
        Date of the peak from which the decline began.
    trough
        Date of the lowest wealth in the episode.
    recovery
        Date wealth regained the prior peak, or ``None`` if never recovered
        within the sample. ``None`` is reported honestly rather than imputed.
    depth
        Maximum decline as a negative decimal (``-0.2`` is a 20% drawdown).
    length
        Observations from peak to recovery inclusive, or to the end of sample
        when unrecovered.
    time_to_recovery
        Observations from trough to recovery, or ``None`` if unrecovered.
    """

    start: pd.Timestamp
    trough: pd.Timestamp
    recovery: pd.Timestamp | None
    depth: float
    length: int
    time_to_recovery: int | None

    @property
    def is_recovered(self) -> bool:
        """Whether wealth regained its prior peak inside the sample."""
        return self.recovery is not None


def drawdown_series(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> pd.Series:
    r"""Underwater curve: decline from the running peak at each observation.

    .. math:: D_t = \frac{W_t}{\max_{s \le t} W_s} - 1

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    pandas.Series
        Drawdown at each date as a non-positive decimal. Zero means at-peak.

    Notes
    -----
    The running peak includes the starting wealth of 1.0, so a series that only
    ever loses money is underwater from its first observation.

    Examples
    --------
    >>> import pandas as pd
    >>> drawdown_series(pd.Series([0.1, -0.2, 0.05])).round(6).tolist()
    [0.0, -0.2, -0.16]
    """
    wealth = wealth_index(returns, nan_policy=nan_policy)
    # The peak must include initial wealth: a first-period loss is a real drawdown.
    running_peak = np.maximum.accumulate(np.maximum(wealth.to_numpy(), 1.0))
    return pd.Series(
        wealth.to_numpy() / running_peak - 1.0, index=wealth.index, name=wealth.name
    )


def max_drawdown(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Largest peak-to-trough decline over the sample.

    .. math:: \text{MDD} = \min_t D_t

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Maximum drawdown as a non-positive decimal. Exactly ``0.0`` when the
        series never falls below its starting wealth -- a real result, not a
        missing one.

    Examples
    --------
    >>> import pandas as pd
    >>> round(max_drawdown(pd.Series([0.1, -0.2, 0.05])), 10)
    -0.2
    >>> max_drawdown(pd.Series([0.01, 0.02]))
    0.0
    """
    return float(drawdown_series(returns, nan_policy=nan_policy).min())


def drawdown_episodes(
    returns: pd.Series,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> list[DrawdownEpisode]:
    """Identify every distinct drawdown episode with its dates and depth.

    An episode opens when wealth first falls below its running peak and closes
    when it regains that peak. An episode still open at the end of the sample is
    returned with ``recovery=None``.

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    list of DrawdownEpisode
        Episodes in chronological order; empty when the series never draws down.

    Examples
    --------
    >>> import pandas as pd
    >>> idx = pd.date_range("2024-01-31", periods=4, freq="ME")
    >>> eps = drawdown_episodes(pd.Series([0.1, -0.2, 0.3, 0.0], index=idx))
    >>> len(eps), round(eps[0].depth, 6), eps[0].is_recovered
    (1, -0.2, True)
    """
    dd = drawdown_series(returns, nan_policy=nan_policy)
    values = dd.to_numpy()
    index = dd.index

    episodes: list[DrawdownEpisode] = []
    in_episode = False
    start_pos = 0
    trough_pos = 0

    for i, value in enumerate(values):
        if not in_episode and value < 0:
            in_episode = True
            # The peak is the observation before the decline began; at i == 0 the
            # peak is the initial wealth, which has no index entry of its own.
            start_pos = max(i - 1, 0)
            trough_pos = i
        elif in_episode:
            if value < values[trough_pos]:
                trough_pos = i
            if value >= 0:
                episodes.append(
                    _build_episode(index, start_pos, trough_pos, i, values[trough_pos])
                )
                in_episode = False

    if in_episode:
        episodes.append(
            _build_episode(index, start_pos, trough_pos, None, values[trough_pos])
        )

    return episodes


def _build_episode(
    index: pd.Index,
    start_pos: int,
    trough_pos: int,
    recovery_pos: int | None,
    depth: float,
) -> DrawdownEpisode:
    end_pos = recovery_pos if recovery_pos is not None else len(index) - 1
    return DrawdownEpisode(
        start=index[start_pos],
        trough=index[trough_pos],
        recovery=index[recovery_pos] if recovery_pos is not None else None,
        depth=float(depth),
        length=end_pos - start_pos + 1,
        time_to_recovery=(
            recovery_pos - trough_pos if recovery_pos is not None else None
        ),
    )


def average_drawdown(
    returns: pd.Series,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    """Mean depth across distinct drawdown episodes.

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Mean episode depth as a non-positive decimal, or ``0.0`` when there are no
        episodes.

    Notes
    -----
    This averages over *episodes*, not over observations. Averaging the underwater
    curve instead gives the pain index -- see :func:`pain_index`.
    """
    episodes = drawdown_episodes(returns, nan_policy=nan_policy)
    if not episodes:
        return 0.0
    return float(np.mean([e.depth for e in episodes]))


def ulcer_index(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Quadratic mean of the underwater curve.

    .. math:: \text{UI} = \sqrt{\frac{1}{n}\sum_{t=1}^{n} D_t^2}

    Penalises deep drawdowns more than shallow ones, and long ones more than
    brief ones.

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Ulcer index as a non-negative decimal.

    References
    ----------
    Martin, P. and McCann, B. (1989). *The Investor's Guide to Fidelity Funds*.
    """
    dd = drawdown_series(returns, nan_policy=nan_policy)
    return float(np.sqrt(np.mean(np.square(dd.to_numpy()))))


def pain_index(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Mean depth of the underwater curve.

    .. math:: \text{PI} = \frac{1}{n}\sum_{t=1}^{n} |D_t|

    Parameters
    ----------
    returns
        Simple periodic returns.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Pain index as a non-negative decimal.
    """
    dd = drawdown_series(returns, nan_policy=nan_policy)
    return float(np.mean(np.abs(dd.to_numpy())))


def volatility(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    annualise: bool = True,
    ddof: int = 1,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Compute the standard deviation of returns, optionally annualised.

    .. math:: \sigma_{ann} = \sigma_{period} \cdot \sqrt{m}

    Parameters
    ----------
    returns
        Simple periodic returns.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    annualise
        Apply the square-root-of-time scaling. Required only when annualising.
    ddof
        Delta degrees of freedom. ``1`` (sample standard deviation) is the
        default; pass ``0`` for the population figure.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Volatility as a decimal.

    Raises
    ------
    InsufficientDataError
        If fewer than ``ddof + 1`` observations are supplied.

    Notes
    -----
    Square-root-of-time scaling assumes returns are serially uncorrelated and
    identically distributed. Real return series usually violate both, so an
    annualised volatility is a convention, not a measurement. It is applied only
    when explicitly requested via ``annualise``.

    Examples
    --------
    >>> import pandas as pd
    >>> r = pd.Series([0.01, -0.01, 0.02, -0.02])
    >>> round(volatility(r, periods_per_year=12, annualise=False), 8)
    0.01825742
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=ddof + 1)

    if len(series) <= ddof:
        msg = (
            f"volatility with ddof={ddof} requires more than {ddof} observation(s), "
            f"got {len(series)}."
        )
        raise InsufficientDataError(msg)

    sigma = float(np.std(series.to_numpy(), ddof=ddof))
    if not annualise:
        return sigma

    ann = resolve_annualisation(
        periods_per_year=periods_per_year,
        frequency=frequency,
        index=series.index if isinstance(series.index, pd.DatetimeIndex) else None,
    )
    return sigma * float(np.sqrt(ann.periods_per_year))


def downside_deviation(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    mar: float | pd.Series = 0.0,
    convention: DownsideConvention = DownsideConvention.FULL,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    annualise: bool = False,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Root of the second lower partial moment about a minimum acceptable return.

    .. math::
        \text{DD} = \sqrt{\frac{1}{n}\sum_{t=1}^{n}
                          \left[\min(r_t - \text{MAR}, 0)\right]^2}

    Under :attr:`DownsideConvention.FULL` (the default) the denominator is the
    total observation count :math:`n`, matching Sortino and Price (1994).

    Parameters
    ----------
    returns
        Simple periodic returns.
    mar
        Minimum acceptable return **per period**, as a decimal. Accepts a scalar
        or a Series aligned to ``returns`` for a time-varying target. It is not
        an annual figure: convert first with
        :func:`convexity.conventions.annual_to_period_rate`.
    convention
        Denominator convention. See :class:`DownsideConvention`.
    periods_per_year
        Explicit annualisation factor, required when ``annualise`` is set.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    annualise
        Apply square-root-of-time scaling.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Downside deviation as a non-negative decimal. Exactly ``0.0`` when no
        observation falls below the target -- a true statement about the sample,
        not a missing value.

    Examples
    --------
    One month at -3% against a 0% target, in a twelve-month sample:

    >>> import pandas as pd
    >>> r = pd.Series([0.01] * 11 + [-0.03])
    >>> round(downside_deviation(r), 8)
    0.00866025

    The same series under the downside-only convention is much larger, because
    the denominator falls from 12 to 1:

    >>> round(downside_deviation(r, convention=DownsideConvention.DOWNSIDE_ONLY), 8)
    0.03
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    target = _align_target(series, mar, name="mar")

    shortfall = np.minimum(series.to_numpy() - target, 0.0)
    squared = np.square(shortfall)

    match convention:
        case DownsideConvention.FULL:
            denominator = float(len(series))
        case DownsideConvention.DOWNSIDE_ONLY:
            n_below = int((shortfall < 0).sum())
            if n_below == 0:
                return 0.0
            denominator = float(n_below)

    dd = float(np.sqrt(squared.sum() / denominator))

    if not annualise:
        return dd

    ann = resolve_annualisation(
        periods_per_year=periods_per_year,
        frequency=frequency,
        index=series.index if isinstance(series.index, pd.DatetimeIndex) else None,
    )
    return dd * float(np.sqrt(ann.periods_per_year))


def upside_deviation(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    mar: float | pd.Series = 0.0,
    convention: DownsideConvention = DownsideConvention.FULL,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Root of the second *upper* partial moment about a target.

    .. math::
        \text{UD} = \sqrt{\frac{1}{n}\sum_{t=1}^{n}
                          \left[\max(r_t - \text{MAR}, 0)\right]^2}

    Parameters
    ----------
    returns
        Simple periodic returns.
    mar
        Per-period target as a decimal; scalar or aligned Series.
    convention
        Denominator convention, mirroring :func:`downside_deviation`.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Upside deviation as a non-negative decimal.
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    target = _align_target(series, mar, name="mar")

    excess = np.maximum(series.to_numpy() - target, 0.0)

    match convention:
        case DownsideConvention.FULL:
            denominator = float(len(series))
        case DownsideConvention.DOWNSIDE_ONLY:
            n_above = int((excess > 0).sum())
            if n_above == 0:
                return 0.0
            denominator = float(n_above)

    return float(np.sqrt(np.square(excess).sum() / denominator))


def skewness(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    bias: bool = True,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Sample skewness of returns.

    .. math::

        g_1 = \frac{\frac{1}{n}\sum (r_t - \bar{r})^3}
                   {\left[\frac{1}{n}\sum (r_t - \bar{r})^2\right]^{3/2}}

    Parameters
    ----------
    returns
        Simple periodic returns.
    bias
        When ``True`` (default) return the biased moment estimator :math:`g_1`
        above. When ``False`` apply the Fisher-Pearson adjustment
        :math:`G_1 = g_1 \sqrt{n(n-1)}/(n-2)`, which requires ``n > 2``.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Skewness. Returns ``nan`` for a zero-variance series, where the ratio is
        ``0/0`` and no finite answer is meaningful.

    Raises
    ------
    InsufficientDataError
        If ``bias=False`` and fewer than three observations are supplied.

    Examples
    --------
    >>> import pandas as pd
    >>> round(skewness(pd.Series([0.0, 0.0, 0.0, 0.3])), 8)
    1.15470054
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    values = series.to_numpy()
    n = len(values)

    if not bias and n < 3:
        msg = f"Unbiased skewness requires at least 3 observations, got {n}."
        raise InsufficientDataError(msg)

    deviations = values - values.mean()
    m2 = float(np.mean(deviations**2))
    m3 = float(np.mean(deviations**3))

    if m2 == 0.0:
        return float("nan")

    g1 = m3 / m2**1.5
    if bias:
        return float(g1)
    return float(g1 * np.sqrt(n * (n - 1)) / (n - 2))


def kurtosis(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    fisher: bool = True,
    bias: bool = True,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Sample kurtosis of returns.

    .. math::

        g_2 = \frac{\frac{1}{n}\sum (r_t - \bar{r})^4}
                   {\left[\frac{1}{n}\sum (r_t - \bar{r})^2\right]^{2}}

    Parameters
    ----------
    returns
        Simple periodic returns.
    fisher
        When ``True`` (default) return excess kurtosis, :math:`g_2 - 3`, so a
        normal distribution scores ``0``. When ``False`` return Pearson kurtosis,
        where a normal scores ``3``.
    bias
        When ``True`` (default) use the biased moment estimator. When ``False``
        apply the standard small-sample correction, requiring ``n > 3``.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Kurtosis under the requested convention. ``nan`` for a zero-variance
        series.

    Raises
    ------
    InsufficientDataError
        If ``bias=False`` and fewer than four observations are supplied.

    Examples
    --------
    A normal-ish sample scores near zero under the Fisher convention:

    >>> import pandas as pd
    >>> round(kurtosis(pd.Series([-1.0, 0.0, 0.0, 1.0])), 8)
    -1.0
    """
    series = validate_returns(returns, nan_policy=nan_policy, min_observations=1)
    values = series.to_numpy()
    n = len(values)

    if not bias and n < 4:
        msg = f"Unbiased kurtosis requires at least 4 observations, got {n}."
        raise InsufficientDataError(msg)

    deviations = values - values.mean()
    m2 = float(np.mean(deviations**2))
    m4 = float(np.mean(deviations**4))

    if m2 == 0.0:
        return float("nan")

    g2 = m4 / m2**2

    if not bias:
        # Standard unbiased estimator of excess kurtosis.
        excess = ((n + 1) * (g2 - 3) + 6) * (n - 1) / ((n - 2) * (n - 3))
        return float(excess if fisher else excess + 3.0)

    return float(g2 - 3.0 if fisher else g2)


def tracking_error(
    returns: pd.Series,
    benchmark: pd.Series,
    *,
    periods_per_year: float | None = None,
    frequency: Frequency | None = None,
    annualise: bool = True,
    ddof: int = 1,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
) -> float:
    r"""Compute the standard deviation of active returns against a benchmark.

    .. math:: \text{TE} = \sigma(r_t - b_t) \cdot \sqrt{m}

    Parameters
    ----------
    returns
        Portfolio simple periodic returns.
    benchmark
        Benchmark simple periodic returns, aligned on the index.
    periods_per_year
        Explicit annualisation factor.
    frequency
        Explicit frequency, used when ``periods_per_year`` is absent.
    annualise
        Apply square-root-of-time scaling.
    ddof
        Delta degrees of freedom for the standard deviation.
    nan_policy
        How to treat missing returns.

    Returns
    -------
    float
        Tracking error as a decimal.

    Raises
    ------
    NoOverlapError
        If the two series share no dates.
    """
    from convexity.alignment import align_series

    port, bench = align_series(returns, benchmark, nan_policy=nan_policy)
    active = port - bench
    return volatility(
        active,
        periods_per_year=periods_per_year,
        frequency=frequency,
        annualise=annualise,
        ddof=ddof,
        nan_policy=NaNPolicy.PROPAGATE,
    )


def _align_target(
    series: pd.Series, target: float | pd.Series, *, name: str
) -> np.ndarray:
    """Broadcast a scalar target, or align a Series target, to ``series``."""
    if isinstance(target, pd.Series):
        from convexity.alignment import align_series

        _, aligned = align_series(series, target, name_b=name)
        return np.asarray(aligned.to_numpy(), dtype=float)

    value = float(target)
    if not np.isfinite(value):
        msg = f"{name} must be finite, got {target!r}."
        raise InsufficientDataError(msg)
    return np.full(len(series), value, dtype=float)
