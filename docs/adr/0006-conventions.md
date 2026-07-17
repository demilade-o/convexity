# 0006: Default conventions and the no-guessing rule

**Status:** Accepted
**Date:** 2026-07-17

## Context

Most quantitative-finance libraries answer questions the user did not ask. Given
monthly returns with no annualisation factor, they annualise as though the data
were daily. Asked for a Sortino ratio, they return *a* number without saying
which of two incompatible downside conventions produced it.

These are not edge cases. They are the normal path, and they are wrong silently
— which is the worst way to be wrong.

## Decision

### Nothing is inferred silently

`resolve_annualisation` follows a strict precedence: explicit
`periods_per_year`, then an explicit `Frequency`, then conservative inference
from a `DatetimeIndex`. **If none applies, it raises.** There is no fallback to
252.

Inference is isolated, testable, and returns a confidence score with the
evidence behind it (median gap, weekend share, gap range). Below a confidence
threshold it refuses rather than guessing, and the error names the diagnostics
and tells the caller to pass `periods_per_year`.

### Competing definitions are exposed, not resolved by fiat

**Downside deviation defaults to `FULL`** — divide the sum of squared shortfalls
by total `n` — per Sortino and Price (1994). `DOWNSIDE_ONLY` divides by the
count below target.

They differ by `sqrt(n / n_below)`. On a series with one bad month in twelve,
that is a factor of 3.46. This is the single most common source of disagreement
between Sortino implementations, so both are available, the default is
documented with its citation, and a test asserts they diverge by exactly the
predicted factor.

### Returns are decimals

`0.01` is 1%. Everywhere. A value of `5` is taken as a 500% return, not 5%: the
library cannot distinguish a genuine 500% return from a percentage-point
mistake, so it does not try.

### A scalar rate is annual

`risk_free=0.05` means 5% per year, converted to a period rate under a named
compounding convention. Pass `risk_free_is_annual=False` for an already-periodic
rate.

Defaulting to annual is the right call because that is how rates are quoted.
Treating a 5% annual bill yield as a 5% *daily* return inflates a Sharpe ratio
beyond recognition, and it is the classic version of this bug.

### Numerators differ between ratios, deliberately

Sharpe and Sortino use **arithmetic** annualised numerators, as defined. Calmar
uses a **geometric** one, following its origin as a return-over-worst-loss
measure where the compounded outcome is what matters. Both are documented at the
call site and in the registry, because a reader would otherwise reasonably assume
they match.

### Zero denominators return, they do not raise

`+/-inf` by the numerator's sign; `nan` when the numerator is zero too. A series
with no downside is a legitimate sample, not a caller error.

This requires care: `np.std` over identical floats returns ~1e-18, not `0.0`, so
a naive implementation divides by dust and reports ~1e16 instead of `inf`.
`risk.exact_std` checks the input's range rather than trusting the reduction.

## Consequences

The API has more parameters than a library that guesses. That is the trade, and
it is deliberate: the parameters are the documentation of what the number means.

Changing any default here is a **breaking change** even without a signature
change, because it silently alters users' results. See ADR 0005.
