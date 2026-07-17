# Roadmap

This roadmap records what is deferred and to which release. Nothing is silently
dropped: if an area is not in a release, it is listed here with a target.

Targets are intentions, not commitments. `convexity` is maintained by one person.

## Shipped

### 0.1.0 — computational foundations, rates, and the data layer

- Conventions, returns, risk, drawdown, and the Sharpe/Sortino/Calmar ratios with
  scalar and time-varying rate support.
- **Risk-free-rate subsystem:** `RateQuote`, `RiskFreeSeries`, `ZeroCurve`, and
  `RiskFreePolicy`, carrying currency, tenor, quote date, compounding, day count,
  instrument, source, and staleness, with look-ahead-free alignment.
- **Data provider layer:** capability-based protocols, a registry, a
  provenance-bearing envelope, an atomic offline-capable cache, and a retrying
  transport. Ships the key-free U.S. Treasury Fiscal Data rate provider and the
  optional research-only yfinance adapter.
- Metric registry, full CI, release automation.

See [CHANGELOG.md](CHANGELOG.md).

## Planned

### 0.2.0 — portfolio, more providers

**Portfolio analytics**
- Portfolio return from weights, exposure, leverage, turnover
- Marginal and component contribution to volatility, percentage risk contribution
- Diversification ratio, Herfindahl-Hirschman index, effective number of positions
- Portfolio beta and tracking error

**More rate/economic providers**
- ECB Data Portal (EUR, no API key)
- FRED (economic series, API key; optional keyed extra)
- Each with terms, licence, attribution and commercial-use status in the provider
  matrix before it ships

### 0.3.0 — fixed income

- Remaining day counts: ACT/ACT ISDA, 30/360 US, 30E/360
- Cash-flow schedules, accrued interest, clean and dirty price
- Yield to maturity with solver diagnostics; current yield
- Macaulay, modified and money duration; DV01/PVBP
- Convexity and duration-convexity approximation
- Discount factor, zero rate, par rate, forward rate conversions
- Zero-curve bootstrap from validated instruments

SciPy becomes a runtime dependency here, when a genuine solver first needs it.

### 0.4.0 — equity and commodities

- Equity: total-return construction, dividend yield, benchmark analytics,
  capture ratios, valuation inputs where validated data exists
- Commodities: typed futures contracts and chains, curve validation,
  contango/backwardation, calendar spreads, basis, roll yield
- Continuous-futures construction with explicit roll rules (unadjusted,
  back-adjusted, ratio-adjusted), preserving roll metadata

This milestone lays the **futures term-structure foundation** — typed contract
and chain models, curve ordering and validation, spreads, basis, roll yield, and
carry decomposition — that the derivatives work below builds on.

### 0.5.0 — breadth

- VaR and expected shortfall (historical, parametric, Cornish-Fisher)
- Regression and factor analytics; up/down beta
- Attribution foundations
- Additional ratios: Omega, Treynor, information, Jensen alpha, capture spreads

### 0.6.0 — derivatives foundation (vanilla)

A separately specified and reviewed module. Room is deliberately left for it in
the architecture — the `data` provider protocols already anticipate a
`FuturesCurveProvider`, and the rate `ZeroCurve` supplies the discounting these
models need — so it slots in without disturbing the core.

Scope, each gated on a written and reviewed formula specification before it
ships, and each pure and network-free like the rest of the analytics core:

- **Futures and forwards:** fair value under cost-of-carry, basis and
  convenience-yield decomposition, calendar-spread analytics, continuous-series
  roll-return attribution — extending the 0.4.0 term-structure foundation.
- **European options:** payoffs, put-call parity, Black–Scholes–Merton price and
  analytical Greeks (delta, gamma, vega, theta, rho).
- **Implied volatility:** a robust solver with convergence diagnostics and
  documented no-solution handling.
- **Volatility estimators:** historical/realised volatility (close-to-close and
  range-based), clearly separated from implied.
- **Binomial/lattice pricing:** a separately validated module for American-style
  and early-exercise payoffs.

Every model will carry the same guarantees as the rest of the library: an
explicit formula, stated conventions, edge-case policy, and independent
validation (put-call parity, Greeks by finite difference, lattice-to-analytic
convergence). None of it is investment advice or a pricing guarantee.

Exotic and path-dependent derivatives, stochastic-volatility calibration, and XVA
remain out of scope until their own reviewed specifications exist (see below).

### 1.0.0 — stability

Reached when: the public API is stable and documented; all shipped metrics have
independent validation; there is a sustained release history; an independent
review of the formulas has happened; and there are no unresolved critical
defects.

`1.0.0` is not a date. It is a bar.

## Not planned

Out of scope for the foreseeable future, regardless of demand:

- Trade execution, brokerage connectivity, order management, live trading
- A backtesting engine (the library may consume backtest output)
- Investment advice or portfolio recommendations
- A hosted data service, or redistribution of third-party market data
- Tick-level or real-time feeds
- **Exotic and path-dependent** derivatives, stochastic-volatility calibration,
  and XVA. Note this is narrower than before: *vanilla* futures, forwards, and
  European options are planned for 0.6.0 above. What stays out is the exotic tail
  — barriers, Asians, autocallables, model calibration — until each has its own
  reviewed specification.
- Scraping any source whose terms do not permit it
