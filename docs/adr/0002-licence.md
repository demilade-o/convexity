# 0002: Licence and contribution policy

**Status:** Accepted
**Date:** 2026-07-17

## Context

The project needs an OSI-approved licence and a contribution policy that
establishes contributors have the right to submit their work.

## Decision

**Apache License 2.0** (SPDX: `Apache-2.0`), with **Developer Certificate of
Origin** sign-off on commits (`git commit -s`).

The licence text is taken verbatim from the canonical source
(<https://www.apache.org/licenses/LICENSE-2.0.txt>, retrieved 2026-07-17,
sha256 `cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`)
rather than transcribed, so no clause is silently altered.

## Alternatives considered

**MIT / BSD-3-Clause.** Shorter and very widely understood; BSD-3-Clause would
match NumPy, SciPy and pandas. Rejected because neither includes an explicit
patent grant. Apache-2.0 section 3 grants one and terminates it for a
contributor who initiates patent litigation. For a library implementing
quantitative methods — a field with active patenting — that protection is worth
the extra length.

**A CLA.** Rejected. A CLA imposes real friction on drive-by contributors and
requires infrastructure to administer. The DCO achieves the provenance goal with
a one-line sign-off and no paperwork. Should the project ever need copyright
assignment, that is a decision for a future ADR and a relicensing conversation,
not a default imposed on the first contributor.

## Consequences

`NOTICE` ships with the distribution, as Apache-2.0 section 4(d) requires when a
NOTICE file exists.

The NOTICE carries a deliberate data notice: the licence granted over this
*code* extends no rights over data a user later retrieves through an optional
provider adapter. Conflating those two is the most likely licensing mistake a
consumer of this library could make.

DCO sign-off is documented in `CONTRIBUTING.md` and asserted in the pull-request
template. It is not currently enforced by a bot; if contribution volume grows
enough to need one, that is a small future change.
