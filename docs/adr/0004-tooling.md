# 0004: Tooling and runtime dependencies

**Status:** Accepted
**Date:** 2026-07-17

## Context

Every runtime dependency is imposed on every user of the library, forever, and
is a supply-chain surface. Development tooling is imposed only on contributors.
The two deserve different thresholds.

## Decision

**Runtime: NumPy and pandas. Nothing else.**

**SciPy is deliberately not a dependency.** The statistics this release computes
— skewness and kurtosis with explicit Fisher/Pearson and bias settings — are
plain moment arithmetic. Implementing them directly is around twenty lines, and
gives exact control over the bias convention rather than inheriting
`scipy.stats` defaults that we would then have to document as ours. SciPy is a
large dependency to impose on a user who wants a Sortino ratio.

SciPy earns its place when a genuine solver does — yield to maturity, implied
volatility — which is `0.3.0`. Recorded in `ROADMAP.md`.

HTTP clients live behind the `providers` extra. Importing this package must not
pull a networking stack into an environment doing pure arithmetic.

**Development:**

| Tool | Role | Note |
| --- | --- | --- |
| uv | environments, locking, resolution | also provides the interpreters |
| Hatchling | build backend | pure-Python wheel |
| Ruff | format + lint | replaces black, isort, flake8, bandit, pydocstyle |
| mypy | strict type checking | over `src` **and** `tests` |
| pytest | tests | `--disable-socket` |
| Hypothesis | property tests | |
| import-linter | architecture contracts | |
| MkDocs Material + mkdocstrings | documentation | |

## Notable choices

**mypy strict over tests too, with no per-module override.** Exempting tests is
common. Rejected: a test passing the wrong type to a metric is exactly the bug a
type checker should catch, and exempting tests hides it.

**Ruff selects `ANN`, `D` and `S`.** A typed, documented public API is a product
requirement here, not a style preference, so the linter enforces it.

**`filterwarnings = ["error"]`.** A NumPy warning is how silent wrongness
announces itself. Scrolling past one is not an option.

**Branch coverage, with two thresholds** — 95% core, 90% total. The validation
layer is almost entirely branches; line coverage would report a policy as tested
when only one side of it ever ran.

**pre-commit uses local `uv`-driven hooks**, not mirrored remote repos with their
own `rev` pins. The usual pattern creates a second source of truth: pre-commit
pins Ruff at one version, `uv.lock` at another, and contributors get "passes
locally, fails in CI". Driving hooks through `uv run` means versions come from
`uv.lock` — exactly what CI resolves.

## Consequences

Skewness and kurtosis are our code and need our tests. Both are covered,
including the zero-variance case where the moment ratio is `0/0` and we return
`nan` rather than an arbitrary number.

Minimum declared versions (`numpy>=2.1`, `pandas>=2.2`) are a promise, so CI has
a job resolving `--resolution lowest-direct` to prove it. Testing only the newest
resolution would never check the floor.
