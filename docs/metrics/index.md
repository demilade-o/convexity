# Metric catalogue

<!--
  GENERATED FILE - do not edit by hand.
  Regenerate with: python scripts/generate_metric_docs.py
  Source of truth: src/convexity/registry.py
-->

Every metric this library computes, with the conventions it computes under.
This page is generated from the machine-readable registry in
`convexity.registry`, and CI fails if the two disagree.

Returns are decimals throughout: `0.01` is 1%.

## How to read an entry

- **Formula** is the definition as implemented. The rendered form, with every
  symbol defined, is in the function's own docstring.
- **Annualisation** states whether and how the result is scaled to a year. Where
  it says the value is not annualised, it is per-period.
- **Edge cases** is the documented policy at the boundaries, not a description of
  what happens to occur.
- **References** are primary sources. Where a metric has competing definitions in
  the literature, the default is stated with its citation and the alternatives are
  exposed as parameters.


## Contents

- **Returns** — [`simple_returns`](#simple_returns), [`log_returns`](#log_returns), [`to_log_returns`](#to_log_returns), [`to_simple_returns`](#to_simple_returns), [`wealth_index`](#wealth_index), [`cumulative_return`](#cumulative_return), [`annualised_return`](#annualised_return), [`arithmetic_annualised_return`](#arithmetic_annualised_return), [`cagr`](#cagr)
- **Risk** — [`volatility`](#volatility), [`downside_deviation`](#downside_deviation), [`upside_deviation`](#upside_deviation), [`skewness`](#skewness), [`kurtosis`](#kurtosis)
- **Drawdown** — [`drawdown_series`](#drawdown_series), [`max_drawdown`](#max_drawdown), [`drawdown_episodes`](#drawdown_episodes), [`average_drawdown`](#average_drawdown), [`ulcer_index`](#ulcer_index), [`pain_index`](#pain_index)
- **Ratio** — [`sharpe_ratio`](#sharpe_ratio), [`sortino_ratio`](#sortino_ratio), [`calmar_ratio`](#calmar_ratio), [`rolling_sharpe`](#rolling_sharpe), [`rolling_sortino`](#rolling_sortino), [`rolling_calmar`](#rolling_calmar)
- **Benchmark** — [`tracking_error`](#tracking_error)
- **Convention** — [`annual_to_period_rate`](#annual_to_period_rate), [`period_to_annual_rate`](#period_to_annual_rate), [`year_fraction`](#year_fraction), [`infer_frequency`](#infer_frequency), [`resolve_annualisation`](#resolve_annualisation), [`align_asof`](#align_asof), [`align_series`](#align_series)

## Returns

Returns, wealth, and annualisation. Simple returns compound multiplicatively; log returns compound additively. The two are never mixed silently.

### `simple_returns`

Simple (arithmetic) returns from a price series.

| | |
| --- | --- |
| **Formula** | `r_t = P_t / P_{t-1} - 1` |
| **Units** | decimal (0.01 is 1%) |
| **Annualisation** | none; per-period |
| **Minimum sample** | 2 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Non-positive price raises DataQualityError. First observation is dropped, never zero-filled. Fewer than 2 prices raises.

API: [`convexity.simple_returns`](../reference/api.md#convexity.returns.simple_returns)

### `log_returns`

Continuously compounded returns from a price series.

| | |
| --- | --- |
| **Formula** | `r_t = ln(P_t / P_{t-1})` |
| **Units** | decimal |
| **Annualisation** | none; per-period |
| **Minimum sample** | 2 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | continuously compounded returns |

**Edge cases.** Non-positive price raises; the logarithm is undefined there.

API: [`convexity.log_returns`](../reference/api.md#convexity.returns.log_returns)

### `to_log_returns`

Convert simple returns to log returns.

| | |
| --- | --- |
| **Formula** | `r_log = ln(1 + r)` |
| **Units** | decimal |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** A return at or below -1.0 raises; the logarithm diverges.

API: [`convexity.to_log_returns`](../reference/api.md#convexity.returns.to_log_returns)

### `to_simple_returns`

Convert log returns to simple returns.

| | |
| --- | --- |
| **Formula** | `r = exp(r_log) - 1` |
| **Units** | decimal |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Total round-trip identity with to_log_returns.

API: [`convexity.to_simple_returns`](../reference/api.md#convexity.returns.to_simple_returns)

### `wealth_index`

Compound simple returns into a wealth level.

| | |
| --- | --- |
| **Formula** | `W_t = W_0 * prod(1 + r_i)` |
| **Units** | wealth (same units as `initial`) |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** A return of exactly -1.0 drives wealth to zero and it stays zero: wealth cannot recover from a total loss. Non-positive `initial` raises.

API: [`convexity.wealth_index`](../reference/api.md#convexity.returns.wealth_index)

### `cumulative_return`

Total compounded return over the sample.

| | |
| --- | --- |
| **Formula** | `R = prod(1 + r_i) - 1` |
| **Units** | decimal |
| **Annualisation** | none; holding-period |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | holding-period return, total return |

**Edge cases.** Compounds rather than sums: +10% then -10% is -1%, not 0%.

API: [`convexity.cumulative_return`](../reference/api.md#convexity.returns.cumulative_return)

### `annualised_return`

Geometric annualised return from periodic returns.

| | |
| --- | --- |
| **Formula** | `R_ann = (prod(1 + r_i))^(m/n) - 1` |
| **Units** | decimal per year |
| **Annualisation** | Geometric. Requires periods_per_year, an explicit Frequency, or a confidently inferable DatetimeIndex; never assumes 252. |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | CAGR (periodic), geometric mean return |

**Edge cases.** Terminal wealth of zero annualises to exactly -1.0. No annualisation route raises FrequencyInferenceError.

API: [`convexity.annualised_return`](../reference/api.md#convexity.returns.annualised_return)

### `arithmetic_annualised_return`

Arithmetic mean return scaled to a year.

| | |
| --- | --- |
| **Formula** | `R_arith = m * mean(r)` |
| **Units** | decimal per year |
| **Annualisation** | Linear scaling by m. |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Exceeds the geometric annualised return by approximately half the variance. This is not the return an investor earns; it is reported because Sharpe and Sortino are defined on it.

API: [`convexity.arithmetic_annualised_return`](../reference/api.md#convexity.returns.arithmetic_annualised_return)

### `cagr`

Compound annual growth rate from actual elapsed calendar time.

| | |
| --- | --- |
| **Formula** | `CAGR = W_T^(365.25 / elapsed_days) - 1` |
| **Units** | decimal per year |
| **Annualisation** | From elapsed time directly; needs no periods_per_year, so it is the honest choice for irregularly spaced observations. |
| **Minimum sample** | 2 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Requires a DatetimeIndex and a positive elapsed span.

API: [`convexity.cagr`](../reference/api.md#convexity.returns.cagr)

## Risk

Dispersion and downside risk. Note that annualised volatility is a convention, not a measurement: square-root-of-time scaling assumes returns are serially uncorrelated and identically distributed, and real return series usually violate both.

### `volatility`

Standard deviation of returns, optionally annualised.

| | |
| --- | --- |
| **Formula** | `sigma_ann = sigma_period * sqrt(m)` |
| **Units** | decimal |
| **Annualisation** | Square-root-of-time, applied only when annualise=True. Assumes serially uncorrelated, identically distributed returns -- both usually false, which is why it is a convention, not a measurement. |
| **Minimum sample** | 2 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | standard deviation, sigma |

**Edge cases.** A constant series returns exactly 0.0, not floating-point dust. Requires more than ddof observations.

API: [`convexity.volatility`](../reference/api.md#convexity.risk.volatility)

### `downside_deviation`

Root of the second lower partial moment about a target.

| | |
| --- | --- |
| **Formula** | `DD = sqrt( sum(min(r_t - MAR, 0)^2) / denominator )` |
| **Units** | decimal |
| **Annualisation** | Square-root-of-time when annualise=True. |
| **Requires** | mar (per-period target) |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | semideviation, downside risk |

**Edge cases.** Denominator convention is explicit: FULL divides by total n (Sortino and Price 1994, the default); DOWNSIDE_ONLY divides by the count below target. The two differ by sqrt(n / n_below). Returns exactly 0.0 when nothing falls below the target -- a true statement about the sample, not a missing value.

**References**

- Sortino, F. A. and Price, L. N. (1994). Performance Measurement in a Downside Risk Framework. The Journal of Investing, 3(3), 59-64.

API: [`convexity.downside_deviation`](../reference/api.md#convexity.risk.downside_deviation)

### `upside_deviation`

Root of the second upper partial moment about a target.

| | |
| --- | --- |
| **Formula** | `UD = sqrt( sum(max(r_t - MAR, 0)^2) / denominator )` |
| **Units** | decimal |
| **Annualisation** | none by default |
| **Requires** | mar (per-period target) |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Mirrors downside_deviation under negation of the series.

API: [`convexity.upside_deviation`](../reference/api.md#convexity.risk.upside_deviation)

### `skewness`

Sample skewness of returns.

| | |
| --- | --- |
| **Formula** | `g1 = m3 / m2^(3/2)` |
| **Units** | dimensionless |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Zero-variance series returns nan: the ratio is 0/0 and reporting 0 would imply a symmetry that cannot be known. bias=False applies the Fisher-Pearson adjustment and requires n > 2.

API: [`convexity.skewness`](../reference/api.md#convexity.risk.skewness)

### `kurtosis`

Sample kurtosis of returns.

| | |
| --- | --- |
| **Formula** | `g2 = m4 / m2^2` |
| **Units** | dimensionless |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** fisher=True (default) returns excess kurtosis (normal scores 0); fisher=False returns Pearson kurtosis (normal scores 3). Zero-variance returns nan. bias=False requires n > 3.

API: [`convexity.kurtosis`](../reference/api.md#convexity.risk.kurtosis)

## Drawdown

Drawdown analytics. The running peak includes the starting wealth of 1.0, so a first-period loss is a real drawdown.

### `drawdown_series`

Underwater curve: decline from the running peak.

| | |
| --- | --- |
| **Formula** | `D_t = W_t / max_{s<=t}(W_s) - 1` |
| **Units** | decimal, non-positive |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | underwater curve |

**Edge cases.** The running peak includes starting wealth of 1.0, so a first-period loss is a real drawdown. Bounded in [-1, 0].

API: [`convexity.drawdown_series`](../reference/api.md#convexity.risk.drawdown_series)

### `max_drawdown`

Largest peak-to-trough decline over the sample.

| | |
| --- | --- |
| **Formula** | `MDD = min_t(D_t)` |
| **Units** | decimal, non-positive |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | MDD, maximum drawdown |

**Edge cases.** Exactly 0.0 when the series never falls below its starting wealth -- a real result, not a missing one. Measured from the running peak, not from an interim level.

API: [`convexity.max_drawdown`](../reference/api.md#convexity.risk.max_drawdown)

### `drawdown_episodes`

Distinct drawdown episodes with dates, depth and recovery.

| | |
| --- | --- |
| **Formula** | `Episodes between successive returns to the running peak.` |
| **Units** | list of DrawdownEpisode |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** An episode open at the end of the sample reports recovery=None rather than imputing a recovery that did not happen.

API: [`convexity.drawdown_episodes`](../reference/api.md#convexity.risk.drawdown_episodes)

### `average_drawdown`

Mean depth across distinct drawdown episodes.

| | |
| --- | --- |
| **Formula** | `mean(depth of each episode)` |
| **Units** | decimal, non-positive |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Averages over episodes, not observations; averaging the underwater curve instead gives the pain index. Zero when no episodes exist.

API: [`convexity.average_drawdown`](../reference/api.md#convexity.risk.average_drawdown)

### `ulcer_index`

Quadratic mean of the underwater curve.

| | |
| --- | --- |
| **Formula** | `UI = sqrt( mean(D_t^2) )` |
| **Units** | decimal, non-negative |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Never below the pain index (power-mean inequality); equal only when the underwater curve is flat. Zero when never underwater.

**References**

- Martin, P. and McCann, B. (1989). The Investor's Guide to Fidelity Funds.

API: [`convexity.ulcer_index`](../reference/api.md#convexity.risk.ulcer_index)

### `pain_index`

Mean depth of the underwater curve.

| | |
| --- | --- |
| **Formula** | `PI = mean(|D_t|)` |
| **Units** | decimal, non-negative |
| **Annualisation** | none |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Zero when never underwater.

API: [`convexity.pain_index`](../reference/api.md#convexity.risk.pain_index)

## Ratio

Risk-adjusted performance. Each ratio accepts a scalar rate or target (annual by default) or a time-varying Series, aligned with a backward as-of join that cannot use future information.

The three ratios do **not** share a numerator convention. Sharpe and Sortino use arithmetic annualised excess; Calmar uses a geometric one. This is deliberate and is stated on each entry.

### `sharpe_ratio`

Annualised excess return per unit of total volatility.

| | |
| --- | --- |
| **Formula** | `S = m * mean(r - f) / ( sigma(r - f) * sqrt(m) )` |
| **Units** | dimensionless, per year |
| **Annualisation** | Numerator scales by m, denominator by sqrt(m). Excess is computed per period and then annualised, so a time-varying risk-free series is handled correctly rather than reduced to its mean. |
| **Requires** | risk_free (scalar annual, or aligned Series) |
| **Minimum sample** | 2 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Arithmetic, not geometric: the numerator is a mean excess scaled by m, as Sharpe defined it. Zero denominator gives +/-inf by sign, or nan when the numerator is also zero.

**References**

- Sharpe, W. F. (1966). Mutual Fund Performance. The Journal of Business, 39(1), 119-138.
- Sharpe, W. F. (1994). The Sharpe Ratio. The Journal of Portfolio Management, 21(1), 49-58.

API: [`convexity.sharpe_ratio`](../reference/api.md#convexity.performance.sharpe_ratio)

### `sortino_ratio`

Annualised excess return per unit of downside deviation.

| | |
| --- | --- |
| **Formula** | `Sortino = m * mean(r - MAR) / ( DD * sqrt(m) )` |
| **Units** | dimensionless, per year |
| **Annualisation** | Numerator by m, denominator by sqrt(m). |
| **Requires** | mar (scalar annual by default, or aligned Series) |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Denominator convention is explicit (FULL by default, per Sortino and Price 1994). +inf when there is no downside and mean excess is positive; nan when there is no downside and mean excess is zero.

**References**

- Sortino, F. A. and Price, L. N. (1994). Performance Measurement in a Downside Risk Framework. The Journal of Investing, 3(3), 59-64.

API: [`convexity.sortino_ratio`](../reference/api.md#convexity.performance.sortino_ratio)

### `calmar_ratio`

Annualised excess return over maximum drawdown.

| | |
| --- | --- |
| **Formula** | `Calmar = (R_ann - f_ann) / |MDD|` |
| **Units** | dimensionless, per year |
| **Annualisation** | The numerator is a GEOMETRIC annualised return, unlike Sharpe and Sortino which use arithmetic means. This follows the ratio's origin as a return-over-worst-loss measure, where the compounded outcome is the quantity of interest. |
| **Requires** | risk_free (optional; 0.0 by default, matching the classic form) |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |
| **Also known as** | MAR ratio (with lookback=None) |

**Edge cases.** lookback_periods is applied BEFORE the drawdown is computed, so the drawdown is the worst decline within the window, not an earlier one the window excludes. The classic definition uses a trailing 36 months; None (default) uses the full sample, making this the MAR ratio. +inf when there is no drawdown and the return is positive.

**References**

- Young, T. W. (1991). Calmar Ratio: A Smoother Tool. Futures, 20(1).

API: [`convexity.calmar_ratio`](../reference/api.md#convexity.performance.calmar_ratio)

### `rolling_sharpe`

Sharpe ratio over a rolling window.

| | |
| --- | --- |
| **Formula** | `sharpe_ratio applied to each trailing window` |
| **Units** | dimensionless, per year |
| **Annualisation** | As sharpe_ratio. |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Windows shorter than min_periods yield nan rather than a value computed from a partial window. A sparse rate Series is passed whole to the as-of alignment, never reindexed onto the window.

API: [`convexity.rolling_sharpe`](../reference/api.md#convexity.performance.rolling_sharpe)

### `rolling_sortino`

Sortino ratio over a rolling window.

| | |
| --- | --- |
| **Formula** | `sortino_ratio applied to each trailing window` |
| **Units** | dimensionless, per year |
| **Annualisation** | As sortino_ratio. |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Incomplete windows yield nan.

API: [`convexity.rolling_sortino`](../reference/api.md#convexity.performance.rolling_sortino)

### `rolling_calmar`

Calmar ratio over a rolling window.

| | |
| --- | --- |
| **Formula** | `calmar_ratio applied to each trailing window` |
| **Units** | dimensionless, per year |
| **Annualisation** | As calmar_ratio. |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** The window IS the Calmar lookback. Incomplete windows yield nan.

API: [`convexity.rolling_calmar`](../reference/api.md#convexity.performance.rolling_calmar)

## Benchmark

Benchmark-relative analytics.

### `tracking_error`

Standard deviation of active return against a benchmark.

| | |
| --- | --- |
| **Formula** | `TE = sigma(r_t - b_t) * sqrt(m)` |
| **Units** | decimal |
| **Annualisation** | Square-root-of-time when annualise=True. |
| **Requires** | benchmark returns |
| **Minimum sample** | 2 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Zero against itself. A constant offset gives zero: it measures the variability of the gap, not its level. No overlap raises NoOverlapError.

API: [`convexity.tracking_error`](../reference/api.md#convexity.risk.tracking_error)

## Convention

Convention utilities. These are public because the conventions are part of the result: a caller who cannot inspect them cannot know what a number means.

### `annual_to_period_rate`

Convert an annual rate to the return earned over one period.

| | |
| --- | --- |
| **Formula** | `SIMPLE: r/m | COMPOUNDED: (1+r)^(1/m) - 1 | CONTINUOUS: exp(r/m) - 1` |
| **Units** | decimal per period |
| **Annualisation** | Inverse of period_to_annual_rate. |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** For a positive rate the conventions order continuous > simple > compounded. COMPOUNDED requires r > -1.0. Treating an annual rate as a period return is the classic Sharpe-inflation bug this prevents.

API: [`convexity.annual_to_period_rate`](../reference/api.md#convexity.conventions.compounding.annual_to_period_rate)

### `period_to_annual_rate`

Convert a period rate to an annual rate.

| | |
| --- | --- |
| **Formula** | `Exact inverse of annual_to_period_rate under the same convention.` |
| **Units** | decimal per year |
| **Annualisation** | n/a |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Round-trips with annual_to_period_rate to floating tolerance.

API: [`convexity.period_to_annual_rate`](../reference/api.md#convexity.conventions.compounding.period_to_annual_rate)

### `year_fraction`

Year fraction between two dates under a day-count convention.

| | |
| --- | --- |
| **Formula** | `ACT/360: actual_days / 360 | ACT/365F: actual_days / 365` |
| **Units** | years |
| **Annualisation** | n/a |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Reversed dates raise rather than returning a negative fraction. Times of day are normalised away: this is a calendar-day convention. ACT/365F ignores the leap day in its denominator, so a full leap year exceeds 1.

API: [`convexity.year_fraction`](../reference/api.md#convexity.conventions.daycount.year_fraction)

### `infer_frequency`

Conservatively infer observation frequency from a DatetimeIndex.

| | |
| --- | --- |
| **Formula** | `Median gap matched against documented spacing bands.` |
| **Units** | FrequencyInference |
| **Annualisation** | n/a |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Returns frequency=None with a reason rather than rounding an unrecognised spacing to the nearest band. Reports a confidence score and the evidence behind it. Business daily is distinguished from calendar daily by weekend presence, not gap size.

API: [`convexity.infer_frequency`](../reference/api.md#convexity.conventions.frequency.infer_frequency)

### `resolve_annualisation`

Resolve an annualisation factor under documented precedence.

| | |
| --- | --- |
| **Formula** | `periods_per_year > Frequency > inference from index` |
| **Units** | Annualisation |
| **Annualisation** | n/a |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Raises FrequencyInferenceError when no route yields an answer, or when inference is below the confidence threshold. Never falls back to 252. The result records which route produced it.

API: [`convexity.resolve_annualisation`](../reference/api.md#convexity.conventions.frequency.resolve_annualisation)

### `align_asof`

Align a source series onto a target index, backward-looking only.

| | |
| --- | --- |
| **Formula** | `For each target date, the latest source observation at or before it.` |
| **Units** | as source |
| **Annualisation** | n/a |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** Never looks forward, which is what makes it safe for risk-free rates and benchmarks. Supports max_staleness and publication_lag. A target before any observation is nan; no target matching raises.

API: [`convexity.align_asof`](../reference/api.md#convexity.alignment.align_asof)

### `align_series`

Align two series on their common index.

| | |
| --- | --- |
| **Formula** | `Inner join on the shared index.` |
| **Units** | as inputs |
| **Annualisation** | n/a |
| **Minimum sample** | 1 |
| **Status** | stable |
| **Added in** | 0.1.0 |

**Edge cases.** No value is forward-filled: a gap removes the date from both rather than borrowing a neighbour. No overlap raises rather than returning an empty result.

API: [`convexity.align_series`](../reference/api.md#convexity.alignment.align_series)
