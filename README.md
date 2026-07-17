# convexity

**Quantitative finance analytics with explicit conventions, documented formulas, and honest failure modes.**

[![License: Apache 2.0](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13%20%7C%203.14-blue.svg)](https://devguide.python.org/versions/)

> **Status: 0.1.0 — early development.** The public API is unstable while the
> version is `0.x` and may change between minor releases. See [ROADMAP.md](ROADMAP.md)
> for what is implemented and what is planned.

## Why another one?

Most performance-analytics libraries will quietly answer a question you did not
ask. Pass them monthly returns and they may annualise as though the data were
daily. Ask for a Sortino ratio and you will get *a* number, without being told
which of two incompatible downside-deviation conventions produced it. Hand them
a 5% annual bill yield where a periodic return was expected and the Sharpe ratio
will be spectacular, and wrong.

`convexity` is built on the opposite instinct:

- **Nothing is inferred silently.** Annualisation, compounding, day count, the
  risk-free convention, and the missing-data policy are all parameters. When a
  convention cannot be resolved, the library raises with diagnostics rather than
  assuming one. There is no fallback to 252.
- **Competing definitions are exposed, not resolved by fiat.** Where the
  literature disagrees — as it does for downside deviation — you choose the
  variant, and the default is documented with its reason and its citation.
- **Analytics never touch the network.** Importing this package or calling any
  metric performs no I/O. This is enforced in CI, where the entire test suite
  runs with sockets disabled.
- **Failures are loud.** Invalid input raises a specific, actionable exception.
  The library will not return a plausible but meaningless number.

## Install

```bash
pip install convexity
```

Requires Python 3.12–3.14. The core depends only on NumPy and pandas.

Optional extras:

```bash
pip install "convexity[providers]"   # official key-free rate/economic data adapters
pip install "convexity[yahoo]"       # research/personal-use only — see Data and legal
pip install "convexity[all]"
```

## Five-minute start

```python
import pandas as pd
import convexity as cx

returns = pd.Series(
    [0.021, -0.013, 0.034, 0.008, -0.027, 0.019, 0.011, -0.005, 0.024, 0.002, -0.018, 0.030],
    index=pd.date_range("2024-01-31", periods=12, freq="ME"),
)

# Frequency is explicit. Omit periods_per_year and the library will infer it from
# the index — but only if the index supports a confident answer, and it will tell
# you what it concluded rather than guessing.
cx.annualised_return(returns, periods_per_year=12)   # 0.0946...
cx.volatility(returns, periods_per_year=12)          # 0.0704...
cx.max_drawdown(returns)                             # -0.027

# A scalar risk-free rate is an ANNUAL rate by default and is converted to a
# period rate for you, under a compounding convention you can name.
cx.sharpe_ratio(returns, risk_free=0.05, periods_per_year=12)

# A time-varying rate works identically. It is aligned with a backward as-of
# join, so a rate published after a measurement date can never inform it.
rates = pd.Series([0.053, 0.048], index=pd.to_datetime(["2024-01-01", "2024-07-01"]))
cx.sortino_ratio(returns, mar=rates, periods_per_year=12)
```

Every metric documents its formula, units, conventions, edge cases, and
references. Start with the [metric catalogue](docs/metrics/) and the
[concepts guide](docs/concepts/).

## What it does

| Area | Status |
| --- | --- |
| Returns, wealth, annualisation, CAGR | Implemented |
| Dispersion, downside, drawdown, Ulcer/pain | Implemented |
| Sharpe, Sortino, Calmar (+ rolling) | Implemented |
| Risk-free rates: models, conversion, as-of alignment | Implemented |
| Data providers: protocol, cache, provenance | Implemented |
| Portfolio analytics | Planned — see [ROADMAP.md](ROADMAP.md) |
| Fixed income, curves | Planned |
| Equity, commodities, futures curves | Planned |

Out of scope for the foreseeable future: order execution, brokerage
connectivity, live trading, backtesting engines, and hosted data services.

## Data and legal

This project **distributes no market or economic data**. Optional adapters
retrieve data at runtime, directly from the provider, on behalf of the user.

Free to access is not the same as openly licensed. Data retrieved through an
adapter is governed by that provider's terms and by any third-party rights in
the underlying series — rights this project's licence neither grants nor
extends. The [provider matrix](docs/providers/provider-matrix.md) records
authentication, terms, licensing, attribution, and commercial-use status for
each adapter, and marks unknown legal status as unknown rather than inferring it.

The Yahoo adapter is **research and personal use only**. It is not affiliated
with or endorsed by Yahoo, and it is never a test or build dependency.

**This software is a research and analysis tool. It is not investment advice,
and it makes no claim of regulatory compliance or valuation accuracy.**

## Documentation

- [Concepts](docs/concepts/) — returns, annualisation, risk-free rates, alignment, point-in-time data
- [Metric catalogue](docs/metrics/) — formula, conventions, edge cases, references per metric
- [Providers](docs/providers/provider-matrix.md) — terms, attribution, limitations
- [API reference](docs/reference/)
- [Architecture decisions](docs/adr/)

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md) for setup,
tests, style, and the evidence standard for new metrics — every formula needs a
reference or a hand-worked derivation, not a citation of another library.

This project uses the [Developer Certificate of Origin](https://developercertificate.org/).
Sign off your commits with `git commit -s`.

By participating you agree to the [Code of Conduct](CODE_OF_CONDUCT.md).

## Citation

If you use `convexity` in research, please cite it. See [CITATION.cff](CITATION.cff).

## Security

Report vulnerabilities privately — see [SECURITY.md](SECURITY.md). Please do not
open a public issue for a security report.

## Licence

[Apache License 2.0](LICENSE). See [NOTICE](NOTICE) and
[THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
