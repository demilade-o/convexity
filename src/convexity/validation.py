"""Input validation and missing-data policy.

Policies are enums, never free-text strings, so a typo is a type error rather than
a silent behaviour change. Validators never mutate caller-owned objects: any
function that changes a series returns a new one.
"""

from __future__ import annotations

import enum
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from convexity.exceptions import (
    DataQualityError,
    IndexValidationError,
    InsufficientDataError,
)

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "NaNPolicy",
    "apply_nan_policy",
    "validate_datetime_index",
    "validate_returns",
]


class NaNPolicy(enum.Enum):
    """How a metric treats missing observations.

    Attributes
    ----------
    RAISE
        Any ``NaN`` raises :class:`~convexity.exceptions.DataQualityError`. Safest
        default for metrics where a gap changes the meaning of the result.
    DROP
        Drop missing observations, then compute. Note that dropping breaks the
        even spacing that annualisation assumes; the diagnostic records how many
        were removed so the caller can judge.
    PROPAGATE
        Leave ``NaN`` in place and let it propagate to the result. Useful when the
        caller wants missingness to be visible rather than handled.
    """

    RAISE = "raise"
    DROP = "drop"
    PROPAGATE = "propagate"


def validate_datetime_index(
    index: pd.Index,
    *,
    require_monotonic: bool = True,
    require_unique: bool = True,
) -> pd.DatetimeIndex:
    """Validate that an index is usable for a time-dependent metric.

    Parameters
    ----------
    index
        Index to check.
    require_monotonic
        Require monotonic increasing timestamps. Out-of-order data is never
        silently sorted, because sorting a series whose values were computed in
        the original order can fabricate results.
    require_unique
        Require unique timestamps. Duplicates are never silently dropped or
        aggregated; the caller must decide what a repeated timestamp means.

    Returns
    -------
    pandas.DatetimeIndex
        The same index, narrowed for typing purposes. Not a copy.

    Raises
    ------
    IndexValidationError
        If the index is not a ``DatetimeIndex``, or violates a requirement.

    Examples
    --------
    >>> import pandas as pd
    >>> idx = validate_datetime_index(pd.date_range("2024-01-01", periods=3))
    >>> len(idx)
    3
    """
    if not isinstance(index, pd.DatetimeIndex):
        msg = (
            f"A DatetimeIndex is required for time-dependent metrics, got "
            f"{type(index).__name__}. Convert with pd.to_datetime(...) first."
        )
        raise IndexValidationError(msg)

    if require_unique and not index.is_unique:
        duplicates = index[index.duplicated()].unique()
        preview = ", ".join(str(d) for d in duplicates[:3])
        msg = (
            f"Index contains {len(duplicates)} duplicated timestamp(s) "
            f"(e.g. {preview}). Duplicates are not dropped automatically: decide "
            f"whether they should be aggregated, averaged, or removed, then retry."
        )
        raise IndexValidationError(msg)

    if require_monotonic and not index.is_monotonic_increasing:
        msg = (
            "Index is not monotonic increasing. Out-of-order observations are not "
            "sorted automatically because ordering can be meaningful. Sort "
            "explicitly with .sort_index() if that is correct for your data."
        )
        raise IndexValidationError(msg)

    return index


def validate_returns(
    returns: pd.Series | Sequence[float] | np.ndarray,
    *,
    name: str = "returns",
    min_observations: int = 1,
    nan_policy: NaNPolicy = NaNPolicy.RAISE,
    require_datetime_index: bool = False,
    allow_total_loss: bool = True,
) -> pd.Series:
    """Validate and normalise a returns input.

    Returns are decimals throughout this library: ``0.01`` is 1%. A value of
    ``5`` is interpreted as a 500% return, not 5%, and is not rejected -- the
    library cannot distinguish a genuine 500% return from a percentage-point
    mistake, so it does not guess.

    Parameters
    ----------
    returns
        Periodic returns as a Series, array, or sequence.
    name
        Label used in error messages.
    min_observations
        Minimum usable observations after the NaN policy is applied.
    nan_policy
        How to treat missing values. See :class:`NaNPolicy`.
    require_datetime_index
        Require a valid ``DatetimeIndex``.
    allow_total_loss
        Permit returns of exactly ``-1.0`` (total loss). Returns strictly below
        ``-1.0`` are always rejected: a simple return under ``-100%`` implies
        negative wealth and is invariably a data error.

    Returns
    -------
    pandas.Series
        A validated float Series. Always a new object; the caller's input is
        never mutated.

    Raises
    ------
    DataQualityError
        Non-finite values under ``NaNPolicy.RAISE``, infinities, or returns below
        ``-1.0``.
    InsufficientDataError
        Fewer usable observations than ``min_observations``.
    IndexValidationError
        Index unusable when ``require_datetime_index`` is set.

    Examples
    --------
    >>> import pandas as pd
    >>> validate_returns(pd.Series([0.01, -0.02, 0.03])).tolist()
    [0.01, -0.02, 0.03]
    """
    series = (
        returns.copy() if isinstance(returns, pd.Series) else pd.Series(returns)
    )

    try:
        series = series.astype(float)
    except (TypeError, ValueError) as exc:
        msg = f"{name} must be numeric; could not cast to float ({exc})."
        raise DataQualityError(msg) from exc

    if require_datetime_index:
        validate_datetime_index(series.index)

    # Infinities are always an error: they are never a meaningful return and
    # would silently poison every downstream aggregate.
    if bool(np.isinf(series.to_numpy()).any()):
        n_inf = int(np.isinf(series.to_numpy()).sum())
        msg = (
            f"{name} contains {n_inf} infinite value(s). Infinite returns are not "
            f"meaningful; clean the input before computing metrics."
        )
        raise DataQualityError(msg)

    series = apply_nan_policy(series, nan_policy, name=name)

    if not allow_total_loss:
        below = series <= -1.0
        if bool(below.any()):
            msg = (
                f"{name} contains {int(below.sum())} value(s) at or below -1.0, "
                f"which this metric cannot compound. Set allow_total_loss=True "
                f"only if a total loss is genuinely represented."
            )
            raise DataQualityError(msg)
    else:
        below = series < -1.0
        if bool(below.any()):
            worst = float(series.min())
            msg = (
                f"{name} contains {int(below.sum())} simple return(s) below -1.0 "
                f"(minimum {worst:.6g}). A simple return under -100% implies "
                f"negative wealth. If these are log returns, convert them first."
            )
            raise DataQualityError(msg)

    n_usable = int(series.notna().sum())
    if n_usable < min_observations:
        msg = (
            f"{name} has {n_usable} usable observation(s) but this metric requires "
            f"at least {min_observations}."
        )
        raise InsufficientDataError(msg)

    return series


def apply_nan_policy(
    series: pd.Series,
    policy: NaNPolicy,
    *,
    name: str = "series",
) -> pd.Series:
    """Apply a :class:`NaNPolicy` to a series.

    Parameters
    ----------
    series
        Input series. Not mutated.
    policy
        Policy to apply.
    name
        Label used in error messages.

    Returns
    -------
    pandas.Series
        A new series with the policy applied.

    Raises
    ------
    DataQualityError
        If ``policy`` is :attr:`NaNPolicy.RAISE` and missing values are present.
    """
    n_missing = int(series.isna().sum())
    if n_missing == 0:
        return series

    match policy:
        case NaNPolicy.RAISE:
            first = series.index[series.isna()][0]
            msg = (
                f"{name} contains {n_missing} missing value(s), first at {first!r}. "
                f"Pass nan_policy=NaNPolicy.DROP to drop them (note this breaks even "
                f"spacing that annualisation assumes) or NaNPolicy.PROPAGATE to let "
                f"them flow into the result."
            )
            raise DataQualityError(msg)
        case NaNPolicy.DROP:
            return series.dropna()
        case NaNPolicy.PROPAGATE:
            return series
