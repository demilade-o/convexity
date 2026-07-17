"""Series alignment with point-in-time integrity.

Two series can only be compared where they overlap, and a rate or benchmark
observation may only inform a measurement date it preceded. Both rules are
enforced here rather than left to pandas' default index arithmetic, which will
happily broadcast a future value onto a past date.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd

from convexity.exceptions import NoOverlapError, StaleDataError
from convexity.validation import NaNPolicy, apply_nan_policy, validate_datetime_index

__all__ = ["align_asof", "align_series"]

#: Datetime resolutions pandas supports, ordered coarsest to finest.
DatetimeUnit = Literal["s", "ms", "us", "ns"]


def align_series(
    a: pd.Series,
    b: pd.Series,
    *,
    nan_policy: NaNPolicy = NaNPolicy.PROPAGATE,
    name_a: str = "returns",
    name_b: str = "other",
) -> tuple[pd.Series, pd.Series]:
    """Align two series on their common index.

    Alignment is an inner join: only dates present in both survive. Neither input
    is mutated, and no value is forward-filled -- a gap in one series removes the
    date from both rather than borrowing a neighbouring observation.

    Parameters
    ----------
    a, b
        Series to align.
    nan_policy
        Applied to both series *after* the join, so a missing value in either
        member is handled consistently.
    name_a, name_b
        Labels used in error messages.

    Returns
    -------
    tuple of pandas.Series
        The two series restricted to their shared, ordered index.

    Raises
    ------
    NoOverlapError
        If the series share no dates. This is raised rather than returning an
        empty result, because every downstream metric of an empty series is
        either an error or a misleading ``nan``.

    Examples
    --------
    >>> import pandas as pd
    >>> idx_a = pd.date_range("2024-01-01", periods=3)
    >>> idx_b = pd.date_range("2024-01-02", periods=3)
    >>> x, y = align_series(pd.Series([1.0, 2, 3], index=idx_a),
    ...                     pd.Series([4.0, 5, 6], index=idx_b))
    >>> len(x)
    2
    """
    series_a = pd.Series(a).astype(float)
    series_b = pd.Series(b).astype(float)

    common = series_a.index.intersection(series_b.index)
    if len(common) == 0:
        msg = (
            f"{name_a} and {name_b} share no common index entries, so they cannot "
            f"be compared. {name_a} spans {_span(series_a)}; {name_b} spans "
            f"{_span(series_b)}. Check for a timezone or calendar mismatch."
        )
        raise NoOverlapError(msg)

    out_a = apply_nan_policy(series_a.loc[common], nan_policy, name=name_a)
    out_b = apply_nan_policy(series_b.loc[common], nan_policy, name=name_b)

    if nan_policy is NaNPolicy.DROP:
        # Dropping independently would desynchronise the pair.
        both = out_a.index.intersection(out_b.index)
        out_a, out_b = out_a.loc[both], out_b.loc[both]

    return out_a, out_b


def align_asof(
    target_index: pd.DatetimeIndex,
    source: pd.Series,
    *,
    max_staleness: pd.Timedelta | None = None,
    publication_lag: pd.Timedelta | None = None,
    name: str = "source",
) -> pd.Series:
    """Align a source series onto a target index using backward as-of logic.

    For each target date, the most recent source observation *at or before* that
    date is selected. A source observation never informs an earlier target date,
    which is what makes this safe for risk-free rates, benchmarks, and any other
    series joined onto a measurement calendar.

    Parameters
    ----------
    target_index
        Dates to align onto. Must be a valid, sorted, unique ``DatetimeIndex``.
    source
        Series to draw from, indexed by observation date.
    max_staleness
        Reject any target date whose matched observation is older than this. Use
        it to prevent a rate from months ago silently standing in for today's.
        ``None`` permits unbounded carry-forward.
    publication_lag
        Delay between an observation's timestamp and its real-world availability.
        Each source observation is treated as usable only from
        ``observation_date + publication_lag`` onwards. This models the fact that
        a figure stamped for a given day is often not published until later.
    name
        Label used in error messages.

    Returns
    -------
    pandas.Series
        Values aligned to ``target_index``, carrying its index.

    Raises
    ------
    NoOverlapError
        If no target date has any prior source observation.
    StaleDataError
        If ``max_staleness`` is exceeded for any target date.
    IndexValidationError
        If either index is not a sorted, unique ``DatetimeIndex``. Sorting is
        required for the backward match to be deterministic.

    Examples
    --------
    A rate published monthly, aligned onto daily dates, carries forward:

    >>> import pandas as pd
    >>> rates = pd.Series([0.05, 0.04],
    ...                   index=pd.to_datetime(["2024-01-01", "2024-02-01"]))
    >>> daily = pd.to_datetime(["2024-01-15", "2024-02-15"])
    >>> align_asof(daily, rates).tolist()
    [0.05, 0.04]

    A target date before any observation has no valid match:

    >>> align_asof(pd.to_datetime(["2023-12-01", "2024-01-15"]), rates).tolist()
    [nan, 0.05]
    """
    # validate_datetime_index enforces monotonicity and uniqueness on both sides,
    # which is what makes the backward match deterministic.
    target_checked = validate_datetime_index(target_index)
    source_series = pd.Series(source).astype(float)
    source_index = validate_datetime_index(source_series.index)

    effective = source_series.copy()
    if publication_lag is not None:
        # Shift availability forward: an observation becomes usable only after
        # its publication lag has elapsed.
        effective.index = source_index + publication_lag

    # merge_asof requires both join keys to share a dtype exactly, and pandas
    # does not guarantee a single datetime resolution: adding a Timedelta can
    # promote an index to nanoseconds while the other side stays microseconds.
    # Normalise both to the finer of the two so no timestamp precision is lost.
    effective_index = pd.DatetimeIndex(effective.index)
    unit = _finer_unit(target_checked.unit, effective_index.unit)
    target_norm = target_checked.as_unit(unit)
    source_norm = effective_index.as_unit(unit)

    frame_target = pd.DataFrame(index=target_norm).reset_index(names="_target")
    frame_source = pd.DataFrame(
        {"_value": effective.to_numpy(), "_observed": source_norm}
    )

    merged = pd.merge_asof(
        frame_target,
        frame_source,
        left_on="_target",
        right_on="_observed",
        direction="backward",
    )

    values = merged["_value"].to_numpy()
    if bool(np.all(np.isnan(values))):
        msg = (
            f"No {name} observation precedes any target date. {name} spans "
            f"{_span(effective)}; targets span {target_index[0]} to "
            f"{target_index[-1]}. An as-of join never looks forward."
        )
        raise NoOverlapError(msg)

    if max_staleness is not None:
        age = merged["_target"] - merged["_observed"]
        too_old = age > max_staleness
        if bool(too_old.any()):
            worst = age[too_old].max()
            first = merged.loc[too_old, "_target"].iloc[0]
            msg = (
                f"{name} exceeded the permitted staleness of {max_staleness} for "
                f"{int(too_old.sum())} target date(s); the worst is {worst} old "
                f"(first at {first}). Supply fresher data or raise max_staleness "
                f"deliberately."
            )
            raise StaleDataError(msg)

    return pd.Series(values, index=target_checked, name=source_series.name)


_UNIT_ORDER: tuple[DatetimeUnit, ...] = ("s", "ms", "us", "ns")


def _finer_unit(left: DatetimeUnit, right: DatetimeUnit) -> DatetimeUnit:
    """Return whichever datetime unit carries more precision."""
    return max(left, right, key=_UNIT_ORDER.index)


def _span(series: pd.Series) -> str:
    if len(series) == 0:
        return "(empty)"
    return f"{series.index[0]} to {series.index[-1]}"
