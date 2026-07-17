# Architecture decision records

Decisions that are hard to reverse are recorded here: what was decided, what was
rejected, and why. Facts that can go stale carry a source URL and an access date.

| ADR | Decision | Status |
| --- | --- | --- |
| [0001](0001-project-name.md) | Distribution and import name: `convexity` | Accepted |
| [0002](0002-licence.md) | Apache-2.0 with DCO sign-off | Accepted |
| [0003](0003-architecture.md) | Layered core, no I/O in analytics | Accepted |
| [0004](0004-tooling.md) | uv, Hatchling, Ruff, mypy strict; NumPy + pandas only | Accepted |
| [0005](0005-versioning.md) | SemVer, PEP 440, static single-sourced version | Accepted |
| [0006](0006-conventions.md) | Default conventions and the no-guessing rule | Accepted |
| [0007](0007-provider-policy.md) | Key-free official providers first; yfinance optional | Accepted |
| [0008](0008-scope-amendment.md) | Python 3.12+; 0.1.0 scope | Accepted |
