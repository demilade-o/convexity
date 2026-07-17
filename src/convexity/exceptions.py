"""Package-specific exceptions.

Every failure mode in :mod:`convexity` raises a subclass of :class:`ConvexityError`
so callers can distinguish library errors from arbitrary ``ValueError``s raised by
NumPy or pandas. Messages are written to be actionable: they state what was wrong,
what was expected, and how to proceed.

The library never returns a plausible-but-meaningless number in place of an error.
Where a metric is genuinely undefined for an input (for example a Sortino ratio for
a series with no downside observations), the behaviour is a documented, deliberate
policy -- see the relevant metric page -- and not an accident.
"""

from __future__ import annotations

__all__ = [
    "AlignmentError",
    "ConventionError",
    "ConvexityError",
    "CurrencyMismatchError",
    "DataQualityError",
    "FrequencyInferenceError",
    "IndexValidationError",
    "InsufficientDataError",
    "LookAheadError",
    "NoOverlapError",
    "ProviderError",
    "ProviderResponseError",
    "ProviderUnavailableError",
    "RateLimitError",
    "StaleDataError",
    "UndefinedMetricError",
    "ValidationError",
]


class ConvexityError(Exception):
    """Base class for every error raised by :mod:`convexity`."""


# --------------------------------------------------------------------------- #
# Input validation
# --------------------------------------------------------------------------- #


class ValidationError(ConvexityError, ValueError):
    """Input failed validation.

    Also inherits :class:`ValueError` so that callers with existing
    ``except ValueError`` handlers are not broken by adopting this package.
    """


class InsufficientDataError(ValidationError):
    """Fewer usable observations than the metric's documented minimum sample."""


class IndexValidationError(ValidationError):
    """The index is unusable for a time-dependent metric.

    Raised for non-``DatetimeIndex`` inputs where dates are required, and for
    non-monotonic or duplicated timestamps, which are never silently reordered
    or dropped.
    """


class DataQualityError(ValidationError):
    """Values violate the metric's domain.

    Covers non-finite values under a strict NaN policy, simple returns at or
    below ``-1.0`` where the metric compounds wealth, and non-positive prices.
    """


# --------------------------------------------------------------------------- #
# Conventions
# --------------------------------------------------------------------------- #


class ConventionError(ConvexityError):
    """A convention was unsupported, ambiguous, or mutually inconsistent."""


class FrequencyInferenceError(ConventionError):
    """Observation frequency could not be inferred confidently.

    The library never guesses an annualisation factor. Supply ``periods_per_year``
    explicitly, or pass an explicit :class:`~convexity.conventions.Frequency`.
    """


# --------------------------------------------------------------------------- #
# Alignment and point-in-time integrity
# --------------------------------------------------------------------------- #


class AlignmentError(ConvexityError):
    """Two or more series could not be aligned under the requested policy."""


class NoOverlapError(AlignmentError):
    """Series share no overlapping observations after alignment."""


class StaleDataError(AlignmentError):
    """An aligned observation exceeded the permitted staleness."""


class LookAheadError(AlignmentError):
    """An operation would have used information unavailable at the as-of date.

    Raised defensively: alignment in this package is backward-looking by default
    and this error indicates a caller explicitly requested, or a provider supplied,
    data stamped after the measurement date.
    """


class CurrencyMismatchError(ConvexityError):
    """Operands are denominated in different currencies with no conversion policy."""


# --------------------------------------------------------------------------- #
# Metrics
# --------------------------------------------------------------------------- #


class UndefinedMetricError(ConvexityError):
    """The metric is mathematically undefined for the supplied input.

    Raised only where the documented policy for the metric is to raise. Metrics
    whose documented policy is to return ``nan`` or an infinity do so instead.
    """


# --------------------------------------------------------------------------- #
# Data providers
# --------------------------------------------------------------------------- #


class ProviderError(ConvexityError):
    """Base class for data-provider failures."""


class ProviderUnavailableError(ProviderError):
    """The provider could not be used at all.

    Typically a missing optional dependency, absent credentials, or offline mode
    with no cache entry.
    """


class ProviderResponseError(ProviderError):
    """The provider responded, but the payload was unusable."""


class RateLimitError(ProviderError):
    """The provider signalled a rate limit.

    ``retry_after`` carries the server's advice in seconds when supplied.
    """

    def __init__(self, message: str, *, retry_after: float | None = None) -> None:
        super().__init__(message)
        self.retry_after = retry_after
