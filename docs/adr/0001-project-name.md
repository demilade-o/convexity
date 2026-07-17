# 0001: Distribution and import name

**Status:** Accepted
**Date:** 2026-07-17

## Context

The package needs a distribution name on PyPI and a valid import name. It must
not imply endorsement by any financial firm, exchange, or regulator, and it must
not collide with an established Python package.

## Decision

Distribution name **`convexity`**, import name **`convexity`**. Identical, so
`pip install convexity` and `import convexity` agree — one fewer thing to
remember.

## Alternatives considered

Availability checked against the PyPI JSON API on **2026-07-17**. A 404 means no
project of that name existed at that moment. This is provisional evidence of
availability, **not legal clearance** for trademark purposes.

| Candidate | PyPI | Note |
| --- | --- | --- |
| `convexity` | available | **Chosen.** Finance-native, distinctive, no material clash. |
| `basispoint` | available | Good; only one unrelated GitHub project. |
| `agio` | available | Shortest, but the meaning is obscure to most users. |
| `cambist` | available | Distinctive but obscure. |
| `py-quant-fin` | available | Rejected — see below. |
| `pyquantfin` | **taken** | Occupied by another project. |
| `quantfin` | **taken** | Occupied by another project. |

`py-quant-fin` was the owner's initial suggestion and was available. It was
rejected for three reasons: the near-identical `pyquantfin` and `quantfin` are
both already taken, so a typo lands a user on someone else's package; the `py-`
prefix is redundant on an index where everything is Python; and the import
`py_quant_fin` is long for the primary interface.

## Consequences

`convexity` is a fixed-income term, which slightly under-sells a multi-asset
library. Accepted: it is evocative of quantitative finance generally, and the
alternative was a generic name with a collision risk.

The name is provisional against trademark: availability on an index is not
clearance. Should a conflict emerge before `1.0.0`, renaming is possible while
the version is `0.x`.
