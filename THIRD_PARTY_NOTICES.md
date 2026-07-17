# Third-party notices

`convexity` is distributed under the [Apache License 2.0](LICENSE). It bundles no
third-party code: the packages below are declared dependencies, installed
separately by pip, and remain under their own licences.

## Runtime dependencies (core)

| Package | Licence | Project |
| --- | --- | --- |
| NumPy | BSD-3-Clause | <https://numpy.org/> |
| pandas | BSD-3-Clause | <https://pandas.pydata.org/> |

Both are compatible with Apache-2.0 for our purposes: we depend on them, we do
not redistribute them.

## Optional dependencies

| Extra | Package | Licence | Notes |
| --- | --- | --- | --- |
| `providers` | httpx | BSD-3-Clause | HTTP client for official data adapters |
| `yahoo` | yfinance | Apache-2.0 | **Research and personal use only** — see below |

### yfinance

Installed only via `convexity[yahoo]`. It is never a test or build dependency,
and the core library never imports it.

yfinance's own documentation states that it is **not affiliated with, endorsed
by, or vetted by Yahoo**, and that the Yahoo Finance API is **intended for
personal use only**. Consult Yahoo's terms of service before relying on data
retrieved through it. `convexity`'s Apache-2.0 licence grants no rights over any
data obtained from Yahoo or any other provider.

- yfinance: <https://github.com/ranaroussi/yfinance>
- Documentation and disclaimer: <https://ranaroussi.github.io/yfinance/>

## Data

**This project distributes no market or economic data.**

Optional adapters retrieve data at runtime, directly from the provider, on behalf
of the user. That data is governed by the provider's terms and by any
third-party rights in the underlying series — rights this project's licence
neither grants nor extends.

Free to access is not the same as openly licensed. For example, the FRED API
terms of use state that data series available through it may be owned by third
parties and subject to copyright, and that permission must be obtained from the
data owner for anything beyond personal use. Similar conditions apply elsewhere.

See [docs/providers/provider-matrix.md](docs/providers/provider-matrix.md) for
per-provider terms, attribution requirements, and commercial-use status. Legal
status that is unknown is recorded as unknown, never inferred.

## Development dependencies

Development and documentation tooling — pytest, Hypothesis, Ruff, mypy, MkDocs,
uv and their transitive dependencies — is not distributed with the package and is
listed in `pyproject.toml` under `[dependency-groups]`. Each remains under its
own licence.

A machine-readable SBOM (CycloneDX) is generated for every release and attached
to the GitHub release.
