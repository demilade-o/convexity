# Tutorial: analysing a return series

A complete pass over a strategy's monthly returns, from raw numbers to a
defensible summary. Every code block runs as a doctest in CI.

## The data

Synthetic, and deliberately so: this project ships no market data. A synthetic
series reproduces every issue you are likely to hit.

```python
>>> import pandas as pd
>>> import convexity as cx
>>> returns = pd.Series(
...     [0.021, -0.013, 0.034, 0.008, -0.027, 0.019, 0.011, -0.005,
...      0.024, 0.002, -0.018, 0.030, 0.015, -0.009, 0.028, -0.033,
...      0.041, 0.006, -0.011, 0.017, 0.009, -0.022, 0.036, 0.013],
...     index=pd.date_range("2023-01-31", periods=24, freq="ME"),
... )
>>> len(returns)
24

```

## Step 1: what frequency is this?

Before any annualised number, establish the frequency — and make the library
show its evidence rather than trusting it:

```python
>>> inference = cx.infer_frequency(returns.index)
>>> inference.frequency, inference.is_confident
(<Frequency.MONTHLY: 'monthly'>, True)
>>> inference.confidence
1.0

```

Confident, so inference is safe here. We will still pass `periods_per_year=12`
explicitly below: being explicit costs nothing and survives someone later
handing this function a ragged index.

## Step 2: growth

```python
>>> round(cx.cumulative_return(returns), 6)
0.18584
>>> round(cx.annualised_return(returns, periods_per_year=12), 6)
0.088963

```

Note what happens if you use the arithmetic mean instead:

```python
>>> round(cx.arithmetic_annualised_return(returns, periods_per_year=12), 6)
0.088

```

Higher — always. The gap is volatility drag, roughly half the variance. The
arithmetic figure is not the return an investor earned; it is reported because
Sharpe and Sortino are defined on it.

## Step 3: risk

```python
>>> round(cx.volatility(returns, periods_per_year=12), 6)
0.071925
>>> round(cx.max_drawdown(returns), 6)
-0.033

```

Drawdown episodes tell you more than the maximum alone:

```python
>>> episodes = cx.drawdown_episodes(returns)
>>> len(episodes)
8
>>> worst = min(episodes, key=lambda e: e.depth)
>>> round(worst.depth, 6), worst.is_recovered
(-0.033, True)

```

`is_recovered` matters: an unrecovered drawdown reports `recovery=None` rather
than pretending a recovery happened.

## Step 4: risk-adjusted, against a real rate

A scalar rate is annual and gets converted for you:

```python
>>> round(cx.sharpe_ratio(returns, risk_free=0.04, periods_per_year=12), 6)
0.667361

```

A time-varying rate is aligned with a backward as-of join. Two quotes cover two
years; you do not expand them yourself:

```python
>>> rates = pd.Series(
...     [0.045, 0.038],
...     index=pd.to_datetime(["2022-12-01", "2024-01-01"]),
... )
>>> round(cx.sharpe_ratio(returns, risk_free=rates, periods_per_year=12), 6)
0.646363

```

## Step 5: state your Sortino convention

```python
>>> full = cx.sortino_ratio(returns, mar=0.04, periods_per_year=12)
>>> only = cx.sortino_ratio(
...     returns, mar=0.04, periods_per_year=12,
...     convention=cx.DownsideConvention.DOWNSIDE_ONLY,
... )
>>> round(full, 4), round(only, 4)
(1.069, 0.6546)

```

The same series, the same target, two legitimate conventions, and the
downside-only figure is 39% lower. The gap is exactly `sqrt(24/9)`, since 9 of
the 24 months fall below the per-period target of 0.333%:

```python
>>> round(full / only, 4)
1.633

```

Reporting one without naming it is how performance numbers become unfalsifiable.

## Step 6: Calmar, and its lookback

```python
>>> round(cx.calmar_ratio(returns, periods_per_year=12), 6)
2.695842

```

The classic definition uses a trailing 36 months. With 24 months of data, the
full sample *is* the window — so this is really the MAR ratio, and saying so is
part of reporting it honestly.

Restricting the lookback changes both the return and the drawdown:

```python
>>> round(cx.calmar_ratio(returns, lookback_periods=12, periods_per_year=12), 6)
2.749942

```

## Step 7: rolling stability

A single ratio over 24 observations is noisy. Rolling shows whether it is stable
or an artefact of one window:

```python
>>> rolling = cx.rolling_sortino(returns, window=12, periods_per_year=12)
>>> bool(rolling.iloc[:11].isna().all())
True
>>> round(float(rolling.iloc[-1]), 4)
2.1362

```

Incomplete windows are `nan`, never a value computed from a partial window.

## Step 8: shape

```python
>>> round(cx.skewness(returns), 4)
-0.283
>>> round(cx.kurtosis(returns), 4)
-0.8949

```

`kurtosis` is Fisher (excess) by default, so a normal distribution scores 0. Pass
`fisher=False` for the Pearson convention where a normal scores 3.

With 24 observations, treat both as indicative. Fourth moments need far more data
than people assume.

## What you can defensibly say

> Over 24 months to December 2024, the strategy compounded 18.6% (8.9%
> annualised), with 7.2% annualised volatility and a 3.3% maximum drawdown.
> Against a time-varying risk-free rate, the Sharpe ratio was 0.65. The Sortino
> ratio was 1.07 using the full-sample downside convention of Sortino and Price
> (1994); it is 0.65 under the downside-only convention.

Every number carries its convention. That is the whole point.

## What you cannot say

Not from 24 observations: that the Sharpe ratio is significantly above zero,
that the drawdown is representative of the strategy's risk, or that any of this
predicts anything.

See [Limitations](../limitations.md).
