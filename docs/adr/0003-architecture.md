# 0003: Layered core with no I/O in analytics

**Status:** Accepted
**Date:** 2026-07-17

## Context

The library must be usable in notebooks, backtests, services and scheduled jobs.
Users must be able to trust that calling a metric does not reach the network:
that trust underpins reproducibility, offline use, and test determinism.

## Decision

A `src` layout with strictly directed layers, highest to lowest:

```
performance -> risk -> alignment -> returns -> conventions -> validation -> exceptions
```

Higher layers may import lower ones; never the reverse. Data providers sit
outside this stack entirely and may depend on it, never the other way round.

**This is enforced, not documented.** `import-linter` runs in CI with two
contracts:

1. the layers above are acyclic and directed downwards;
2. no analytics module may import `httpx`, `socket`, `urllib`, `requests` or
   `yfinance`.

The test suite additionally runs with `--disable-socket`, so any accidental
network call fails loudly rather than passing in CI and breaking for a user on a
plane.

## Alternatives considered

**Documenting the layering in a contributing guide.** Rejected. "Analytics never
touch the network" is a product guarantee users rely on. A guarantee enforced
only by reviewer attention is a guarantee that will be broken by the first
plausible-looking pull request, and probably not noticed for a release or two.

**A single flat module.** Simpler initially, but circular imports become
inevitable as the surface grows, and there is then no mechanical way to state
what may depend on what.

**pandas accessors** (`df.cx.sortino()`). Rejected for the first stable release:
accessor namespaces are a global, collision-prone resource, and the value over a
plain function is small.

## Consequences

`convexity.registry` and `convexity._diagnostics` sit outside the layer contract
because they are metadata rather than analytics.

Adding a provider that an analytics module needs is impossible by construction —
which is the point. Data flows in as a plain Series from the caller.

Importing `convexity` touches only NumPy and pandas.
