# Changelog

All notable changes to this project are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/) with
[PEP 440](https://peps.python.org/pep-0440/)-compatible version strings.

While the version is `0.x` the public API is explicitly unstable and may change
between minor releases. Changes to a **default convention** are treated as
breaking even when the signature is unchanged, because they silently change
users' numbers.

## [Unreleased]

Nothing yet.

## [0.1.0] — unreleased

First release. Computational foundations and the conventions layer that
everything else depends on, plus the risk-free-rate subsystem and a pluggable,
provenance-bearing data layer.

### Added

**Conventions**

- `Frequency`, `Annualisation`, `resolve_annualisation` with a documented
  precedence: explicit `periods_per_year`, then an explicit `Frequency`, then
  conservative inference from a `DatetimeIndex`. Raises with diagnostics when no
  route applies; there is no fallback to 252.
- `infer_frequency` returning a candidate, a confidence score, and the evidence
  behind it. Distinguishes business-daily from calendar-daily by weekend
  presence rather than gap size.
- `Compounding` (simple, compounded, continuous) with `annual_to_period_rate`
  and `period_to_annual_rate`, which round-trip exactly.
- `DayCount` (ACT/360, ACT/365F) and `year_fraction`.

**Returns**

- `simple_returns`, `log_returns`, `to_log_returns`, `to_simple_returns`
- `wealth_index`, `cumulative_return`
- `annualised_return` (geometric), `arithmetic_annualised_return`, `cagr`
  (from actual elapsed time, needing no periods-per-year)

**Risk**

- `drawdown_series`, `max_drawdown`, `drawdown_episodes`, `average_drawdown`
- `ulcer_index`, `pain_index`
- `volatility`, `downside_deviation`, `upside_deviation`
- `skewness`, `kurtosis` with explicit Fisher/Pearson and bias settings
- `tracking_error`

**Ratios**

- `sharpe_ratio`, `sortino_ratio`, `calmar_ratio`
- `rolling_sharpe`, `rolling_sortino`, `rolling_calmar`
- All accept a scalar (annual by default) or a time-varying rate/target Series,
  aligned with a backward as-of join that cannot use future information.

**Alignment**

- `align_series` (inner join, no forward-filling) and `align_asof`
  (backward-looking, with `max_staleness` and `publication_lag`).

**Risk-free rates** (`convexity.rates`)

- `RateQuote`, `RiskFreeSeries`, `ZeroCurve`, `RiskFreePolicy` — every rate
  carries its currency, tenor, quote date, compounding, day count, instrument,
  source, and staleness.
- Annual-quote-to-period-return conversion under a declared compounding
  convention; alignment onto a return calendar with no look-ahead.
- `RiskFreePolicy` refuses to convert across currencies silently.
- `ZeroCurve` discount factors and forward rates with declared interpolation and
  stated flat extrapolation.

**Data providers** (`convexity.data`)

- Capability-based provider protocols (`RiskFreeRateProvider`,
  `EconomicSeriesProvider`, `PriceHistoryProvider`), a `ProviderRegistry`, and a
  `DataEnvelope` that binds every fetch to an immutable `Provenance` record.
- A `FileCache` with atomic writes, an offline mode, traversal-safe keys, and no
  `pickle`; a retrying transport with bounded jittered backoff that honours
  `Retry-After`.
- `TreasuryFiscalDataProvider` — U.S. Treasury Fiscal Data, official and
  requiring **no API key**, returning a USD `RiskFreeSeries`.
- Optional `YahooFinanceProvider` behind `convexity[yahoo]`, labelled
  research/personal-use only and never a test or build dependency.
- Importing `convexity` performs no network setup and loads no HTTP client; the
  architecture contracts forbid any analytics or rate module from importing a
  provider.

**Infrastructure**

- Machine-readable metric registry, tested against the public API so the
  catalogue cannot drift.
- `show_versions()` for bug reports.
- Apache-2.0, DCO, full CI across Python 3.12–3.14 on Linux, macOS and Windows.

### Conventions chosen

- **Downside deviation defaults to `FULL`** (divide by total `n`), per Sortino
  and Price (1994). `DOWNSIDE_ONLY` is available. The two differ by
  `sqrt(n / n_below)`; several popular libraries use the latter.
- **Sharpe and Sortino use arithmetic annualised numerators**, as defined.
  **Calmar uses a geometric one**, following its origin as a
  return-over-worst-loss measure.
- **Zero-denominator policy**: `+/-inf` by the numerator's sign, `nan` when the
  numerator is also zero. A series with no downside is a legitimate sample, not
  a caller error, so these return rather than raise.
- **A scalar `risk_free`/`mar` is an annual rate by default** and is converted to
  a period rate under a named compounding convention.

### Known limitations

- Portfolio, fixed-income, equity and commodity analytics are not in this
  release. See [ROADMAP.md](ROADMAP.md) for targets.
- The shipped rate provider returns Treasury *average* interest rates on
  outstanding debt — a monthly short-rate proxy, not a new-issue yield. The
  caveat is surfaced in each response's provenance.
- ECB and FRED providers, and zero-curve bootstrapping from market instruments,
  are planned for later releases.
- Only ACT/360 and ACT/365F day counts ship; the rest arrive with fixed income.
- Python 3.11 is not supported: NumPy ≥2.5 and SciPy ≥1.18 require ≥3.12.

[Unreleased]: https://github.com/demilade-o/convexity/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/demilade-o/convexity/releases/tag/v0.1.0
