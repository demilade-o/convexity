# Release-candidate evidence

This report records the exact commands run to verify the `0.1.0` release
candidate, their outcomes, the environment they ran in, and — just as important —
what has **not** been executed and why. Nothing here is asserted that was not
observed; steps that require infrastructure this project does not yet have are
listed as such, not claimed as done.

## Environment

Everything below was run locally on a single machine.

| Component | Version |
| --- | --- |
| OS | macOS (Darwin 24.6.0, x86-64) |
| Python | 3.14.6 |
| NumPy | 2.5.1 |
| pandas | 3.0.3 |
| Ruff | 0.15.22 |
| mypy | 2.3.0 |
| import-linter | 2.13 |
| pytest | 9.1.1 |
| Hypothesis | 6.156.6 |
| respx / httpx | 0.23.1 / 0.28.1 |
| uv | 0.11.26 |

!!! note "Where each result was observed"
    The command output quoted below was produced **locally on CPython 3.14.6 /
    macOS**. The project targets 3.12–3.14 on Linux, macOS and Windows; those
    other interpreters and operating systems have since executed this code on
    GitHub Actions. The full matrix, the dependency audit, CodeQL and the secret
    scan all pass on commit `dcbbf19` (2026-08-12) — see
    [Verified on CI](#verified-on-ci). What remains genuinely unrun is the
    release/publish pipeline and the human-only owner settings, listed at the end.

## Format and lint

```
ruff format --check src tests      # 44 files already formatted
ruff check src tests               # All checks passed!
```

Both exit `0`.

## Static typing

```
mypy                               # Success: no issues found in 44 source files
```

Strict mode, `warn_unreachable` on. Exit `0`.

## Architecture contracts

```
lint-imports                       # Contracts: 3 kept, 0 broken.
```

The three contracts prove that the core layers are acyclic, that no analytics or
rate module imports a networking dependency (`httpx`, `socket`, `urllib`,
`requests`, `yfinance`), and that no core module imports the concrete providers.
Exit `0`.

## Tests and coverage

```
pytest --cov --cov-branch          # 681 passed
```

681 tests pass with the network disabled for the entire suite (`--disable-socket`
in `pyproject.toml`). Provider tests use respx-mocked HTTP and injected clocks;
no test opens a real socket.

Two coverage thresholds, checked separately:

```
coverage report --include="…conventions…,returns.py,risk.py,performance.py,\
    validation.py,alignment.py,rates/*" --fail-under=95    # TOTAL 98%, exit 0
coverage report --fail-under=90                            # TOTAL 97%, exit 0
```

The computational core (conventions, returns, risk, performance, validation,
alignment, rates) is at **98%** branch coverage against a 95% floor. The whole
package, including the I/O data layer, is at **97%** against a 90% floor. The
risk-free-rate subsystem and the entire data layer are at **100%**.

Doctests run as their own step:

```
pytest --doctest-modules src/convexity     # 43 passed
```

## Independent validation

Every public metric is validated by at least one method that cannot silently
agree with a bug:

- **Hand-worked derivations** for Sharpe (numerator exactly `0.15`), Sortino
  (ratio exactly `8/3`), Calmar, the rate conversions, and the day counts.
- **Property tests** (Hypothesis, 31 in total) for return round-trips, drawdown
  bounds, the rate annual↔period round-trip, zero-curve discount-factor bounds,
  and the point-in-time alignment guarantee on arbitrary shapes.
- **Registry/API consistency:** a test proves every exported metric has a
  catalogue entry and vice versa, so documentation cannot drift from code.

## Packaging

```
uv build                           # built sdist and wheel
uvx twine check --strict dist/*    # both PASSED
python scripts/check_artefacts.py  # both artefacts passed content checks
```

The wheel ships `convexity/py.typed` and every module including
`convexity/rates/` and `convexity/data/`. The artefact check confirms no private
reference material, credentials, caches, or provider data are present in either
artefact.

Clean-environment install and import, from each artefact, in a fresh virtual
environment with only the declared dependencies:

```
# wheel
uv pip install dist/convexity-0.1.0-py3-none-any.whl
python -c "import convexity"        # imports; httpx and the data layer are NOT loaded
# sortino_ratio reproduces the hand-worked 8/3 = 2.66666667
# RiskFreeSeries.to_period_returns reproduces 0.05/12 = 0.00416667

# sdist
uv pip install dist/convexity-0.1.0.tar.gz
# sortino_ratio reproduces 2.66666667
```

The installed wheel confirms the network-free guarantee end to end: after
`import convexity`, neither `httpx` nor `convexity.data` appears in
`sys.modules`.

## Documentation

```
mkdocs build --strict              # builds; warnings are errors
```

The metric catalogue is generated from the registry, and a check fails CI if the
two disagree:

```
python scripts/generate_metric_docs.py --check    # ok: matches the registry
```

## Data layer verification

The one key-free official provider — U.S. Treasury Fiscal Data — is verified
end to end against a respx-mocked API whose fixtures mimic the documented
response shape (no captured responses). The tests cover: percent-to-decimal
parsing, complete provenance, a cache hit with a correct age on the second call,
`use_cache=False` bypass, offline mode served from cache, offline-without-cache
raising, malformed/empty/short responses raising, and the fetched series feeding
a Sharpe ratio through a look-ahead-free alignment.

The retrying transport is verified for: retry on `429`/`5xx`, no retry on other
`4xx`, bounded attempts, exponential jittered backoff, `Retry-After` honoured,
and connection errors surfacing as `ProviderUnavailableError`. The cache is
verified for atomic writes, traversal-safe keys, and corruption reading back as a
miss.

## Security and supply chain

- **Secret / private-material scan:** the tracked tree contains no reference to
  private planning material, no credentials, and no provider data. Enforced at
  commit time by `scripts/check_staged.py` and at build time by
  `scripts/check_artefacts.py`.
- **Dependency audit (`pip-audit`):** could not be executed locally — the
  sandbox cannot reach `pypi.org` to fetch the advisory database — so it runs on
  CI, where the index is reachable, and **passes** on commit `dcbbf19`. The audit
  exports the resolved dependency set with `--no-emit-project`, so it checks the
  third-party dependencies rather than `convexity` itself, which is unpublished.
  See [Verified on CI](#verified-on-ci).

## Verified on CI

The repository is now hosted at `github.com/demilade-o/convexity`, and the CI and
Security workflows have executed against commit `dcbbf19` (2026-08-12). The
following ran on GitHub-hosted runners and **passed** — they are no longer merely
configured:

- **CI matrix** — the test suite on Python 3.12/3.13/3.14 on Ubuntu, and 3.12 and
  3.14 on both macOS and Windows. Seven legs, all green; Linux and Windows have
  now executed this code, not only macOS.
- **Minimum-dependency job** pinning the lowest declared versions (NumPy 2.1,
  pandas 2.2).
- **`pip-audit`** against the resolved dependency set (third-party only).
- **CodeQL** (`security-extended`) and the **detect-secrets** scan over the full
  history. CodeQL flaked once on a transient TLS error fetching its own tool
  bundle and passed on re-run; it is not a code finding.
- **Dependency review** on pull requests, enabled once the repository's dependency
  graph was switched on.

## Still requires a human with owner access

These cannot be done by automation and have **not** been done. None is claimed:

- **Release / publish pipeline:** PyPI Trusted Publishing via OIDC, SBOM and
  attestations. It publishes only on a tag, under owner-approved environment
  protection, never on an ordinary push or a forked pull request — and no tag has
  been cut.
- **Branch protection:** required status checks, required review, conversation
  resolution, no force-push or deletion on `main`.
- **Registering the PyPI Trusted Publisher** and the protected release environment.
- **Publishing to TestPyPI/PyPI.**

The public repository itself has been created and `main` pushed by the owner. A
maintainer runbook for the remaining steps lives alongside the project
documentation.

## Summary

Every locally provable gate for the `0.1.0` candidate passes on CPython 3.14.6 /
macOS: format, lint, strict typing, architecture contracts, 681 network-disabled
tests, both coverage thresholds, doctests, packaging build and clean install from
both artefacts, and the strict documentation build. What remains is genuinely
remote- or human-gated, and is listed above rather than asserted.
