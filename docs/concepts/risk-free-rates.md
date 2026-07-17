# Risk-free rates

A risk-free rate is not a number. It is a number *plus* the six decisions that
give it meaning: the currency, the tenor, the date it was observed, the
compounding convention, the day-count basis, and whether it was even current on
the date you are measuring against.

Pass a bare `0.05` into a Sharpe ratio and all six are hidden. `convexity` models
them explicitly instead, so a downstream metric knows exactly what it was handed.

!!! warning "There is no universal risk-free rate"
    An overnight policy rate, a Treasury bill yield, and a ten-year
    constant-maturity yield are different numbers measuring different things.
    Which one is "the" risk-free rate depends on the horizon and currency of your
    question. `convexity` records which one you used; it does not choose for you.

## The four models

| Model | What it carries |
| --- | --- |
| [`RateQuote`](../reference/api.md#convexity.rates.models.RateQuote) | One dated rate with its full convention. |
| [`RiskFreeSeries`](../reference/api.md#convexity.rates.models.RiskFreeSeries) | A history of quotes under one convention, plus provenance. |
| [`ZeroCurve`](../reference/api.md#convexity.rates.models.ZeroCurve) | A term structure for discounting and forward rates. |
| [`RiskFreePolicy`](../reference/api.md#convexity.rates.models.RiskFreePolicy) | The reusable rules for turning any of the above into an aligned series. |

## From an annual quote to a period return

A quoted annual rate is not a period return. Converting one to the other needs a
declared compounding convention, and getting it wrong is the classic
Sharpe-inflation bug — treating a 5% annual bill yield as a 5% daily return.

```python
import pandas as pd
import convexity as cx

quote = cx.RateQuote(0.12, pd.Timestamp("2024-01-31"), currency="USD")
quote.period_return(12)      # 0.01 — a 12% annual rate is 1% per month, simple
```

The compounding convention travels with the quote. If it says `COMPOUNDED`, the
conversion is geometric; if `SIMPLE` (the money-market default), it is pro-rata.

## Alignment never looks ahead

The reason these models exist is to feed a ratio *safely*. A
[`RiskFreeSeries`](../reference/api.md#convexity.rates.models.RiskFreeSeries)
aligns onto a return series' calendar with a **backward as-of join**: for each
date, the most recent rate *at or before* it. A rate published after a
measurement date can never inform it.

```python
idx = pd.date_range("2024-01-31", periods=12, freq="ME")
returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 3, index=idx)

rates = cx.RiskFreeSeries(pd.Series([0.05], index=idx[:1]), currency="USD")
rf = rates.to_period_returns(idx, periods_per_year=12)   # aligned, per-period

cx.sharpe_ratio(returns, risk_free=rf, periods_per_year=12)
```

`to_period_returns` does two things in order: it aligns the annual rate onto the
target calendar without look-ahead, then converts it to a per-period return under
the series' own compounding. See [Point-in-time data](point-in-time.md) for the
alignment guarantees, including `max_staleness` and `publication_lag`.

## Policies refuse to convert silently

A [`RiskFreePolicy`](../reference/api.md#convexity.rates.models.RiskFreePolicy)
bundles the rules — currency, preferred instrument, staleness, publication lag —
so the same definition can be reused across analyses. It refuses to cross
currencies:

```python
policy = cx.RiskFreePolicy(currency="EUR", max_staleness=pd.Timedelta(days=40))
policy.resolve(usd_series, target_index)   # raises CurrencyMismatchError
```

A EUR policy handed a USD series raises rather than converting: an FX conversion
is a modelling decision, not a detail to be inferred.

## Curves: discounting and forwards

A [`ZeroCurve`](../reference/api.md#convexity.rates.models.ZeroCurve) stores
continuously compounded zero rates at pillar tenors and interpolates between
them. It answers discount-factor and forward-rate queries; the interpolation
method is declared, and extrapolation beyond the pillars is flat and documented,
not silent.

```python
curve = cx.ZeroCurve([1.0, 2.0, 5.0], [0.03, 0.035, 0.04],
                     valuation_date=pd.Timestamp("2024-01-01"))
curve.discount_factor(2.0)     # exp(-z(2) * 2)
curve.forward_rate(2.0, 5.0)   # continuously compounded forward
```

Curve *bootstrapping* from market instruments arrives with the fixed-income
module; see [ROADMAP.md](https://github.com/demilade-o/convexity/blob/main/ROADMAP.md).
This release ships the discounting and forward-rate mechanics.
