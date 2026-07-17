#!/usr/bin/env python3
"""Generate the metric catalogue page from the registry.

The catalogue is generated, never hand-written, because a hand-written one is
wrong within a release -- and a wrong catalogue is worse than none, since readers
consult it precisely to learn which convention produced a number.

``--check`` verifies the committed page matches what the registry would produce
and exits non-zero if it does not, so a stale catalogue fails CI.

Usage::

    python scripts/generate_metric_docs.py           # write
    python scripts/generate_metric_docs.py --check   # verify, do not write
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import convexity
from convexity.registry import Category, MetricSpec, iter_metrics

OUTPUT = Path("docs/metrics/index.md")

HEADER = """# Metric catalogue

<!--
  GENERATED FILE - do not edit by hand.
  Regenerate with: python scripts/generate_metric_docs.py
  Source of truth: src/convexity/registry.py
-->

Every metric this library computes, with the conventions it computes under.
This page is generated from the machine-readable registry in
`convexity.registry`, and CI fails if the two disagree.

Returns are decimals throughout: `0.01` is 1%.

## How to read an entry

- **Formula** is the definition as implemented. The rendered form, with every
  symbol defined, is in the function's own docstring.
- **Annualisation** states whether and how the result is scaled to a year. Where
  it says the value is not annualised, it is per-period.
- **Edge cases** is the documented policy at the boundaries, not a description of
  what happens to occur.
- **References** are primary sources. Where a metric has competing definitions in
  the literature, the default is stated with its citation and the alternatives are
  exposed as parameters.

"""

CATEGORY_INTROS: dict[Category, str] = {
    Category.RETURNS: (
        "Returns, wealth, and annualisation. Simple returns compound "
        "multiplicatively; log returns compound additively. The two are never "
        "mixed silently."
    ),
    Category.RISK: (
        "Dispersion and downside risk. Note that annualised volatility is a "
        "convention, not a measurement: square-root-of-time scaling assumes "
        "returns are serially uncorrelated and identically distributed, and real "
        "return series usually violate both."
    ),
    Category.DRAWDOWN: (
        "Drawdown analytics. The running peak includes the starting wealth of "
        "1.0, so a first-period loss is a real drawdown."
    ),
    Category.RATIO: (
        "Risk-adjusted performance. Each ratio accepts a scalar rate or target "
        "(annual by default) or a time-varying Series, aligned with a backward "
        "as-of join that cannot use future information.\n\n"
        "The three ratios do **not** share a numerator convention. Sharpe and "
        "Sortino use arithmetic annualised excess; Calmar uses a geometric one. "
        "This is deliberate and is stated on each entry."
    ),
    Category.BENCHMARK: "Benchmark-relative analytics.",
    Category.CONVENTION: (
        "Convention utilities. These are public because the conventions are part "
        "of the result: a caller who cannot inspect them cannot know what a "
        "number means."
    ),
}


def _render_metric(spec: MetricSpec) -> str:
    lines = [f"### `{spec.name}`", "", spec.summary, ""]

    rows = [
        ("Formula", f"`{spec.formula}`"),
        ("Units", spec.units),
        ("Annualisation", spec.annualisation),
        ("Minimum sample", str(spec.min_observations)),
        ("Status", spec.status.value),
        ("Added in", spec.added_in),
    ]
    if spec.requires:
        rows.insert(3, ("Requires", ", ".join(spec.requires)))
    if spec.aliases:
        rows.append(("Also known as", ", ".join(spec.aliases)))

    lines.append("| | |")
    lines.append("| --- | --- |")
    for label, value in rows:
        lines.append(f"| **{label}** | {value} |")
    lines.append("")

    lines.append(f"**Edge cases.** {spec.edge_cases}")
    lines.append("")

    if spec.references:
        lines.append("**References**")
        lines.append("")
        for reference in spec.references:
            lines.append(f"- {reference}")
        lines.append("")

    # mkdocstrings anchors are the object's full import path, which is the
    # defining module rather than the re-export in convexity/__init__.py.
    # Resolve it here so the link cannot rot; a wrong anchor fails
    # `mkdocs build --strict`.
    qualified = f"{getattr(convexity, spec.name).__module__}.{spec.name}"
    lines.append(f"API: [`convexity.{spec.name}`](../reference/api.md#{qualified})")
    lines.append("")
    return "\n".join(lines)


def render() -> str:
    """Render the full catalogue from the registry."""
    parts = [HEADER]

    parts.append("## Contents\n")
    for category in Category:
        specs = list(iter_metrics(category))
        if not specs:
            continue
        # The TOC slug for a heading of `` `name` `` is the name itself:
        # underscores survive slugification, so no substitution is wanted here.
        names = ", ".join(f"[`{s.name}`](#{s.name})" for s in specs)
        parts.append(f"- **{category.value.title()}** — {names}")
    parts.append("")

    for category in Category:
        specs = list(iter_metrics(category))
        if not specs:
            continue
        parts.append(f"## {category.value.title()}\n")
        intro = CATEGORY_INTROS.get(category)
        if intro:
            parts.append(f"{intro}\n")
        for spec in specs:
            parts.append(_render_metric(spec))

    return "\n".join(parts).rstrip() + "\n"


def main() -> int:
    """Write or verify the catalogue."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify without writing")
    args = parser.parse_args()

    content = render()

    if args.check:
        if not OUTPUT.exists():
            print(f"FAIL: {OUTPUT} does not exist. Run: python {__file__}")
            return 1
        if OUTPUT.read_text() != content:
            print(
                f"FAIL: {OUTPUT} is out of date with the registry.\n"
                f"Regenerate with: python scripts/generate_metric_docs.py"
            )
            return 1
        print(f"ok: {OUTPUT} matches the registry")
        return 0

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(content)
    print(f"wrote {OUTPUT} ({len(content.splitlines())} lines)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
