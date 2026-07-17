# convexity

**Quantitative finance analytics with explicit conventions, documented formulas,
and honest failure modes.**

!!! warning "Not investment advice"
    This is a research and analysis tool. It is not investment advice, and it
    makes no claim of regulatory compliance or valuation accuracy.

## Why this exists

Most performance-analytics libraries will quietly answer a question you did not
ask. Pass monthly returns and they may annualise as though the data were daily.
Ask for a Sortino ratio and you get *a* number, without being told which of two
incompatible downside conventions produced it. Hand them a 5% annual bill yield
where a periodic return was expected and the Sharpe ratio will be spectacular,
and wrong.

`convexity` is built on the opposite instinct.

**Nothing is inferred silently.** Annualisation, compounding, day count, the
risk-free convention, and the missing-data policy are parameters. When a
convention cannot be resolved, the library raises with diagnostics rather than
assuming. There is no fallback to 252.

**Competing definitions are exposed, not resolved by fiat.** Where the
literature disagrees — as it does for downside deviation — you choose the
variant, and the default is documented with its reason and its citation.

**Analytics never touch the network.** Importing this package or calling any
metric performs no I/O. This is enforced: the architecture contract forbids
analytics modules from importing a networking library, and the entire test suite
runs with sockets disabled.

**Failures are loud.** Invalid input raises a specific, actionable exception.
The library will not return a plausible but meaningless number.

## Install

```bash
pip install convexity
```

Python 3.12–3.14. The core depends only on NumPy and pandas.

## Where to go next

- **[Five-minute start](getting-started.md)** — the shortest path to a number you
  can trust.
- **[Conventions](concepts/conventions.md)** — read this if a number surprises
  you. It almost always explains why.
- **[Metric catalogue](metrics/index.md)** — every metric, with its formula,
  units, annualisation and edge cases.
- **[Limitations](limitations.md)** — what this library does not do, and what it
  will not do.
