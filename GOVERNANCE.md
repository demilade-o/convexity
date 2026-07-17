# Governance

## Current state: single maintainer

`convexity` is maintained by one person: [@demilade-o](https://github.com/demilade-o).

This document exists to be honest about what that means rather than to describe
an aspirational structure. A governance document that describes committees which
do not exist is worse than none.

## Roles

**Maintainer.** Merges pull requests, cuts releases, approves the protected
publishing environments, and has final say on scope and conventions. Currently
one person.

**Contributor.** Anyone who opens a pull request, issue, or discussion. No
formal status is required.

## How decisions are made

Ordinary changes — a metric, a fix, a doc improvement — are decided in the pull
request by the maintainer.

Decisions that are hard to reverse get an **Architecture Decision Record** in
`docs/adr/`. These include: the public name, the licence, the layering, the
tooling, the versioning scheme, the default conventions, and the provider
policy. An ADR records the decision, the alternatives, and the reasoning, with
source URLs and access dates for facts that can go stale.

Anything that changes a **default convention** for an existing metric is a
breaking change even if the signature is unchanged, because it silently changes
users' numbers. It requires an ADR, a deprecation period, and a changelog entry.

## Scope decisions

The maintainer decides scope. Deferred work is recorded in
[ROADMAP.md](ROADMAP.md) with a target release, never silently dropped.

Some things are out of scope indefinitely, and a good pull request will not
change that: trade execution, brokerage connectivity, live trading, a
backtesting engine, investment advice, and redistributing third-party market
data.

## Releases

The maintainer cuts releases. The process is automated and gated: a version tag
triggers a workflow that re-runs the full suite from a clean checkout, builds
once, publishes to TestPyPI, smoke-tests the *published* artefact, and only then
requires human approval on a protected environment before PyPI.

No individual holds a PyPI token. Publishing uses Trusted Publishing via OIDC
and cannot be reached from a forked pull request.

## Adding maintainers

There is no fixed rule, because there is no second maintainer yet. The
realistic bar: sustained, high-quality contribution over time, demonstrated
judgement on numerical conventions, and a willingness to say no to scope creep.
If you are interested, contribute for a while and then ask.

When a second maintainer joins, this document must be revised to describe how
disagreements are resolved between them — the single-maintainer model has no
answer to that question and pretending otherwise would be dishonest.

## Succession

This is the part most single-maintainer projects omit.

If the maintainer becomes unavailable for **six months** with no commits, no
issue responses, and no reply to a direct request, the project should be
considered unmaintained. In that case:

- The licence (Apache-2.0) permits anyone to fork and continue the work. That is
  the intended remedy and requires no permission.
- A fork should use a **different distribution name**. The PyPI name and the
  repository are not transferable by this document, and publishing under the
  same name would be confusing and potentially unsafe for existing users.
- If you wish to take over the canonical name rather than fork, open a GitHub
  issue proposing it and follow PyPI's project-abandonment process. Do not
  assume silence is consent.

The maintainer intends to add a co-maintainer before this matters, and to
transfer or archive the project explicitly rather than let it decay silently.

## Code of Conduct

Everyone participating is bound by the [Code of Conduct](CODE_OF_CONDUCT.md).
The maintainer is responsible for enforcement.
