# Requirements

Numbered, testable requirements for `convexity`. Each has a stable `REQ-*` ID
and is mapped to the tests that prove it in the
[traceability matrix](traceability.md).

Requirements marked **Deferred** carry a target release. Nothing is dropped
silently; see [ROADMAP.md](https://github.com/demilade-o/convexity/blob/main/ROADMAP.md).

## Conventions (REQ-CON)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-CON-001 | Annualisation resolves by strict precedence: explicit `periods_per_year`, then `Frequency`, then inference from a `DatetimeIndex`. | Implemented |
| REQ-CON-002 | When no annualisation route applies, raise with diagnostics. Never assume 252. | Implemented |
| REQ-CON-003 | Frequency inference is isolated, conservative, and returns a confidence score plus the evidence behind it. | Implemented |
| REQ-CON-004 | Inference below the confidence threshold refuses rather than guessing. | Implemented |
| REQ-CON-005 | Business-daily is distinguished from calendar-daily by evidence, not gap size alone. | Implemented |
| REQ-CON-006 | Frequency inference is independent of the index's datetime resolution. | Implemented |
| REQ-CON-007 | Annual↔period rate conversion supports simple, compounded and continuous compounding, and round-trips exactly. | Implemented |
| REQ-CON-008 | Day counts ACT/360 and ACT/365F with reference examples and leap-year boundary tests. | Implemented |
| REQ-CON-009 | Remaining day counts: ACT/ACT ISDA, 30/360 US, 30E/360. | **Deferred → 0.3.0** |

## Returns (REQ-RET)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-RET-001 | Simple and logarithmic returns from prices. | Implemented |
| REQ-RET-002 | Cumulative return and wealth index. | Implemented |
| REQ-RET-003 | Geometric annualised return (CAGR from periodic returns). | Implemented |
| REQ-RET-004 | Arithmetic annualised mean return, separated from the geometric figure. | Implemented |
| REQ-RET-005 | CAGR from actual elapsed time, requiring no periods-per-year. | Implemented |
| REQ-RET-006 | Simple↔log conversion round-trips. | Implemented |
| REQ-RET-007 | Returns are decimals; `0.01` is 1%. | Implemented |
| REQ-RET-008 | Excess return against a scalar or an aligned series. | Implemented |
| REQ-RET-009 | Rolling and expanding returns. | **Deferred → 0.2.0** |
| REQ-RET-010 | Time-weighted and money-weighted return, IRR, XIRR. | **Deferred → 0.5.0** |

## Risk (REQ-RSK)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-RSK-001 | Variance and standard deviation with explicit `ddof`. | Implemented |
| REQ-RSK-002 | Annualised volatility, with the square-root-of-time assumption stated. | Implemented |
| REQ-RSK-003 | Downside deviation about a configurable target, with both denominator conventions exposed. | Implemented |
| REQ-RSK-004 | Upside deviation. | Implemented |
| REQ-RSK-005 | Drawdown series, underwater curve, maximum drawdown. | Implemented |
| REQ-RSK-006 | Drawdown episodes with start, trough, recovery, and duration. | Implemented |
| REQ-RSK-007 | Average drawdown across episodes. | Implemented |
| REQ-RSK-008 | Ulcer index and pain index. | Implemented |
| REQ-RSK-009 | Skewness and kurtosis with explicit Fisher/Pearson and bias settings. | Implemented |
| REQ-RSK-010 | Tracking error. | Implemented |
| REQ-RSK-011 | Historical, Gaussian and Cornish-Fisher VaR; expected shortfall. | **Deferred → 0.5.0** |

## Ratios (REQ-RAT)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-RAT-001 | Sharpe ratio, arithmetic form, clearly identified as such. | Implemented |
| REQ-RAT-002 | Sortino ratio with configurable target and an explicit downside convention. | Implemented |
| REQ-RAT-003 | Calmar ratio with an exact lookback and a stated max-drawdown definition. | Implemented |
| REQ-RAT-004 | MAR ratio (Calmar over the full sample). | Implemented |
| REQ-RAT-005 | Every ratio accepts scalar and time-varying rate/target inputs. | Implemented |
| REQ-RAT-006 | Rolling variants of each ratio. | Implemented |
| REQ-RAT-007 | Zero-denominator behaviour is documented policy, not incidental. | Implemented |
| REQ-RAT-008 | Ratios with competing definitions expose variants and document the default's reason. | Implemented |
| REQ-RAT-009 | Information, Treynor, Jensen alpha, Omega, capture ratios. | **Deferred → 0.5.0** |

## Alignment and point-in-time integrity (REQ-PIT)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-PIT-001 | Rate and benchmark alignment uses backward as-of logic and cannot use future information. | Implemented |
| REQ-PIT-002 | Forward-filling supports a maximum staleness. | Implemented |
| REQ-PIT-003 | A configurable publication lag models delayed availability. | Implemented |
| REQ-PIT-004 | Series alignment never borrows a neighbouring observation. | Implemented |
| REQ-PIT-005 | No overlap raises rather than returning an empty result. | Implemented |
| REQ-PIT-006 | Alignment is independent of datetime resolution. | Implemented |

## Validation and edge cases (REQ-VAL)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-VAL-001 | Missing-data policy is an enum, not a string, and is metric-appropriate. | Implemented |
| REQ-VAL-002 | A `DatetimeIndex` is required for time-dependent metrics; duplicates and non-monotonic order raise. | Implemented |
| REQ-VAL-003 | Non-finite values are rejected; infinities always. | Implemented |
| REQ-VAL-004 | Simple returns below -1.0 are rejected; exactly -1.0 is permitted. | Implemented |
| REQ-VAL-005 | Caller-owned objects are never mutated. | Implemented |
| REQ-VAL-006 | Empty and single-observation inputs behave per documented policy. | Implemented |
| REQ-VAL-007 | Constant and zero-volatility series behave per documented policy. | Implemented |
| REQ-VAL-008 | Errors are package-specific and actionable. | Implemented |

## Risk-free rates (REQ-RTE)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-RTE-001 | `RateQuote` carries value, date, currency, tenor, compounding, day count, instrument, source, and staleness. | Implemented |
| REQ-RTE-002 | An annual quote converts to a period return under a declared compounding convention. | Implemented |
| REQ-RTE-003 | `RiskFreeSeries` aligns onto a target calendar with backward as-of logic and no look-ahead. | Implemented |
| REQ-RTE-004 | Alignment honours `max_staleness` and a configurable `publication_lag`. | Implemented |
| REQ-RTE-005 | `RiskFreePolicy` refuses to convert across currencies silently. | Implemented |
| REQ-RTE-006 | `ZeroCurve` provides discount factors and forward rates with declared interpolation and stated extrapolation. | Implemented |
| REQ-RTE-007 | Rate distinctions (overnight, bill, constant-maturity, OIS) are modelled, not conflated. | Implemented |
| REQ-RTE-008 | Zero-curve bootstrap from market instruments. | **Deferred → 0.3.0** |

## Data providers (REQ-DAT)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-DAT-001 | Analytics make no network calls; enforced mechanically. | Implemented |
| REQ-DAT-002 | No credential, cache, or provider data is tracked or shipped. | Implemented |
| REQ-DAT-003 | Capability-based provider protocols with package-owned models. | Implemented |
| REQ-DAT-004 | Every fetch returns provenance. | Implemented |
| REQ-DAT-005 | Cache with atomic writes, offline mode, and no unsafe deserialisation. | Implemented |
| REQ-DAT-006 | Timeouts, bounded retries with backoff, rate-limit awareness. | Implemented |
| REQ-DAT-007 | At least one key-free official rate/economic provider. | Implemented |
| REQ-DAT-008 | yfinance optional, research/personal-use labelled, never a build dependency. | Implemented |
| REQ-DAT-009 | Further rate/economic providers (ECB, FRED). | **Deferred → 0.2.0** |

## Packaging and quality (REQ-PKG)

| ID | Requirement | Status |
| --- | --- | --- |
| REQ-PKG-001 | Builds reproducibly as wheel and sdist. | Implemented |
| REQ-PKG-002 | Installs and imports in a clean environment from each artefact. | Implemented |
| REQ-PKG-003 | `py.typed` ships. | Implemented |
| REQ-PKG-004 | CI covers Python 3.12–3.14 on Linux, macOS and Windows. | Implemented (defined; executes on a remote) |
| REQ-PKG-005 | Minimum declared dependencies are tested, not just the newest. | Implemented (defined) |
| REQ-PKG-006 | Coverage ≥95% computational core, ≥90% total, branch-based. | Implemented |
| REQ-PKG-007 | Ruff, strict mypy, architecture contracts pass. | Implemented |
| REQ-PKG-008 | Docs build with warnings as errors. | Implemented |
| REQ-PKG-009 | Dependency vulnerability audit and secret scanning. | Implemented (defined) |
| REQ-PKG-010 | Release uses PyPI Trusted Publishing/OIDC with no long-lived token. | Implemented (defined) |
| REQ-PKG-011 | Every public metric is registered in the catalogue. | Implemented |
| REQ-PKG-012 | Every public metric has independent validation. | Implemented |

**"Implemented (defined)"** means the configuration is complete and locally
verifiable where possible, but the job itself executes only on GitHub-hosted
infrastructure, which requires a remote that does not yet exist. See the
[release-candidate evidence report](release-candidate-evidence.md) for exactly
what has and has not been executed.
