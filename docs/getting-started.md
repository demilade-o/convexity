# Five-minute start

Every example on this page is executed as a doctest in CI, so none of them can
rot.

## Install

```bash
pip install convexity
```

## A tear sheet in ten lines

```python
>>> import pandas as pd
>>> import convexity as cx
>>> returns = pd.Series(
...     [0.021, -0.013, 0.034, 0.008, -0.027, 0.019,
...      0.011, -0.005, 0.024, 0.002, -0.018, 0.030],
...     index=pd.date_range("2024-01-31", periods=12, freq="ME"),
... )
>>> round(cx.annualised_return(returns, periods_per_year=12), 6)
0.08718
>>> round(cx.volatility(returns, periods_per_year=12), 6)
0.06812
>>> round(cx.max_drawdown(returns), 6)
-0.027

```

## Frequency is explicit

`periods_per_year=12` is not boilerplate. It is the difference between a
plausible number and a wrong one.

Omit it and the library will infer from the index — but only if the index
supports a *confident* answer, and it will tell you what it concluded rather
than guessing:

```python
>>> inference = cx.infer_frequency(returns.index)
>>> inference.frequency
<Frequency.MONTHLY: 'monthly'>
>>> inference.is_confident
True
>>> round(inference.diagnostics["median_gap_days"], 1)
31.0

```

If the index cannot support a confident answer, you get an error naming the
diagnostics — never a silent guess:

```python
>>> cx.sortino_ratio(pd.Series([0.01, -0.02, 0.03]))
Traceback (most recent call last):
    ...
convexity.exceptions.FrequencyInferenceError: Cannot annualise: supply periods_per_year, a Frequency, or a DatetimeIndex to infer from. This library does not assume a default.

```

## A scalar risk-free rate is annual

`risk_free=0.05` means **5% per year**. The library converts it to a period rate
under a compounding convention you can name:

```python
>>> round(cx.sharpe_ratio(returns, risk_free=0.05, periods_per_year=12), 6)
0.528477

```

Supplying an already-periodic rate? Say so, or it will be understated by a
factor of `m`:

```python
>>> monthly_rate = 0.05 / 12
>>> round(cx.sharpe_ratio(returns, risk_free=monthly_rate,
...                       risk_free_is_annual=False, periods_per_year=12), 6)
0.528477

```

## A time-varying rate works identically

Rates are aligned with a backward as-of join, so a rate published after a
measurement date can never inform it:

```python
>>> rates = pd.Series(
...     [0.053, 0.048],
...     index=pd.to_datetime(["2023-12-01", "2024-07-01"]),
... )
>>> round(cx.sortino_ratio(returns, mar=rates, periods_per_year=12), 6)
0.823281

```

The two quotes cover twelve months: 5.3% applies until July, 4.8% after. You do
not need to expand them yourself.

## Choose your convention

Downside deviation has two incompatible denominator conventions, and libraries
disagree about which to use. Here you choose, and the default is documented:

```python
>>> full = cx.downside_deviation(returns, mar=0.0)
>>> only = cx.downside_deviation(
...     returns, mar=0.0, convention=cx.DownsideConvention.DOWNSIDE_ONLY
... )
>>> round(full, 6), round(only, 6)
(0.010194, 0.017656)

```

The `DOWNSIDE_ONLY` figure is larger by exactly `sqrt(3)`, because 4 of the 12
months are below target and the denominator falls from 12 to 4:

```python
>>> round(only / full, 6)
1.732051

```

Neither is wrong; they measure different things. Silence about which one you got
would be wrong.

## Reporting a problem

```python
>>> cx.show_versions()  # doctest: +SKIP
convexity    : 0.1.0
python       : 3.13.14
numpy        : 2.5.1
pandas       : 3.0.3
...
```

## Next

- **[Conventions](concepts/conventions.md)** — the four things that explain
  almost every surprising number.
- **[Metric catalogue](metrics/index.md)** — every metric and its contract.
