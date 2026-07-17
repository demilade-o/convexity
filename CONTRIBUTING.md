# Contributing to convexity

Thank you for considering a contribution. This project has an unusually strict
evidence standard for numerical code, and it is worth understanding why before
you start.

## The evidence standard

**Every formula needs a source that is not another library.**

This is the rule that shapes everything else here. Copying a formula from
another package imports its convention choices and its bugs, and you inherit
them without knowing which you got. Several widely-used libraries disagree on
the downside-deviation denominator; at least one is confidently wrong about it.
If our only evidence is "library X does it this way", we have no way to tell
which of us is right.

Acceptable evidence, in order of preference:

1. **A primary reference.** The paper or textbook that defined the metric.
   Sortino and Price (1994) for the Sortino ratio, not a blog post about it.
2. **A published worked example** with numbers you can reproduce exactly.
3. **A hand derivation** included in the test, with the working written out so a
   reviewer can check the arithmetic rather than trust it.

A cross-check against another implementation is welcome *as a supplement*, and
where we deliberately disagree with a popular library we document why.

### Choose fixtures where the arithmetic is exact

The best test data makes the derivation checkable by eye. Our Sortino fixture is
`[0.01] * 11 + [-0.03]` because the `sqrt(m)` annualisation cancels the `1/n` of
the FULL convention exactly, giving `0.08 / 0.03 = 8/3` in closed form. Our
Calmar fixture uses `n == m` so the annualisation exponent is 1. Prefer a
fixture that produces a clean number over a realistic one that produces
`2.7182818...` and can only be compared against a recorded output.

**A test asserting the value the code currently returns proves only that the code
agrees with itself.** That is not validation.

## Conventions, not defaults

Where the literature disagrees, expose the variants as named parameters and
document the default *with its reason*. Never resolve a genuine ambiguity by
picking one silently.

Where a convention cannot be resolved from the inputs, raise with diagnostics.
The library does not guess. There is no fallback to 252.

## Setup

```bash
uv sync --all-extras --group dev
uv run --group lint pre-commit install
```

Pre-commit hooks run through `uv`, so their versions come from `uv.lock` — the
same versions CI resolves. Local and CI results cannot diverge.

## Checks

```bash
uv run ruff format .                       # format
uv run ruff check . --fix                  # lint
uv run mypy                                # strict, over src and tests alike
uv run pytest                              # network disabled via --disable-socket
uv run pytest --doctest-modules src/convexity   # every documented example runs
uv run --group lint lint-imports           # architecture boundaries
uv run --group docs mkdocs build --strict  # docs, warnings are errors
```

Coverage gates: **95% on the computational core, 90% overall**, both branch-based.
Branch coverage matters because the validation layer is almost all branches, and
line coverage would report a policy as tested when only one side of it ever ran.

Do not lower a threshold to make a change pass. If a gate is wrong, that is a
separate discussion in its own issue.

## Adding a metric

1. Implement it in the module matching its category. Analytics never perform I/O
   and never import a provider — `lint-imports` enforces this.
2. Full type annotations and a NumPy-style docstring with the formula in
   rendered notation, every parameter, the return contract, edge cases, and
   references.
3. Add a `MetricSpec` to `src/convexity/registry.py`. A metric without a registry
   entry fails CI: the catalogue is tested against the public API.
4. Tests: a hand-worked derivation, the edge cases (empty, single observation,
   constant/zero-variance, zero denominator, no downside, no drawdown, total
   loss, missing data), and non-mutation.
5. Add a property test if the metric has an invariant — a bound, a round trip, a
   monotonicity. Hypothesis finds the inputs you would not have chosen. It has
   already falsified one invariant in this codebase that looked obviously true.
6. Update `CHANGELOG.md`.

## Adding a data provider

Free to access is not the same as openly licensed.

1. Record the provider in `docs/providers/provider-matrix.md`: authentication,
   terms URL, licence, attribution, commercial-use status, rate limits, known
   limitations. **Mark unknown legal status as unknown** — never infer it.
2. Implement the capability protocol. Providers return package-owned models;
   provider-specific objects must not leak into the public API.
3. Return provenance with every fetch.
4. Contract tests use mocked or synthetic responses. **Tests never hit a live
   endpoint** — the whole suite runs with sockets disabled.
5. Never commit a captured response containing real market data. It may be
   licensed, it is not ours to redistribute, and it makes tests
   non-deterministic. Construct fixtures instead.

## Data and licensing

**No market or economic data enters this repository** — not in tests, not in
docs, not in examples. `scripts/check_staged.py` rejects data files and
credentials at commit time, and `scripts/check_artefacts.py` rejects them at
build time.

## Commits and pull requests

We use [Conventional Commits](https://www.conventionalcommits.org/) for PR
titles: `feat:`, `fix:`, `docs:`, `test:`, `ci:`, `build:`, `refactor:`, `chore:`.

Write a commit body that explains **why**, not what — the diff already says what.
If you made a judgement call, record the reasoning and what you rejected. This
project's history is meant to be readable as an explanation of its own design.

PRs are squash-merged. Keep them focused: one metric, one fix, one concern.

### Developer Certificate of Origin

Contributions are accepted under the [DCO](https://developercertificate.org/).
Sign off each commit:

```bash
git commit -s
```

This certifies you have the right to submit the work under the project's licence.
There is no CLA and no paperwork.

## Code style

- British English in prose; standard API spellings (`color`) where a dependency
  requires them.
- Returns are decimals. `0.01` is 1%. Everywhere, without exception.
- Never mutate a caller's object.
- Raise a specific, actionable exception. Never return a plausible but
  meaningless number.
- Avoid "institutional-grade", "accurate", or unqualified "risk-free" in prose.

## Review

You can expect review to focus on: whether the formula's source is real, whether
the conventions are explicit, whether the edge cases are tested, and whether a
future reader could tell what convention produced a number. Style is handled by
Ruff and is not a review topic.
