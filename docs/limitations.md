# Limitations

What this library does not do, cannot do, and will not do. Read this before
relying on it.

## Not investment advice

`convexity` is a research and analysis tool. It computes statistics from numbers
you supply. It does not know whether those numbers are right, whether the
strategy that produced them is sound, or whether anything it reports should
inform a decision.

It makes **no claim** of regulatory compliance, audited valuation, or accuracy
for any particular purpose.

## Not in this release

| Area | Target |
| --- | --- |
| Risk-free-rate subsystem and data providers | 0.2.0 |
| Portfolio analytics | 0.2.0 |
| Fixed income, remaining day counts, curves | 0.3.0 |
| Equity and commodity analytics, futures curves | 0.4.0 |
| VaR, expected shortfall, factor analytics | 0.5.0 |

Only ACT/360 and ACT/365F day counts ship. A convention that is not implemented
is **absent from the `DayCount` enum** rather than approximated by a neighbour.

## Never in scope

No amount of demand will change these:

- Trade execution, brokerage connectivity, order management, live trading
- A backtesting engine — the library may consume backtest output, not produce it
- Investment advice or portfolio recommendations
- A hosted data service, or redistribution of third-party market data
- Tick-level or real-time feeds
- Scraping any source whose terms do not permit it

## Statistical limitations

**Annualised volatility is a convention.** `sqrt(m)` scaling assumes returns are
serially uncorrelated and identically distributed. Real return series are
usually neither. The number is comparable and conventional; it is not a
measurement of anything your data actually did.

**Short samples annualise badly.** Raising growth to `m/n` extrapolates. Two
observations of `[0.0, 1.0]` annualise geometrically to 6300% at `m=12`. That is
arithmetically correct and financially meaningless. The library computes what you
ask for; judging whether the sample supports the question is your job.

**Ratios are sample statistics, not estimates with confidence intervals.** A
Sharpe ratio from 12 monthly observations is extremely noisy. `convexity` does
not currently report standard errors, so it cannot tell you that.

**Skewness and kurtosis need far more data than people assume.** Fourth moments
from small samples are dominated by their extremes.

## Numerical limitations

- Floating-point arithmetic. Round trips agree to ~1e-9, not exactly.
- Compounded wealth can overflow for extreme inputs over long horizons.
- A constant series has exactly zero dispersion here, which is a deliberate
  correction of a floating-point artefact rather than a mathematical claim about
  your data.

## Point-in-time limitations

Backward-looking alignment is necessary, not sufficient. It does **not** address:

- **Revisions.** Economic series are revised; a revised value used before the
  revision existed is still look-ahead. Vintage support arrives with providers.
- **Survivorship bias.** A property of your universe.
- **Fundamentals timing.** Never align a later filing to an earlier date.

## What "verified" means here

The [release-candidate evidence report](development/release-candidate-evidence.md)
distinguishes four things carefully:

1. Verified locally, on macOS, with output shown.
2. Configuration complete but **not executed** — Linux and Windows CI jobs
   require a remote that does not yet exist.
3. Owner-only external settings — branch protection, PyPI Trusted Publishing.
4. Not done.

Cross-platform CI is currently **category 2**. The matrix is defined and
reviewable; it has not run. Do not read the presence of a workflow file as
evidence that it passes.

## Reporting a limitation

If you hit one that is not listed, that is worth an issue. See
[SUPPORT.md](https://github.com/demilade-o/convexity/blob/main/SUPPORT.md).
