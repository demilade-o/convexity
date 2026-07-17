# Conventions

If a number surprises you, the cause is almost always on this page.

A convention is not a detail. It is part of what the number *means*, which is
why every one of them here is a parameter rather than a default buried in an
implementation.

## 1. Annualisation

**A rate per year is not a rate per period.** Scaling between them needs to know
how many periods a year contains, and the library will not guess.

Resolution follows a strict precedence:

1. `periods_per_year` supplied by you — wins outright.
2. An explicit `Frequency` — uses its documented factor.
3. Inference from a `DatetimeIndex` — conservative, and only if confident.

If none applies, you get a `FrequencyInferenceError`. **There is no fallback to
252.** A library that assumes 252 will silently report a daily-annualised figure
for monthly data, and the number will look entirely plausible.

| Frequency | Periods per year |
| --- | --- |
| `BUSINESS_DAILY` | 252 |
| `CALENDAR_DAILY` | 365 |
| `WEEKLY` | 52 |
| `MONTHLY` | 12 |
| `QUARTERLY` | 4 |
| `ANNUAL` | 1 |

252 is a convention — an approximation of trading days in a year — not a derived
constant. It is stated explicitly rather than assumed.

### Inference reports its evidence

```python
>>> import pandas as pd, convexity as cx
>>> result = cx.infer_frequency(pd.date_range("2024-01-01", periods=60, freq="B"))
>>> result.frequency, result.confidence
(<Frequency.BUSINESS_DAILY: 'business_daily'>, 1.0)
>>> result.diagnostics["weekend_share"]
0.0

```

Business-daily and calendar-daily both have a ~1-day median gap. They are
separated by weekend presence, not gap size.

Below the confidence threshold, inference refuses and names the diagnostics.
Irregular data is never coerced into a regular annualisation.

## 2. Annualised volatility is a convention, not a measurement

`sigma_ann = sigma_period * sqrt(m)` assumes returns are serially uncorrelated
and identically distributed. Real return series usually violate both.

The scaling is applied only when you ask for it (`annualise=True`), and its
assumptions are stated on the function. It is a widely-used convention; it is not
a fact about your data.

## 3. The risk-free rate

**A scalar `risk_free` or `mar` is an ANNUAL rate.** The library converts it to a
period rate under a compounding convention you can name.

This default is right because that is how rates are quoted. Treating a 5% annual
bill yield as a 5% *daily* return inflates a Sharpe ratio beyond recognition, and
it is the single most common version of this bug.

Already have a periodic rate? Say so:

```python
>>> returns = pd.Series([0.01, 0.02, -0.01, 0.03] * 3)
>>> annual = cx.sharpe_ratio(returns, risk_free=0.12, periods_per_year=12)
>>> periodic = cx.sharpe_ratio(returns, risk_free=0.01, risk_free_is_annual=False,
...                            periods_per_year=12)
>>> round(annual, 9) == round(periodic, 9)
True

```

### Compounding conventions

| Convention | Period rate | Use |
| --- | --- | --- |
| `SIMPLE` (default) | `r / m` | Money-market quotes: bills, overnight rates |
| `COMPOUNDED` | `(1 + r)^(1/m) - 1` | An effective annual rate (EAR/APY) |
| `CONTINUOUS` | `exp(r / m) - 1` | Derivatives pricing |

For a positive rate these order **continuous > simple > compounded**.
`CONTINUOUS` exceeds the linear `r/m` by its second-order term; `COMPOUNDED` must
be *smaller*, because compounding it `m` times has to land back on exactly `r`.

```python
>>> s = cx.annual_to_period_rate(0.05, 12, cx.Compounding.SIMPLE)
>>> c = cx.annual_to_period_rate(0.05, 12, cx.Compounding.CONTINUOUS)
>>> k = cx.annual_to_period_rate(0.05, 12, cx.Compounding.COMPOUNDED)
>>> c > s > k
True

```

## 4. Downside deviation: two conventions, one choice

This is the most consequential ambiguity in performance analytics.

$$\text{DD} = \sqrt{\frac{1}{d}\sum_{t=1}^{n}\left[\min(r_t - \text{MAR}, 0)\right]^2}$$

The question is what `d` is.

| Convention | `d` | Meaning |
| --- | --- | --- |
| `FULL` (default) | total `n` | The second lower partial moment, per Sortino and Price (1994) |
| `DOWNSIDE_ONLY` | count below target | Average severity of a bad period, *given* it was bad |

They differ by `sqrt(n / n_below)`. One bad month in twelve makes
`DOWNSIDE_ONLY` **3.46×** larger — and correspondingly deflates any Sortino ratio
built on it.

Neither is wrong. They measure different things. What would be wrong is not
saying which you got.

`FULL` is the default because it matches the original definition, and because it
is a genuine moment: it is comparable across series with different numbers of
losing periods, which `DOWNSIDE_ONLY` is not.

## 5. Returns are decimals

`0.01` is 1%. Everywhere, without exception.

A value of `5` is taken as a **500% return**, not 5%. The library cannot
distinguish a genuine 500% return from a percentage-point mistake, so it does not
try. It does reject returns below `-1.0`, which imply negative wealth and are
always an error.

## 6. Numerators differ between ratios

This one catches people:

| Ratio | Numerator |
| --- | --- |
| Sharpe | **Arithmetic** annualised excess |
| Sortino | **Arithmetic** annualised excess |
| Calmar | **Geometric** annualised excess |

Sharpe and Sortino are defined on arithmetic means. Calmar's geometric numerator
follows its origin as a return-over-worst-loss measure, where the compounded
outcome is the quantity of interest.

The arithmetic figure exceeds the geometric by roughly half the variance. That is
volatility drag, and it is why the two are separate functions here rather than
one with a flag.

## 7. Missing data

`NaNPolicy` is an enum, not a string, so a typo is a type error rather than a
silent behaviour change.

| Policy | Behaviour |
| --- | --- |
| `RAISE` (default) | Any `NaN` raises with the location of the first gap |
| `DROP` | Drop missing, then compute |
| `PROPAGATE` | Let `NaN` flow into the result |

`DROP` deserves a warning of its own: dropping breaks the even spacing that
annualisation assumes. It is offered because it is often what you want, not
because it is free.

## 8. Zero denominators

| Numerator | Denominator | Result |
| --- | --- | --- |
| `> 0` | `0` | `+inf` |
| `< 0` | `0` | `-inf` |
| `0` | `0` | `nan` |

These return rather than raise: a series with no downside is a legitimate
sample, not a caller error.

This needs more care than it looks. `np.std` over identical floats returns ~1e-18
rather than `0.0`, so a naive implementation divides by dust and reports ~1e16 —
a meaningless artefact that looks like a finite answer. `convexity` checks the
input's range instead of trusting the reduction, so a constant series gives
exactly zero dispersion and the documented infinity.

## See also

- [Point-in-time data](point-in-time.md) — why alignment is backward-looking
- [Metric catalogue](../metrics/index.md) — the conventions for every metric
