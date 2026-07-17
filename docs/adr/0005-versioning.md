# 0005: Versioning and the single source of truth

**Status:** Accepted
**Date:** 2026-07-17

## Context

The package needs a version scheme with public meaning, and exactly one place
where the version lives.

## Decision

**Semantic Versioning** for public API meaning, with **PEP 440**-compatible
strings. The project stays in `0.x` while the API is explicitly unstable.

The version is single-sourced from `src/convexity/_version.py` and read at build
time by Hatchling (`[tool.hatch.version] path = ...`).

**A change to a default convention is a breaking change**, even when the
signature is unchanged. Changing the downside-deviation default from `FULL` to
`DOWNSIDE_ONLY` would alter every user's Sortino ratio by `sqrt(n / n_below)`
while their code continued to compile and run. Silence there would be worse than
a rename, which at least fails loudly.

## Alternatives considered

**Tag-derived versioning (hatch-vcs / setuptools-scm).** The common choice, and
rejected deliberately. Tag-derived versioning reads git metadata at build time —
and an sdist contains no git metadata. Building from the sdist is exactly what
the release pipeline must verify, so the mechanism would fail at the one moment
it matters most. Workarounds exist; a static file needing none is simpler.

The release workflow closes the gap that tag-derived versioning would otherwise
have handled automatically: it asserts the git tag matches
`convexity.__version__` and fails the release if they disagree. A mismatch means
publishing something other than what the tag claims.

## Consequences

Bumping a version is a manual edit to `_version.py`, caught by the release
workflow's tag check if forgotten.

`0.x` means minor releases may break the API. The bar for `1.0.0` is recorded in
`ROADMAP.md` and is a bar, not a date.
