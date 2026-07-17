"""Capability-based provider protocols.

A provider declares what it can supply, and callers depend on the capability, not
the vendor. This is why there is no single ``Provider.fetch`` that claims to
return everything: a rate provider and a price provider have genuinely different
contracts, and pretending otherwise pushes the difference into runtime failures.

Each capability is a :class:`typing.Protocol`, so a class satisfies it structurally
-- there is nothing to subclass and no registration step. The protocols are
:func:`~typing.runtime_checkable`, so the registry and contract tests can ask
``isinstance(provider, RiskFreeRateProvider)`` to discover what a provider offers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    import pandas as pd

    from convexity.data.models import DataEnvelope
    from convexity.rates import RiskFreeSeries

__all__ = [
    "EconomicSeriesProvider",
    "PriceHistoryProvider",
    "Provider",
    "RiskFreeRateProvider",
]


@runtime_checkable
class Provider(Protocol):
    """Metadata every provider must expose, regardless of capability.

    These fields make a provider self-describing: a caller can display the
    attribution, link to the terms, and know before calling whether a credential
    is required or the data is research-only.
    """

    @property
    def name(self) -> str:
        """Stable, unique provider identifier."""
        ...

    @property
    def terms_url(self) -> str:
        """Link to the provider's terms of use."""
        ...

    @property
    def attribution(self) -> str:
        """Attribution text the provider requires to be displayed."""
        ...

    @property
    def requires_auth(self) -> bool:
        """Whether the provider needs a credential to function."""
        ...

    @property
    def research_only(self) -> bool:
        """Whether the data is licensed for research/personal use only."""
        ...


@runtime_checkable
class RiskFreeRateProvider(Provider, Protocol):
    """A provider that returns a risk-free rate history with conventions."""

    def fetch_risk_free(
        self,
        *,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        offline: bool = False,
        use_cache: bool = True,
    ) -> DataEnvelope[RiskFreeSeries]:
        """Fetch a risk-free rate series wrapped in provenance."""
        ...


@runtime_checkable
class EconomicSeriesProvider(Provider, Protocol):
    """A provider that returns a named economic time series."""

    def fetch_series(
        self,
        series_id: str,
        *,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        offline: bool = False,
        use_cache: bool = True,
    ) -> DataEnvelope[pd.Series]:
        """Fetch one economic series wrapped in provenance."""
        ...


@runtime_checkable
class PriceHistoryProvider(Provider, Protocol):
    """A provider that returns a price history for a symbol."""

    def fetch_prices(
        self,
        symbol: str,
        *,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        offline: bool = False,
        use_cache: bool = True,
    ) -> DataEnvelope[pd.DataFrame]:
        """Fetch a price history wrapped in provenance."""
        ...
