# Roadmap

This roadmap records what is deferred and to which release. Nothing is silently
dropped: if an area is not in a release, it is listed here with a target.

Targets are intentions, not commitments. `convexity` is maintained by one person.

## Shipped

### 0.1.0 — computational foundations

Conventions, returns, risk, drawdown, and the Sharpe/Sortino/Calmar ratios with
scalar and time-varying rate support. Metric registry, full CI, release
automation. See [CHANGELOG.md](CHANGELOG.md).

## Planned

### 0.2.0 — rates, providers, portfolio

**Risk-free-rate subsystem**
- `RateQuote`, `RiskFreeSeries`, `RiskFreePolicy` carrying currency, tenor,
  quote convention, day count, compounding, source, and staleness
- Curve construction and maturity selection under a declared policy

**Data providers**
- Capability-based provider protocols, registry, and a cache with atomic writes
- U.S. Treasury Fiscal Data (USD, no API key)
- ECB Data Portal (EUR, no API key)
- Optional `convexity[yahoo]` research/personal-use adapter
- Provider matrix recording terms, licence, attribution and commercial-use status

**Portfolio analytics**
- Portfolio return from weights, exposure, leverage, turnover
- Marginal and component contribution to volatility, percentage risk contribution
- Diversification ratio, Herfindahl-Hirschman index, effective number of positions
- Portfolio beta and tracking error

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

### 0.5.0 — breadth

- VaR and expected shortfall (historical, parametric, Cornish-Fisher)
- Regression and factor analytics; up/down beta
- Attribution foundations
- Additional ratios: Omega, Treynor, information, Jensen alpha, capture spreads

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
- Exotic-derivative pricing, stochastic calibration, XVA
- Scraping any source whose terms do not permit it
