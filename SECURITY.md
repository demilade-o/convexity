# Security policy

## Supported versions

While `convexity` is in `0.x`, only the latest released minor version receives
security fixes. Once `1.0.0` ships, this table will list a supported window.

| Version | Supported |
| ------- | --------- |
| 0.1.x   | Yes       |
| < 0.1   | No        |

## Reporting a vulnerability

**Please do not open a public issue for a security report.**

Report privately through GitHub's private vulnerability reporting:

<https://github.com/demilade-o/convexity/security/advisories/new>

This routes the report to the maintainer privately and keeps the discussion,
patch, and disclosure in one place.

Please include: affected version, a description of the issue, reproduction
steps, and the impact you believe it has.

### What to expect

| Stage | Target |
| --- | --- |
| Acknowledgement | 3 working days |
| Initial assessment | 10 working days |
| Fix or mitigation plan | 30 days for confirmed high severity |

These are targets for a small project, not contractual guarantees. If you have
not heard back within the acknowledgement window, please open a public issue
saying only that you are awaiting a response on a private report — with no
details of the vulnerability itself.

### Disclosure

We follow coordinated disclosure. We will agree a disclosure date with you,
publish a GitHub Security Advisory with a CVE where warranted, credit you unless
you prefer otherwise, and release a fixed version before the advisory is public.

## Scope

In scope:

- Code execution, path traversal, or unsafe deserialisation through any public API
- Credential or secret leakage through logs, exceptions, caches, or artefacts
- Cache poisoning or unsafe file handling in the provider cache
- Supply-chain weaknesses in the release workflow

Out of scope:

- Vulnerabilities in third-party data providers themselves — report those to the
  provider
- **Incorrect numerical results.** These matter enormously, but they are bugs,
  not vulnerabilities. Please use the
  [incorrect metric issue template](https://github.com/demilade-o/convexity/issues/new?template=metric_incorrect.yml)
  so the discussion is public and the fix is reviewable.
- Denial of service from deliberately pathological input to a local function

## Security design notes

- **No credentials are required for the core library.** Analytics perform no I/O.
- **No secret is ever placed in a log, exception message, cache key, or fixture.**
- **The cache never deserialises executable formats.** `pickle` is not used for
  cached provider data.
- **Releases use PyPI Trusted Publishing (OIDC).** No long-lived PyPI token
  exists to be stolen. Publishing requires approval on a protected environment
  and cannot be reached from a forked pull request.
- **Third-party GitHub Actions are pinned to immutable commit SHAs**, so a
  compromised upstream tag cannot alter our builds. Dependabot keeps the pins
  current.
