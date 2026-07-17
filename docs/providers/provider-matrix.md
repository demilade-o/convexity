# Provider matrix

!!! danger "Free to access is not the same as openly licensed"
    Being able to download data does not mean you may redistribute it, use it
    commercially, or publish results derived from it. **`convexity`'s Apache-2.0
    licence grants you no rights whatsoever over data you retrieve through it.**
    Those rights come from the provider, and from whoever owns the underlying
    series — often not the same party.

## This project distributes no data

Not in the wheel. Not in the sdist. Not in the documentation, the examples, or
the test fixtures.

Adapters retrieve data at runtime, directly from the provider, on your behalf
and under your acceptance of their terms. Two automated controls enforce this:
`scripts/check_staged.py` rejects data files at commit time, and
`scripts/check_artefacts.py` rejects them at build time, in both CI and the
release workflow.

The reason is not fussiness. A captured provider response may carry licensing
obligations this project cannot satisfy on your behalf, and committed data makes
tests non-deterministic. Contract tests use constructed fixtures.

## Status

**No provider adapters ship in 0.1.0.** The `providers` and `yahoo` extras are
declared, but the adapters arrive in `0.2.0` — see [ROADMAP.md](https://github.com/demilade-o/convexity/blob/main/ROADMAP.md).

This page records the policy and the assessment of each candidate now, because
the legal assessment is the part that must not be rushed at implementation time.

## Planned adapters

| Provider | Data | Auth | Terms | Commercial use | Redistribution | Status |
| --- | --- | --- | --- | --- | --- | --- |
| U.S. Treasury Fiscal Data | USD bill/yield series | **None** | [Fiscal Data](https://fiscaldata.treasury.gov/api-documentation/) | Believed permitted (US federal work) — **verify at implementation** | Believed permitted — **verify** | Planned 0.2.0 |
| ECB Data Portal | EUR rates, €STR | **None** | [ECB Data Portal](https://data.ecb.europa.eu/) | **Unknown — verify** | **Unknown — verify** | Planned 0.2.0 |
| FRED | Economic series | **API key** | [FRED API terms](https://fred.stlouisfed.org/docs/api/terms_of_use.html) | **Restricted — see below** | **No** for third-party series | Planned 0.2.0, optional extra |
| Yahoo (via yfinance) | Prices | None | [yfinance docs](https://ranaroussi.github.io/yfinance/) | **No — personal use only** | **No** | Planned 0.2.0, optional extra |

Where a cell says **unknown**, it means unknown. It does not mean "probably
fine". Inferring permission is how a project ends up redistributing something it
may not.

## Why key-free providers come first

Treasury and ECB are the primary adapters, ahead of FRED, for an engineering
reason as much as a legal one.

A provider requiring a credential can only ever be tested with mocks. No
maintainer, CI run, or contributor can verify the real integration without
someone's secret, so the claim "this provider works" rests on trust. A key-free
provider can be smoke-tested for real, on a schedule, by anyone who checks out
the repository.

That makes the guarantee independently verifiable rather than asserted.

## FRED

FRED is the obvious first choice for economic data and is nonetheless deferred to
an optional keyed extra.

Its published terms of use
(<https://fred.stlouisfed.org/docs/api/terms_of_use.html>, assessed 2026-07-17)
state that:

- an API key is required, and each application should use a distinct key;
- proper attribution must accompany any use of FRED content;
- **series available through FRED may be owned by third parties and subject to
  copyright**, and the Bank's provision of the API does not override those
  owners' restrictions;
- **permission must be obtained from the data owner** for anything beyond your
  own personal use;
- third-party proprietary content may not be redistributed for commercial use
  without express written permission from the data provider.

This is the clearest available illustration of the distinction this page opens
with. FRED is free, public, and governmental — and a series you pull from it may
still be someone else's copyrighted work that you may not republish.

## Yahoo via yfinance

Available as `convexity[yahoo]` and labelled **research and personal use only**.

yfinance's own documentation states that it is **not affiliated with, endorsed
by, or vetted by Yahoo**, and that the Yahoo Finance API is **intended for
personal use only** (<https://ranaroussi.github.io/yfinance/>, assessed
2026-07-17).

Accordingly, in this project:

- it is **never** a test or build dependency;
- the core library never imports it, enforced by the architecture contract;
- **no Yahoo data** is ever placed in the wheel, sdist, docs, examples or fixtures;
- no claim is made about its availability, completeness, or suitability for
  production;
- it is replaceable through the provider protocol.

If your use is commercial, or you need a reliability guarantee, this adapter is
not for you. Use a provider you have a contract with.

## Before you use any adapter

1. **Read the provider's current terms.** The links above were assessed on the
   date shown. Terms change; this page will lag them.
2. **Check who owns the underlying series**, not just who serves it.
3. **Attribute as required.**
4. **Do not assume your use case is covered** because the data was free to fetch.

## This page is not legal advice

It records this project's reading of published terms on the dates shown, to help
you ask the right questions. It is not a legal opinion, it may be wrong, and it
may be out of date. You are responsible for your own compliance.

## Adding a provider

See [CONTRIBUTING.md](https://github.com/demilade-o/convexity/blob/main/CONTRIBUTING.md).
The legal assessment comes first, and unknown status is recorded as unknown.
