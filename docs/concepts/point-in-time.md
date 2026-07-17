# Point-in-time data

A number that used information which did not exist yet is not a slightly
optimistic number. It is a fiction.

Look-ahead bias is insidious because it always flatters, and it never raises an
error. This page describes what `convexity` does about it.

## The default is backward-looking

Pandas will happily broadcast a future value onto a past date. Given a rate
series and a returns series, an ordinary index join or a `reindex` with
forward-fill can quietly put September's rate on a March observation.

`convexity` never joins a rate or benchmark with plain index arithmetic. It uses
a **backward as-of join**: for each measurement date, the most recent source
observation *at or before* that date.

```python
>>> import pandas as pd, convexity as cx
>>> rates = pd.Series([0.05, 0.04],
...                   index=pd.to_datetime(["2024-01-01", "2024-02-01"]))
>>> cx.align_asof(pd.to_datetime(["2024-01-15", "2024-02-15"]), rates).tolist()
[0.05, 0.04]

```

A date before any observation gets `nan`, never a backfill:

```python
>>> cx.align_asof(pd.to_datetime(["2023-12-01", "2024-01-15"]), rates).tolist()
[nan, 0.05]

```

This guarantee is property-tested: on arbitrary target and source shapes, no
as-of match ever carries an observation dated after the target it informed.

## A future rate cannot change a past result

The practical consequence, asserted for every ratio:

```python
>>> returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 3,
...                     index=pd.date_range("2024-01-31", periods=12, freq="ME"))
>>> base = pd.Series([0.05], index=pd.to_datetime(["2023-12-01"]))
>>> with_future = pd.Series([0.05, 0.99],
...                         index=pd.to_datetime(["2023-12-01", "2030-01-01"]))
>>> a = cx.sortino_ratio(returns, mar=base, periods_per_year=12)
>>> b = cx.sortino_ratio(returns, mar=with_future, periods_per_year=12)
>>> a == b
True

```

Appending a 99% rate dated 2030 changes nothing about a 2024 sample. If it did,
the alignment would be leaking.

## Publication lag

An observation's timestamp is not when it became knowable. A figure stamped for
1 January is frequently not published until later, and using it on 3 January is
look-ahead even though the dates look fine.

`publication_lag` models this:

```python
>>> quotes = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
>>> targets = pd.to_datetime(["2024-01-03", "2024-01-10"])
>>> lagged = cx.align_asof(targets, quotes, publication_lag=pd.Timedelta(days=5))
>>> bool(lagged.isna().iloc[0]), float(lagged.iloc[1])
(True, 0.05)

```

With a five-day lag the observation is invisible on 3 January and available by
10 January.

## Staleness

Carrying a rate forward is usually right. Carrying it forward *forever* is not:
a rate from six months ago should not silently stand in for today's.

```python
>>> old = pd.Series([0.05], index=pd.to_datetime(["2024-01-01"]))
>>> cx.align_asof(pd.to_datetime(["2024-06-01"]), old,
...               max_staleness=pd.Timedelta(days=7))
Traceback (most recent call last):
    ...
convexity.exceptions.StaleDataError: source exceeded the permitted staleness of 7 days 00:00:00 for 1 target date(s); the worst is 152 days 00:00:00 old (first at 2024-06-01 00:00:00). Supply fresher data or raise max_staleness deliberately.

```

Unbounded carry-forward is the default because a bound cannot be chosen for you.
Setting one is a judgement about your data.

## Alignment never borrows

`align_series` is an inner join. A gap in one series removes the date from both
rather than borrowing a neighbouring observation:

```python
>>> a = pd.Series([1.0, 2.0, 3.0], index=pd.date_range("2024-01-01", periods=3))
>>> b = pd.Series([4.0, 6.0], index=pd.to_datetime(["2024-01-01", "2024-01-03"]))
>>> left, right = cx.align_series(a, b)
>>> len(left), right.tolist()
(2, [4.0, 6.0])

```

No overlap at all raises rather than returning an empty frame, because every
metric of an empty series is either an error or a misleading `nan`.

## What this does not solve

- **Revisions.** Many economic series are revised after first publication. Using
  a revised value for a date before the revision existed is look-ahead. Handling
  it needs vintage data, which arrives with the provider layer.
- **Survivorship bias.** A property of your universe, not your alignment.
- **Fundamentals.** Never align a later filing to an earlier investment date.
  Point-in-time fundamentals arrive with the equity module.

Backward-looking alignment is necessary, not sufficient.
