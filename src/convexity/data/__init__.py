"""Pluggable, provenance-bearing data access, isolated from the analytics core.

Importing :mod:`convexity` never imports this subpackage, and no metric function
depends on it. That separation is a product guarantee enforced by the import
contracts in ``pyproject.toml``: analytics that could reach a provider could
perform I/O, and the promise that a metric never touches the network would become
unenforceable.

What lives here:

- :class:`Provenance` and :class:`DataEnvelope` -- every fetch returns data
  wrapped with where it came from, when, under what terms, and whether it was
  served from cache.
- Capability protocols in :mod:`convexity.data.protocols` -- a provider declares
  what it can supply, so callers depend on a capability, not a concrete vendor.
- :class:`ProviderRegistry` -- name-based lookup of registered providers.
- :class:`FileCache` -- an atomic, JSON-backed, traversal-safe local cache with an
  offline mode.

Concrete providers live in :mod:`convexity.data.providers` and are imported
explicitly, because they pull in optional networking dependencies that the core
must never require.
"""

from __future__ import annotations

from convexity.data.cache import CacheState, FileCache
from convexity.data.models import DataEnvelope, Provenance
from convexity.data.protocols import (
    EconomicSeriesProvider,
    PriceHistoryProvider,
    Provider,
    RiskFreeRateProvider,
)
from convexity.data.registry import ProviderRegistry

__all__ = [
    "CacheState",
    "DataEnvelope",
    "EconomicSeriesProvider",
    "FileCache",
    "PriceHistoryProvider",
    "Provenance",
    "Provider",
    "ProviderRegistry",
    "RiskFreeRateProvider",
]
