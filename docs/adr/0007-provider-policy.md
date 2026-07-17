# 0007: Data-provider policy

**Status:** Accepted
**Date:** 2026-07-17

## Context

The library needs market and economic data adapters. Data carries legal
conditions that code licences do not, and "free to access" is routinely confused
with "openly licensed".

## Decision

### Key-free official providers first

The primary rate/economic adapters are **U.S. Treasury Fiscal Data** (USD) and
**ECB Data Portal** (EUR). Neither requires an API key.

This is an engineering decision as much as a legal one. A provider requiring a
credential can only ever be tested with mocks — no maintainer or CI run can
verify the real integration without someone's secret. A key-free provider can be
smoke-tested for real, on a schedule, by anyone. The claim "a provider works"
becomes independently verifiable instead of taken on trust.

**FRED is deferred to an optional keyed extra**, despite being the obvious first
choice for economic data. Its terms require an API key and attribution, and
state that series available through it may be owned by third parties and subject
to copyright, with permission needed from the data owner for anything beyond
personal use (<https://fred.stlouisfed.org/docs/api/terms_of_use.html>, accessed
2026-07-17 via the St. Louis Fed's published terms).

### Currencies

USD (3-month Treasury bill) and EUR (€STR) initially, per the owner's decision.
Other currencies are fully supported through user-supplied rates and curves;
they simply have no bundled adapter yet.

There is no universal risk-free rate. The default proxy is configurable per
currency, and the documentation distinguishes policy rates, bill rates,
constant-maturity yields, OIS proxies and zero curves rather than pretending
they are interchangeable.

### yfinance is optional, research-only, and never a dependency of anything

Available as `convexity[yahoo]`. Its own documentation states it is **not
affiliated with, endorsed by, or vetted by Yahoo**, and that the Yahoo Finance
API is **intended for personal use only**
(<https://ranaroussi.github.io/yfinance/>, accessed 2026-07-17).

Therefore: it is never a test or build dependency; no Yahoo data is ever placed
in the wheel, sdist, documentation, examples or fixtures; the adapter is
replaceable through the provider protocol; and no availability, completeness or
production-suitability claim is made about it.

### No data is ever committed or shipped

This project distributes no market or economic data. A captured provider
response may carry licensing obligations our Apache-2.0 licence does not grant,
and it makes tests non-deterministic. Contract tests use constructed fixtures.

Two enforced controls: `scripts/check_staged.py` rejects data files and
credentials at commit time; `scripts/check_artefacts.py` rejects them at build
time and runs in both CI and the release workflow. Both are tested in both
directions.

### Unknown legal status is recorded as unknown

`docs/providers/provider-matrix.md` records authentication, terms, licence,
attribution, commercial-use status, rate limits and known limitations per
provider. Where the status is unclear, it says so. Inferring "probably fine" is
how a project ends up redistributing something it may not.

## Consequences

Adapters ship in `0.2.0`; the protocol lands with them. See `ROADMAP.md`.

Users needing FRED or Yahoo install an extra and accept those terms themselves.
The core stays lawful, offline, and deterministic.

This ADR is not legal advice. It records the project's reading of published
terms on the access date shown; those terms change, and users are responsible
for their own compliance.
