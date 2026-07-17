"""Immutable risk-free-rate models with explicit conventions and provenance.

Every model here validates on construction and never mutates a caller-owned
object. Rates are decimals throughout: ``0.05`` is 5%, never ``5``.

The alignment operations are backward-looking by construction -- they delegate to
:func:`convexity.alignment.align_asof`, so a rate published after a measurement
date can never inform it. That is the property that makes these safe to feed into
a Sharpe or Sortino ratio.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
import pandas as pd

from convexity.alignment import align_asof
from convexity.conventions import Compounding, DayCount, annual_to_period_rate
from convexity.exceptions import (
    ConventionError,
    CurrencyMismatchError,
    DataQualityError,
    ValidationError,
)
from convexity.validation import validate_datetime_index

if TYPE_CHECKING:
    from collections.abc import Sequence

__all__ = [
    "InterpolationMethod",
    "RateInstrument",
    "RateQuote",
    "RiskFreePolicy",
    "RiskFreeSeries",
    "ZeroCurve",
]


class RateInstrument(enum.Enum):
    """What the rate actually measures.

    There is no universal risk-free rate. These distinctions are the reason:
    an overnight policy rate, a Treasury bill yield, and a constant-maturity
    yield are different numbers measuring different things, and which one is
    "the" risk-free rate depends on the horizon and currency of the question.

    Attributes
    ----------
    OVERNIGHT
        An overnight or near-overnight benchmark, such as SOFR, EUR STR, or a
        central-bank policy rate. The usual proxy for a short-horizon risk-free
        rate.
    TREASURY_BILL
        A short-dated government bill yield.
    TREASURY_CONSTANT_MATURITY
        A yield interpolated to a fixed maturity, such as the 3-month or 10-year
        constant-maturity Treasury series.
    OIS
        An overnight-indexed-swap rate, a common collateralised discounting proxy.
    DEPOSIT
        An interbank deposit or term money-market rate.
    GENERIC
        A caller-supplied rate whose precise instrument is unspecified. Recorded
        as such rather than guessed.
    """

    OVERNIGHT = "overnight"
    TREASURY_BILL = "treasury_bill"
    TREASURY_CONSTANT_MATURITY = "treasury_constant_maturity"
    OIS = "ois"
    DEPOSIT = "deposit"
    GENERIC = "generic"


class InterpolationMethod(enum.Enum):
    """How a :class:`ZeroCurve` interpolates between its pillars.

    Attributes
    ----------
    LINEAR_ZERO
        Linear in the continuously compounded zero rate. Simple and stable; the
        default. Discount factors it implies are not guaranteed arbitrage-free
        between pillars, which is acceptable for the discounting and forward-rate
        queries this release supports and is documented rather than hidden.
    LINEAR_LOG_DF
        Linear in the log of the discount factor, equivalently piecewise-constant
        instantaneous forward rates. Guarantees positive, monotone discount
        factors for an upward zero curve.
    """

    LINEAR_ZERO = "linear_zero"
    LINEAR_LOG_DF = "linear_log_df"


def _validate_currency(currency: str) -> str:
    """Return an upper-cased ISO 4217 code, or raise if it is not one."""
    code = currency.strip().upper()
    if len(code) != 3 or not code.isalpha():
        msg = (
            f"currency must be a three-letter ISO 4217 code, got {currency!r}. "
            f"Examples: 'USD', 'EUR', 'GBP'."
        )
        raise ValidationError(msg)
    return code


@dataclass(frozen=True, slots=True)
class RateQuote:
    """A single dated risk-free rate with its full convention.

    Attributes
    ----------
    value
        Annualised rate as a decimal. ``0.05`` is 5%.
    quote_date
        The date the rate is observed for (its as-of date).
    currency
        ISO 4217 currency code, upper-cased on construction.
    tenor
        Tenor label, such as ``"ON"``, ``"3M"`` or ``"10Y"``. Free text, because
        the space of tenor conventions is larger than any enum; it is recorded
        for the reader, not parsed.
    compounding
        Compounding convention the rate is quoted under.
    day_count
        Day-count basis the rate is quoted under.
    instrument
        What the rate measures. See :class:`RateInstrument`.
    source
        Human-readable provenance, such as a provider and series identifier.
    retrieved_at
        UTC timestamp at which the value was retrieved, if known. Distinct from
        ``quote_date``: a figure observed for one day may be retrieved on another.
    terms_url
        Link to the source's terms of use, if applicable.

    Raises
    ------
    ValidationError
        If ``value`` is not finite or ``currency`` is not a valid ISO 4217 code.

    Examples
    --------
    >>> import pandas as pd
    >>> q = RateQuote(0.05, pd.Timestamp("2024-01-31"), "USD")
    >>> round(q.period_return(252), 8)
    0.00019841
    """

    value: float
    quote_date: pd.Timestamp
    currency: str = "USD"
    tenor: str = "ON"
    compounding: Compounding = Compounding.SIMPLE
    day_count: DayCount = DayCount.ACT_360
    instrument: RateInstrument = RateInstrument.OVERNIGHT
    source: str = "user-supplied"
    retrieved_at: pd.Timestamp | None = None
    terms_url: str | None = None

    def __post_init__(self) -> None:
        if not np.isfinite(self.value):
            msg = f"RateQuote.value must be finite, got {self.value!r}."
            raise ValidationError(msg)
        object.__setattr__(self, "quote_date", pd.Timestamp(self.quote_date))
        object.__setattr__(self, "currency", _validate_currency(self.currency))

    def period_return(
        self, periods_per_year: float, *, compounding: Compounding | None = None
    ) -> float:
        """Return the rate earned over one period of the given frequency.

        Parameters
        ----------
        periods_per_year
            Number of periods per year (for example ``252`` for business daily).
        compounding
            Override the quote's own compounding for the conversion. Defaults to
            the quote's :attr:`compounding`.

        Returns
        -------
        float
            The period return as a decimal.

        Examples
        --------
        >>> import pandas as pd
        >>> q = RateQuote(0.12, pd.Timestamp("2024-01-31"), "USD")
        >>> round(q.period_return(12), 4)  # 12% annual, monthly, simple
        0.01
        """
        result = annual_to_period_rate(
            self.value, periods_per_year, compounding or self.compounding
        )
        return float(result)

    def staleness(self, asof: pd.Timestamp) -> pd.Timedelta:
        """Return how old this quote is relative to ``asof``.

        Parameters
        ----------
        asof
            The date to measure staleness against.

        Returns
        -------
        pandas.Timedelta
            ``asof - quote_date``. Negative if the quote is dated after ``asof``,
            which indicates a future-dated (look-ahead) quote.
        """
        return pd.Timestamp(asof) - self.quote_date

    def is_future_dated(self, asof: pd.Timestamp) -> bool:
        """Return whether the quote is dated strictly after ``asof``.

        A future-dated quote must never inform a measurement at ``asof``; this
        predicate lets a caller detect the condition before it does harm.
        """
        return self.quote_date > pd.Timestamp(asof)


@dataclass(frozen=True, eq=False)
class RiskFreeSeries:
    """A history of risk-free rates under a single convention.

    All the convention and provenance fields of :class:`RateQuote` apply to the
    whole series: every observation is quoted the same way. The values are annual
    rates as decimals, indexed by observation date.

    Equality is by identity (``eq=False``): the class wraps a mutable pandas
    Series, so value-equality would be both expensive and ambiguous.

    Attributes
    ----------
    rates
        Annual rates as decimals, indexed by a sorted, unique ``DatetimeIndex``.
        Copied on construction; the caller's Series is never retained or mutated.
    currency, tenor, compounding, day_count, instrument, source, terms_url
        As :class:`RateQuote`, applied to every observation.
    retrieved_at
        UTC retrieval timestamp for the whole series, if known.

    Raises
    ------
    ValidationError
        If ``rates`` is empty or contains non-finite values.
    IndexValidationError
        If the index is not a sorted, unique ``DatetimeIndex``.

    Examples
    --------
    >>> import pandas as pd
    >>> idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
    >>> s = RiskFreeSeries(pd.Series([0.05, 0.045], index=idx), currency="USD")
    >>> target = pd.to_datetime(["2024-02-15", "2024-03-15"])
    >>> s.align_to(target).tolist()
    [0.05, 0.045]
    """

    rates: pd.Series
    currency: str = "USD"
    tenor: str = "ON"
    compounding: Compounding = Compounding.SIMPLE
    day_count: DayCount = DayCount.ACT_360
    instrument: RateInstrument = RateInstrument.OVERNIGHT
    source: str = "user-supplied"
    retrieved_at: pd.Timestamp | None = None
    terms_url: str | None = None

    def __post_init__(self) -> None:
        series = pd.Series(self.rates).astype(float)
        if len(series) == 0:
            msg = (
                "RiskFreeSeries requires at least one observation, got an empty series."
            )
            raise ValidationError(msg)
        validate_datetime_index(series.index)
        if not bool(np.isfinite(series.to_numpy()).all()):
            n_bad = int((~np.isfinite(series.to_numpy())).sum())
            msg = (
                f"RiskFreeSeries.rates contains {n_bad} non-finite value(s). A "
                f"risk-free rate of NaN or infinity is never meaningful; clean the "
                f"series before constructing the model."
            )
            raise DataQualityError(msg)
        object.__setattr__(self, "rates", series)
        object.__setattr__(self, "currency", _validate_currency(self.currency))

    def align_to(
        self,
        target_index: pd.DatetimeIndex,
        *,
        max_staleness: pd.Timedelta | None = None,
        publication_lag: pd.Timedelta | None = None,
    ) -> pd.Series:
        """Align the annual rates onto a target index, backward-looking only.

        For each target date the most recent rate at or before it is selected,
        so a rate never informs an earlier date. This is the point-in-time-safe
        way to attach a risk-free series to a return series' calendar.

        Parameters
        ----------
        target_index
            Dates to align onto.
        max_staleness
            Reject a target date whose matched rate is older than this. ``None``
            permits unbounded carry-forward.
        publication_lag
            Treat each rate as available only from ``observation_date +
            publication_lag``, modelling real-world release delay.

        Returns
        -------
        pandas.Series
            Annual rates aligned to ``target_index``. A target date preceding the
            first observation is ``NaN``.

        Raises
        ------
        StaleDataError
            If ``max_staleness`` is exceeded.
        NoOverlapError
            If no target date has any prior observation.
        """
        return align_asof(
            target_index,
            self.rates,
            max_staleness=max_staleness,
            publication_lag=publication_lag,
            name=f"{self.currency} {self.instrument.value} rate",
        )

    def to_period_returns(
        self,
        target_index: pd.DatetimeIndex,
        periods_per_year: float,
        *,
        max_staleness: pd.Timedelta | None = None,
        publication_lag: pd.Timedelta | None = None,
    ) -> pd.Series:
        """Align, then convert to the per-period risk-free return a metric needs.

        This is the operation a Sharpe or Sortino ratio ultimately wants: a
        per-period risk-free return aligned to the strategy's dates, produced
        without look-ahead and under the series' own compounding convention.

        Parameters
        ----------
        target_index
            Dates to align onto, typically the return series' index.
        periods_per_year
            Frequency to convert the annual rate into.
        max_staleness, publication_lag
            As :meth:`align_to`.

        Returns
        -------
        pandas.Series
            Per-period risk-free returns aligned to ``target_index``.

        Examples
        --------
        A flat 12% annual rate becomes a 1% monthly return under simple
        compounding:

        >>> import pandas as pd
        >>> idx = pd.to_datetime(["2024-01-31"])
        >>> s = RiskFreeSeries(pd.Series([0.12], index=idx), currency="USD")
        >>> target = pd.to_datetime(["2024-02-29", "2024-03-31"])
        >>> s.to_period_returns(target, 12).round(4).tolist()
        [0.01, 0.01]
        """
        annual = self.align_to(
            target_index,
            max_staleness=max_staleness,
            publication_lag=publication_lag,
        )
        period = annual_to_period_rate(
            annual.to_numpy(), periods_per_year, self.compounding
        )
        return pd.Series(np.asarray(period, dtype=float), index=annual.index)

    def latest(self, asof: pd.Timestamp) -> RateQuote:
        """Return the most recent quote at or before ``asof`` as a :class:`RateQuote`.

        Parameters
        ----------
        asof
            The as-of date.

        Returns
        -------
        RateQuote
            The latest observation not after ``asof``, carrying every convention.

        Raises
        ------
        ValidationError
            If no observation is at or before ``asof`` -- there is nothing that
            could be known on that date.
        """
        asof_ts = pd.Timestamp(asof)
        eligible = self.rates.loc[self.rates.index <= asof_ts]
        if len(eligible) == 0:
            msg = (
                f"No {self.currency} rate is dated on or before {asof_ts.date()}; "
                f"the series begins at {self.rates.index[0].date()}. An as-of "
                f"lookup never returns a future rate."
            )
            raise ValidationError(msg)
        date = eligible.index[-1]
        return RateQuote(
            value=float(eligible.iloc[-1]),
            quote_date=date,
            currency=self.currency,
            tenor=self.tenor,
            compounding=self.compounding,
            day_count=self.day_count,
            instrument=self.instrument,
            source=self.source,
            retrieved_at=self.retrieved_at,
            terms_url=self.terms_url,
        )


@dataclass(frozen=True, eq=False)
class ZeroCurve:
    """A zero-coupon yield curve for discounting and forward rates.

    The curve stores continuously compounded zero rates at a set of pillar
    tenors, measured in years from the valuation date. Between pillars it
    interpolates under a declared :class:`InterpolationMethod`; beyond them it
    extrapolates flat, which is stated rather than hidden.

    Attributes
    ----------
    tenors
        Pillar tenors in years, strictly increasing and positive.
    zero_rates
        Continuously compounded zero rates at each pillar, as decimals.
    valuation_date
        The date the curve is anchored to.
    currency
        ISO 4217 code.
    interpolation
        Interpolation method. See :class:`InterpolationMethod`.

    Raises
    ------
    ConventionError
        If ``tenors`` and ``zero_rates`` differ in length, or ``tenors`` is not
        strictly increasing and positive.
    DataQualityError
        If any zero rate is non-finite.

    Examples
    --------
    A flat 4% continuously compounded curve discounts as ``exp(-0.04 t)``:

    >>> import numpy as np, pandas as pd
    >>> curve = ZeroCurve([1.0, 2.0, 5.0], [0.04, 0.04, 0.04],
    ...                   valuation_date=pd.Timestamp("2024-01-01"))
    >>> round(curve.discount_factor(2.0), 8)
    0.92311635
    >>> round(curve.zero_rate(3.5), 8)  # flat curve: same everywhere
    0.04
    """

    tenors: Sequence[float] | np.ndarray
    zero_rates: Sequence[float] | np.ndarray
    valuation_date: pd.Timestamp = field(default_factory=lambda: pd.Timestamp("today"))
    currency: str = "USD"
    interpolation: InterpolationMethod = InterpolationMethod.LINEAR_ZERO

    def __post_init__(self) -> None:
        tenors = np.asarray(self.tenors, dtype=float)
        rates = np.asarray(self.zero_rates, dtype=float)
        if tenors.shape != rates.shape or tenors.ndim != 1:
            msg = (
                f"tenors and zero_rates must be equal-length 1-D arrays, got "
                f"shapes {tenors.shape} and {rates.shape}."
            )
            raise ConventionError(msg)
        if len(tenors) == 0:
            msg = "ZeroCurve requires at least one pillar."
            raise ConventionError(msg)
        if not bool(np.all(np.diff(tenors) > 0)) or tenors[0] <= 0:
            msg = (
                f"tenors must be strictly increasing and positive, got {tenors!r}. "
                f"Duplicate or unordered pillars make interpolation ill-defined."
            )
            raise ConventionError(msg)
        if not bool(np.isfinite(rates).all()):
            msg = "ZeroCurve.zero_rates contains a non-finite value."
            raise DataQualityError(msg)
        object.__setattr__(self, "tenors", tenors)
        object.__setattr__(self, "zero_rates", rates)
        object.__setattr__(self, "valuation_date", pd.Timestamp(self.valuation_date))
        object.__setattr__(self, "currency", _validate_currency(self.currency))

    def _check_tenor(self, t: float) -> float:
        if t < 0:
            msg = f"tenor must be non-negative, got {t!r}."
            raise ConventionError(msg)
        return float(t)

    def zero_rate(self, t: float) -> float:
        """Return the interpolated continuously compounded zero rate at tenor ``t``.

        Parameters
        ----------
        t
            Tenor in years, non-negative.

        Returns
        -------
        float
            The zero rate as a decimal. Flat extrapolation applies outside the
            pillar range.
        """
        t = self._check_tenor(t)
        tenors = np.asarray(self.tenors, dtype=float)
        rates = np.asarray(self.zero_rates, dtype=float)
        if self.interpolation is InterpolationMethod.LINEAR_LOG_DF:
            # Linear in log discount factor == linear in (rate * tenor); recover
            # the rate by dividing the interpolated integral by t. At t == 0 the
            # zero rate is the shortest pillar's by convention.
            if t == 0.0:
                return float(rates[0])
            integral = np.interp(t, tenors, rates * tenors)
            return float(integral / t)
        return float(np.interp(t, tenors, rates))

    def discount_factor(self, t: float) -> float:
        """Return the discount factor for tenor ``t``.

        Parameters
        ----------
        t
            Tenor in years, non-negative.

        Returns
        -------
        float
            ``exp(-z(t) * t)``, which is exactly ``1.0`` at ``t == 0``.
        """
        t = self._check_tenor(t)
        return float(np.exp(-self.zero_rate(t) * t))

    def forward_rate(self, t1: float, t2: float) -> float:
        """Return the continuously compounded forward rate between ``t1`` and ``t2``.

        Parameters
        ----------
        t1, t2
            Start and end tenors in years, with ``t2 > t1 >= 0``.

        Returns
        -------
        float
            The forward rate ``(z2 t2 - z1 t1) / (t2 - t1)`` implied by the curve.

        Raises
        ------
        ConventionError
            If ``t2`` does not strictly exceed ``t1``.

        Examples
        --------
        On a flat curve every forward equals the zero rate:

        >>> import pandas as pd
        >>> curve = ZeroCurve([1.0, 5.0], [0.03, 0.03],
        ...                   valuation_date=pd.Timestamp("2024-01-01"))
        >>> round(curve.forward_rate(1.0, 4.0), 8)
        0.03
        """
        t1 = self._check_tenor(t1)
        t2 = self._check_tenor(t2)
        if t2 <= t1:
            msg = f"forward_rate requires t2 > t1, got t1={t1!r}, t2={t2!r}."
            raise ConventionError(msg)
        z1, z2 = self.zero_rate(t1), self.zero_rate(t2)
        return float((z2 * t2 - z1 * t1) / (t2 - t1))


@dataclass(frozen=True, slots=True)
class RiskFreePolicy:
    """Rules for turning a rate source into a per-period series without look-ahead.

    A policy is the reusable configuration of "how this desk defines its
    risk-free rate": which currency and instrument, what staleness is tolerable,
    how long after an observation date a figure is really available.

    Attributes
    ----------
    currency
        Required currency. A series in another currency is a
        :class:`~convexity.exceptions.CurrencyMismatchError`, never silently
        converted.
    instrument
        Preferred proxy. Recorded for provenance and checked against the series.
    tenor
        Preferred tenor label.
    max_staleness
        Maximum age of a matched rate. ``None`` permits unbounded carry-forward.
    publication_lag
        Delay applied to every observation's availability.
    require_instrument_match
        If ``True`` (default), a series whose instrument differs from
        :attr:`instrument` raises rather than being used under the wrong label.

    Examples
    --------
    >>> import pandas as pd
    >>> policy = RiskFreePolicy(currency="USD",
    ...                         max_staleness=pd.Timedelta(days=40))
    >>> idx = pd.to_datetime(["2024-01-31", "2024-02-29"])
    >>> series = RiskFreeSeries(pd.Series([0.05, 0.045], index=idx))
    >>> target = pd.to_datetime(["2024-02-15", "2024-03-10"])
    >>> policy.resolve(series, target).round(4).tolist()
    [0.05, 0.045]
    """

    currency: str = "USD"
    instrument: RateInstrument = RateInstrument.OVERNIGHT
    tenor: str = "ON"
    max_staleness: pd.Timedelta | None = None
    publication_lag: pd.Timedelta | None = None
    require_instrument_match: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "currency", _validate_currency(self.currency))

    def resolve(
        self, series: RiskFreeSeries, target_index: pd.DatetimeIndex
    ) -> pd.Series:
        """Align a series onto a target index under this policy.

        Parameters
        ----------
        series
            The risk-free series to align.
        target_index
            Dates to align onto.

        Returns
        -------
        pandas.Series
            Annual rates aligned to ``target_index``, honouring the policy's
            staleness and publication-lag rules with no look-ahead.

        Raises
        ------
        CurrencyMismatchError
            If the series currency differs from the policy currency.
        ConventionError
            If ``require_instrument_match`` is set and the instruments differ.
        StaleDataError
            If a matched rate exceeds :attr:`max_staleness`.
        """
        if series.currency != self.currency:
            msg = (
                f"policy requires {self.currency} but the series is "
                f"{series.currency}. Risk-free rates are never converted across "
                f"currencies silently; supply a {self.currency} series or an "
                f"explicit FX policy."
            )
            raise CurrencyMismatchError(msg)
        if self.require_instrument_match and series.instrument is not self.instrument:
            msg = (
                f"policy prefers {self.instrument.value} but the series is "
                f"{series.instrument.value}. Set require_instrument_match=False to "
                f"accept a different proxy deliberately."
            )
            raise ConventionError(msg)
        return series.align_to(
            target_index,
            max_staleness=self.max_staleness,
            publication_lag=self.publication_lag,
        )
