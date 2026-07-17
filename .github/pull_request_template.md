## What and why

<!-- What changes, and what problem it solves. Link the issue if there is one. -->

## Numerical claims

<!-- Delete this section only if the change touches no formula or convention. -->

- [ ] The formula is documented in the docstring in rendered notation.
- [ ] Its **source** is cited: a primary reference, a published worked example, or
      a hand derivation included in the tests. Citing another library is not
      evidence -- it imports that library's convention choices and its bugs.
- [ ] Where competing definitions exist, the variants are exposed as named
      parameters and the default is documented **with its reason**.
- [ ] Units, annualisation behaviour, and minimum sample are stated.
- [ ] Independent validation exists: a hand calculation, an invariant/property
      test, or an authoritative published example.

## Conventions and edge cases

- [ ] No convention is inferred silently; anything ambiguous raises with diagnostics.
- [ ] Missing-data policy is explicit and tested.
- [ ] Edge cases covered: empty, single observation, constant/zero-variance,
      zero denominator, no-downside/no-drawdown, total loss.
- [ ] Caller-owned inputs are not mutated.

## Point-in-time integrity

- [ ] No alignment can use information unavailable at the measurement date.
- [ ] Any rate/benchmark join is backward-looking (as-of), not a plain index join.

## Data and licensing

- [ ] No market or economic data is added to the repository, tests, docs, or examples.
- [ ] No credential, cache, or captured provider response is committed.
- [ ] Any new provider records its terms, licence, attribution and commercial-use
      status in `docs/providers/provider-matrix.md`, marking unknowns as unknown.

## Compatibility

- [ ] Public API changes are additive, or deprecated first with a migration note.
- [ ] `CHANGELOG.md` updated.

## Checks

- [ ] `uv run ruff format --check . && uv run ruff check .`
- [ ] `uv run mypy`
- [ ] `uv run pytest`
- [ ] Commits are signed off (`git commit -s`) per the DCO.
