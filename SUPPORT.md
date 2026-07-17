# Support

## Before asking

Most questions about a surprising number are answered by the metric's own
documentation, which states the formula, the conventions, and the edge-case
policy: see the [metric catalogue](docs/metrics/index.md).

If a number looks wrong, the [conventions guide](docs/concepts/conventions.md)
is the fastest route. In our experience the cause is almost always one of:

- **The annualisation factor.** `periods_per_year` is explicit for a reason.
- **The risk-free rate being annual, not per-period.** A scalar `risk_free` is
  an *annual* rate by default and is converted for you. Passing an already-periodic
  rate without `risk_free_is_annual=False` understates it by a factor of `m`.
- **The downside-deviation convention.** `FULL` (the default) and
  `DOWNSIDE_ONLY` differ by `sqrt(n / n_below)`. Other libraries pick differently.
- **Calmar's geometric numerator**, where Sharpe and Sortino use arithmetic means.

## Where to ask

| I want to… | Go to |
| --- | --- |
| Ask how to do something | [Discussions](https://github.com/demilade-o/convexity/discussions) |
| Report a wrong number | [Incorrect metric issue](https://github.com/demilade-o/convexity/issues/new?template=metric_incorrect.yml) |
| Report a bug | [Bug report](https://github.com/demilade-o/convexity/issues/new?template=bug_report.yml) |
| Request a metric | [Metric request](https://github.com/demilade-o/convexity/issues/new?template=new_metric.yml) |
| Propose a data provider | [Provider request](https://github.com/demilade-o/convexity/issues/new?template=new_provider.yml) |
| Report a vulnerability | [Privately](SECURITY.md) — never a public issue |

## Helping us help you

Include the output of:

```python
import convexity
convexity.show_versions()
```

and a minimal reproduction with inline data. Please do not attach market data:
we cannot redistribute it, and a synthetic series almost always reproduces the
issue.

For a disputed number, tell us the value you expected **and where it comes from** —
a hand calculation, a textbook, a paper, or a vendor figure — plus the conventions
you assumed. Libraries legitimately disagree on conventions, and we need to tell a
real defect from a convention difference.

## What is not supported

This is a research and analysis tool. It is **not investment advice**, and we
cannot help you choose investments, interpret results as recommendations, or
validate a strategy.

## Response expectations

`convexity` is maintained by one person alongside other work. Issues are read,
but response times vary. A well-specified issue with a reproduction gets a
faster answer than a general question. Pull requests with tests are the fastest
route of all.
