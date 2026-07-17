"""Machine-readable catalogue of every public metric.

The registry is the single source of truth for what this library computes and
under what conventions. Documentation is generated from it, and a test asserts
that the registry and the public API cannot drift apart: a metric added to the
package without an entry here fails CI, and an entry naming a function that does
not exist fails too.

That coupling is the point. A catalogue maintained by hand becomes wrong within
a release, and a wrong catalogue is worse than none -- users trust it to tell
them which convention a number was computed under.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Iterator

__all__ = [
    "REGISTRY",
    "Category",
    "MetricSpec",
    "Status",
    "get",
    "iter_metrics",
]


class Category(enum.Enum):
    """Analytic family a metric belongs to."""

    RETURNS = "returns"
    RISK = "risk"
    DRAWDOWN = "drawdown"
    RATIO = "ratio"
    BENCHMARK = "benchmark"
    CONVENTION = "convention"


class Status(enum.Enum):
    """Stability of a metric's public contract.

    Attributes
    ----------
    STABLE
        Signature and default conventions will not change without a deprecation
        period, even in ``0.x``.
    EXPERIMENTAL
        May change in a minor release. Documented as such at the call site.
    """

    STABLE = "stable"
    EXPERIMENTAL = "experimental"


@dataclass(frozen=True, slots=True)
class MetricSpec:
    """Everything a caller must know about a metric before trusting its output.

    Attributes
    ----------
    name
        Canonical public function name, importable from ``convexity``.
    aliases
        Other names this quantity is known by in the literature. Recorded for
        discoverability; they are not importable aliases, because two names for
        one function invites the two drifting apart.
    category
        Analytic family.
    status
        Stability of the public contract.
    summary
        One-line description.
    formula
        The formula in plain notation. The rendered form lives in the docstring.
    units
        Units of the returned value.
    annualisation
        How, and whether, the result is annualised.
    requires
        Auxiliary inputs beyond the return series.
    min_observations
        Minimum usable observations.
    edge_cases
        Documented behaviour at the boundaries.
    references
        Primary sources. A citation of another library is never sufficient.
    added_in
        Version in which the metric first appeared or last changed materially.
    """

    name: str
    category: Category
    status: Status
    summary: str
    formula: str
    units: str
    annualisation: str
    edge_cases: str
    added_in: str
    aliases: tuple[str, ...] = ()
    requires: tuple[str, ...] = ()
    min_observations: int = 1
    references: tuple[str, ...] = field(default_factory=tuple)


_SPECS: tuple[MetricSpec, ...] = (
    # ---------------------------------------------------------------- returns
    MetricSpec(
        name="simple_returns",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Simple (arithmetic) returns from a price series.",
        formula="r_t = P_t / P_{t-1} - 1",
        units="decimal (0.01 is 1%)",
        annualisation="none; per-period",
        edge_cases=(
            "Non-positive price raises DataQualityError. First observation is "
            "dropped, never zero-filled. Fewer than 2 prices raises."
        ),
        min_observations=2,
        added_in="0.1.0",
    ),
    MetricSpec(
        name="log_returns",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Continuously compounded returns from a price series.",
        formula="r_t = ln(P_t / P_{t-1})",
        units="decimal",
        annualisation="none; per-period",
        edge_cases="Non-positive price raises; the logarithm is undefined there.",
        aliases=("continuously compounded returns",),
        min_observations=2,
        added_in="0.1.0",
    ),
    MetricSpec(
        name="to_log_returns",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Convert simple returns to log returns.",
        formula="r_log = ln(1 + r)",
        units="decimal",
        annualisation="none",
        edge_cases="A return at or below -1.0 raises; the logarithm diverges.",
        added_in="0.1.0",
    ),
    MetricSpec(
        name="to_simple_returns",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Convert log returns to simple returns.",
        formula="r = exp(r_log) - 1",
        units="decimal",
        annualisation="none",
        edge_cases="Total round-trip identity with to_log_returns.",
        added_in="0.1.0",
    ),
    MetricSpec(
        name="wealth_index",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Compound simple returns into a wealth level.",
        formula="W_t = W_0 * prod(1 + r_i)",
        units="wealth (same units as `initial`)",
        annualisation="none",
        edge_cases=(
            "A return of exactly -1.0 drives wealth to zero and it stays zero: "
            "wealth cannot recover from a total loss. Non-positive `initial` raises."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="cumulative_return",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Total compounded return over the sample.",
        formula="R = prod(1 + r_i) - 1",
        units="decimal",
        annualisation="none; holding-period",
        edge_cases="Compounds rather than sums: +10% then -10% is -1%, not 0%.",
        aliases=("holding-period return", "total return"),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="annualised_return",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Geometric annualised return from periodic returns.",
        formula="R_ann = (prod(1 + r_i))^(m/n) - 1",
        units="decimal per year",
        annualisation=(
            "Geometric. Requires periods_per_year, an explicit Frequency, or a "
            "confidently inferable DatetimeIndex; never assumes 252."
        ),
        edge_cases=(
            "Terminal wealth of zero annualises to exactly -1.0. No annualisation "
            "route raises FrequencyInferenceError."
        ),
        aliases=("CAGR (periodic)", "geometric mean return"),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="arithmetic_annualised_return",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Arithmetic mean return scaled to a year.",
        formula="R_arith = m * mean(r)",
        units="decimal per year",
        annualisation="Linear scaling by m.",
        edge_cases=(
            "Exceeds the geometric annualised return by approximately half the "
            "variance. This is not the return an investor earns; it is reported "
            "because Sharpe and Sortino are defined on it."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="cagr",
        category=Category.RETURNS,
        status=Status.STABLE,
        summary="Compound annual growth rate from actual elapsed calendar time.",
        formula="CAGR = W_T^(365.25 / elapsed_days) - 1",
        units="decimal per year",
        annualisation=(
            "From elapsed time directly; needs no periods_per_year, so it is the "
            "honest choice for irregularly spaced observations."
        ),
        edge_cases="Requires a DatetimeIndex and a positive elapsed span.",
        min_observations=2,
        added_in="0.1.0",
    ),
    # ------------------------------------------------------------------- risk
    MetricSpec(
        name="volatility",
        category=Category.RISK,
        status=Status.STABLE,
        summary="Standard deviation of returns, optionally annualised.",
        formula="sigma_ann = sigma_period * sqrt(m)",
        units="decimal",
        annualisation=(
            "Square-root-of-time, applied only when annualise=True. Assumes "
            "serially uncorrelated, identically distributed returns -- both "
            "usually false, which is why it is a convention, not a measurement."
        ),
        edge_cases=(
            "A constant series returns exactly 0.0, not floating-point dust. "
            "Requires more than ddof observations."
        ),
        aliases=("standard deviation", "sigma"),
        min_observations=2,
        added_in="0.1.0",
    ),
    MetricSpec(
        name="downside_deviation",
        category=Category.RISK,
        status=Status.STABLE,
        summary="Root of the second lower partial moment about a target.",
        formula="DD = sqrt( sum(min(r_t - MAR, 0)^2) / denominator )",
        units="decimal",
        annualisation="Square-root-of-time when annualise=True.",
        edge_cases=(
            "Denominator convention is explicit: FULL divides by total n (Sortino "
            "and Price 1994, the default); DOWNSIDE_ONLY divides by the count "
            "below target. The two differ by sqrt(n / n_below). Returns exactly "
            "0.0 when nothing falls below the target -- a true statement about "
            "the sample, not a missing value."
        ),
        requires=("mar (per-period target)",),
        aliases=("semideviation", "downside risk"),
        references=(
            "Sortino, F. A. and Price, L. N. (1994). Performance Measurement in a "
            "Downside Risk Framework. The Journal of Investing, 3(3), 59-64.",
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="upside_deviation",
        category=Category.RISK,
        status=Status.STABLE,
        summary="Root of the second upper partial moment about a target.",
        formula="UD = sqrt( sum(max(r_t - MAR, 0)^2) / denominator )",
        units="decimal",
        annualisation="none by default",
        edge_cases="Mirrors downside_deviation under negation of the series.",
        requires=("mar (per-period target)",),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="skewness",
        category=Category.RISK,
        status=Status.STABLE,
        summary="Sample skewness of returns.",
        formula="g1 = m3 / m2^(3/2)",
        units="dimensionless",
        annualisation="none",
        edge_cases=(
            "Zero-variance series returns nan: the ratio is 0/0 and reporting 0 "
            "would imply a symmetry that cannot be known. bias=False applies the "
            "Fisher-Pearson adjustment and requires n > 2."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="kurtosis",
        category=Category.RISK,
        status=Status.STABLE,
        summary="Sample kurtosis of returns.",
        formula="g2 = m4 / m2^2",
        units="dimensionless",
        annualisation="none",
        edge_cases=(
            "fisher=True (default) returns excess kurtosis (normal scores 0); "
            "fisher=False returns Pearson kurtosis (normal scores 3). "
            "Zero-variance returns nan. bias=False requires n > 3."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="tracking_error",
        category=Category.BENCHMARK,
        status=Status.STABLE,
        summary="Standard deviation of active return against a benchmark.",
        formula="TE = sigma(r_t - b_t) * sqrt(m)",
        units="decimal",
        annualisation="Square-root-of-time when annualise=True.",
        edge_cases=(
            "Zero against itself. A constant offset gives zero: it measures the "
            "variability of the gap, not its level. No overlap raises NoOverlapError."
        ),
        requires=("benchmark returns",),
        min_observations=2,
        added_in="0.1.0",
    ),
    # --------------------------------------------------------------- drawdown
    MetricSpec(
        name="drawdown_series",
        category=Category.DRAWDOWN,
        status=Status.STABLE,
        summary="Underwater curve: decline from the running peak.",
        formula="D_t = W_t / max_{s<=t}(W_s) - 1",
        units="decimal, non-positive",
        annualisation="none",
        edge_cases=(
            "The running peak includes starting wealth of 1.0, so a first-period "
            "loss is a real drawdown. Bounded in [-1, 0]."
        ),
        aliases=("underwater curve",),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="max_drawdown",
        category=Category.DRAWDOWN,
        status=Status.STABLE,
        summary="Largest peak-to-trough decline over the sample.",
        formula="MDD = min_t(D_t)",
        units="decimal, non-positive",
        annualisation="none",
        edge_cases=(
            "Exactly 0.0 when the series never falls below its starting wealth -- "
            "a real result, not a missing one. Measured from the running peak, "
            "not from an interim level."
        ),
        aliases=("MDD", "maximum drawdown"),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="drawdown_episodes",
        category=Category.DRAWDOWN,
        status=Status.STABLE,
        summary="Distinct drawdown episodes with dates, depth and recovery.",
        formula="Episodes between successive returns to the running peak.",
        units="list of DrawdownEpisode",
        annualisation="none",
        edge_cases=(
            "An episode open at the end of the sample reports recovery=None "
            "rather than imputing a recovery that did not happen."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="average_drawdown",
        category=Category.DRAWDOWN,
        status=Status.STABLE,
        summary="Mean depth across distinct drawdown episodes.",
        formula="mean(depth of each episode)",
        units="decimal, non-positive",
        annualisation="none",
        edge_cases=(
            "Averages over episodes, not observations; averaging the underwater "
            "curve instead gives the pain index. Zero when no episodes exist."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="ulcer_index",
        category=Category.DRAWDOWN,
        status=Status.STABLE,
        summary="Quadratic mean of the underwater curve.",
        formula="UI = sqrt( mean(D_t^2) )",
        units="decimal, non-negative",
        annualisation="none",
        edge_cases=(
            "Never below the pain index (power-mean inequality); equal only when "
            "the underwater curve is flat. Zero when never underwater."
        ),
        references=(
            "Martin, P. and McCann, B. (1989). The Investor's Guide to Fidelity Funds.",
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="pain_index",
        category=Category.DRAWDOWN,
        status=Status.STABLE,
        summary="Mean depth of the underwater curve.",
        formula="PI = mean(|D_t|)",
        units="decimal, non-negative",
        annualisation="none",
        edge_cases="Zero when never underwater.",
        added_in="0.1.0",
    ),
    # ----------------------------------------------------------------- ratios
    MetricSpec(
        name="sharpe_ratio",
        category=Category.RATIO,
        status=Status.STABLE,
        summary="Annualised excess return per unit of total volatility.",
        formula="S = m * mean(r - f) / ( sigma(r - f) * sqrt(m) )",
        units="dimensionless, per year",
        annualisation=(
            "Numerator scales by m, denominator by sqrt(m). Excess is computed "
            "per period and then annualised, so a time-varying risk-free series "
            "is handled correctly rather than reduced to its mean."
        ),
        edge_cases=(
            "Arithmetic, not geometric: the numerator is a mean excess scaled by "
            "m, as Sharpe defined it. Zero denominator gives +/-inf by sign, or "
            "nan when the numerator is also zero."
        ),
        requires=("risk_free (scalar annual, or aligned Series)",),
        min_observations=2,
        references=(
            "Sharpe, W. F. (1966). Mutual Fund Performance. The Journal of "
            "Business, 39(1), 119-138.",
            "Sharpe, W. F. (1994). The Sharpe Ratio. The Journal of Portfolio "
            "Management, 21(1), 49-58.",
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="sortino_ratio",
        category=Category.RATIO,
        status=Status.STABLE,
        summary="Annualised excess return per unit of downside deviation.",
        formula="Sortino = m * mean(r - MAR) / ( DD * sqrt(m) )",
        units="dimensionless, per year",
        annualisation="Numerator by m, denominator by sqrt(m).",
        edge_cases=(
            "Denominator convention is explicit (FULL by default, per Sortino and "
            "Price 1994). +inf when there is no downside and mean excess is "
            "positive; nan when there is no downside and mean excess is zero."
        ),
        requires=("mar (scalar annual by default, or aligned Series)",),
        references=(
            "Sortino, F. A. and Price, L. N. (1994). Performance Measurement in a "
            "Downside Risk Framework. The Journal of Investing, 3(3), 59-64.",
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="calmar_ratio",
        category=Category.RATIO,
        status=Status.STABLE,
        summary="Annualised excess return over maximum drawdown.",
        formula="Calmar = (R_ann - f_ann) / |MDD|",
        units="dimensionless, per year",
        annualisation=(
            "The numerator is a GEOMETRIC annualised return, unlike Sharpe and "
            "Sortino which use arithmetic means. This follows the ratio's origin "
            "as a return-over-worst-loss measure, where the compounded outcome is "
            "the quantity of interest."
        ),
        edge_cases=(
            "lookback_periods is applied BEFORE the drawdown is computed, so the "
            "drawdown is the worst decline within the window, not an earlier one "
            "the window excludes. The classic definition uses a trailing 36 "
            "months; None (default) uses the full sample, making this the MAR "
            "ratio. +inf when there is no drawdown and the return is positive."
        ),
        requires=("risk_free (optional; 0.0 by default, matching the classic form)",),
        aliases=("MAR ratio (with lookback=None)",),
        references=(
            "Young, T. W. (1991). Calmar Ratio: A Smoother Tool. Futures, 20(1).",
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="rolling_sharpe",
        category=Category.RATIO,
        status=Status.STABLE,
        summary="Sharpe ratio over a rolling window.",
        formula="sharpe_ratio applied to each trailing window",
        units="dimensionless, per year",
        annualisation="As sharpe_ratio.",
        edge_cases=(
            "Windows shorter than min_periods yield nan rather than a value "
            "computed from a partial window. A sparse rate Series is passed whole "
            "to the as-of alignment, never reindexed onto the window."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="rolling_sortino",
        category=Category.RATIO,
        status=Status.STABLE,
        summary="Sortino ratio over a rolling window.",
        formula="sortino_ratio applied to each trailing window",
        units="dimensionless, per year",
        annualisation="As sortino_ratio.",
        edge_cases="Incomplete windows yield nan.",
        added_in="0.1.0",
    ),
    MetricSpec(
        name="rolling_calmar",
        category=Category.RATIO,
        status=Status.STABLE,
        summary="Calmar ratio over a rolling window.",
        formula="calmar_ratio applied to each trailing window",
        units="dimensionless, per year",
        annualisation="As calmar_ratio.",
        edge_cases="The window IS the Calmar lookback. Incomplete windows yield nan.",
        added_in="0.1.0",
    ),
    # ------------------------------------------------------------ conventions
    MetricSpec(
        name="annual_to_period_rate",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Convert an annual rate to the return earned over one period.",
        formula=(
            "SIMPLE: r/m | COMPOUNDED: (1+r)^(1/m) - 1 | CONTINUOUS: exp(r/m) - 1"
        ),
        units="decimal per period",
        annualisation="Inverse of period_to_annual_rate.",
        edge_cases=(
            "For a positive rate the conventions order continuous > simple > "
            "compounded. COMPOUNDED requires r > -1.0. Treating an annual rate as "
            "a period return is the classic Sharpe-inflation bug this prevents."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="period_to_annual_rate",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Convert a period rate to an annual rate.",
        formula="Exact inverse of annual_to_period_rate under the same convention.",
        units="decimal per year",
        annualisation="n/a",
        edge_cases="Round-trips with annual_to_period_rate to floating tolerance.",
        added_in="0.1.0",
    ),
    MetricSpec(
        name="year_fraction",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Year fraction between two dates under a day-count convention.",
        formula="ACT/360: actual_days / 360 | ACT/365F: actual_days / 365",
        units="years",
        annualisation="n/a",
        edge_cases=(
            "Reversed dates raise rather than returning a negative fraction. "
            "Times of day are normalised away: this is a calendar-day convention. "
            "ACT/365F ignores the leap day in its denominator, so a full leap "
            "year exceeds 1."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="infer_frequency",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Conservatively infer observation frequency from a DatetimeIndex.",
        formula="Median gap matched against documented spacing bands.",
        units="FrequencyInference",
        annualisation="n/a",
        edge_cases=(
            "Returns frequency=None with a reason rather than rounding an "
            "unrecognised spacing to the nearest band. Reports a confidence score "
            "and the evidence behind it. Business daily is distinguished from "
            "calendar daily by weekend presence, not gap size."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="resolve_annualisation",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Resolve an annualisation factor under documented precedence.",
        formula="periods_per_year > Frequency > inference from index",
        units="Annualisation",
        annualisation="n/a",
        edge_cases=(
            "Raises FrequencyInferenceError when no route yields an answer, or "
            "when inference is below the confidence threshold. Never falls back "
            "to 252. The result records which route produced it."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="align_asof",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Align a source series onto a target index, backward-looking only.",
        formula="For each target date, the latest source observation at or before it.",
        units="as source",
        annualisation="n/a",
        edge_cases=(
            "Never looks forward, which is what makes it safe for risk-free rates "
            "and benchmarks. Supports max_staleness and publication_lag. A target "
            "before any observation is nan; no target matching raises."
        ),
        added_in="0.1.0",
    ),
    MetricSpec(
        name="align_series",
        category=Category.CONVENTION,
        status=Status.STABLE,
        summary="Align two series on their common index.",
        formula="Inner join on the shared index.",
        units="as inputs",
        annualisation="n/a",
        edge_cases=(
            "No value is forward-filled: a gap removes the date from both rather "
            "than borrowing a neighbour. No overlap raises rather than returning "
            "an empty result."
        ),
        added_in="0.1.0",
    ),
)

#: Canonical name -> specification.
REGISTRY: dict[str, MetricSpec] = {spec.name: spec for spec in _SPECS}


def get(name: str) -> MetricSpec:
    """Return the specification for a metric.

    Parameters
    ----------
    name
        Canonical metric name.

    Returns
    -------
    MetricSpec
        The registered specification.

    Raises
    ------
    KeyError
        If the metric is not registered.

    Examples
    --------
    >>> get("sortino_ratio").category
    <Category.RATIO: 'ratio'>
    """
    return REGISTRY[name]


def iter_metrics(category: Category | None = None) -> Iterator[MetricSpec]:
    """Iterate registered metrics, optionally filtered by category.

    Parameters
    ----------
    category
        Restrict to one category, or ``None`` for all.

    Yields
    ------
    MetricSpec
        Specifications in registration order.

    Examples
    --------
    >>> sorted(m.name for m in iter_metrics(Category.RATIO))[:2]
    ['calmar_ratio', 'rolling_calmar']
    """
    for spec in _SPECS:
        if category is None or spec.category is category:
            yield spec
