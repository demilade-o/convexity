# 0008: Scope amendment — Python floor and 0.1.0 contents

**Status:** Accepted
**Date:** 2026-07-17
**Approved by:** project owner

## Context

This ADR records two owner-approved amendments to the original build
specification. Both change what a reader should expect from `0.1.0`, so they are
recorded rather than absorbed silently.

## Amendment 1: Python 3.12–3.14, not 3.11–3.14

### Reason

The scientific stack has moved past 3.11. Verified against the PyPI JSON API on
**2026-07-17**:

| Package | Latest | `requires_python` |
| --- | --- | --- |
| NumPy | 2.5.1 | `>=3.12` |
| SciPy | 1.18.0 | `>=3.12` |
| pandas | 3.0.3 | `>=3.11` |

NumPy **2.4.6** is the last release supporting 3.11; 2.5.0 raised the floor.
This follows the Scientific Python SPEC 0 deprecation cadence.

Supporting 3.11 was still technically possible — the resolver would pin NumPy
≤2.4.6 there — but it would mean one CI job permanently testing a frozen
dependency set that no longer receives fixes, while every other job tested
something else. That job's green tick would mean progressively less over time.

Python 3.11 remains in security-only support until 2027-10
(<https://devguide.python.org/versions/>, accessed 2026-07-17), so users on it
are on a maintenance track already.

### Decision

`requires-python = ">=3.12"`. The CI matrix tests 3.12, 3.13 and 3.14 on Linux,
plus the oldest and newest on macOS and Windows.

## Amendment 2: 0.1.0 covers foundations; other domains are deferred

### Reason

The full specification spans returns, performance, risk, portfolio,
fixed-income, equity, commodity and rate analytics, plus a provider subsystem
and full project infrastructure, at 95%/90% branch coverage with independent
validation of every formula.

Attempting all of it at once produces thin validation everywhere — which is the
failure mode the specification most wants to avoid, and worse than a smaller
release done properly. Correctness before coverage of surface area.

### Decision

**In scope for 0.1.0:** the conventions layer, returns, dispersion, downside and
drawdown risk, the Sharpe/Sortino/Calmar ratios with scalar and time-varying
rate support, alignment with point-in-time integrity, the metric registry, and
complete project infrastructure.

**Deferred, with targets** — recorded in `ROADMAP.md` and in the traceability
matrix as deferred-with-target, never dropped:

| Area | Target |
| --- | --- |
| Risk-free-rate subsystem, provider protocol, Treasury/ECB/yfinance adapters | 0.2.0 |
| Portfolio analytics | 0.2.0 |
| Fixed income, remaining day counts, curve bootstrap | 0.3.0 |
| Equity and commodity analytics, futures curves, continuous series | 0.4.0 |
| VaR/ES, factor and regression analytics, further ratios | 0.5.0 |

### Consequences

`0.1.0` is honestly scoped: the README's capability table marks deferred areas as
planned rather than implied, and `CHANGELOG.md` lists the limitations explicitly.

The day-count module ships only ACT/360 and ACT/365F — the two the rate
subsystem needs. The rest arrive with the fixed-income module that consumes
them. A convention that is not implemented is **absent from the `DayCount` enum**
rather than approximated by a neighbouring one.
