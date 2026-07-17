"""The provider registry: explicit registration, capability-based lookup.

Nothing is registered by default -- a provider that needs a credential or a client
is never constructed implicitly. Registration refuses duplicates, because a silent
replacement could change which terms a later fetch was made under.
"""

from __future__ import annotations

import pandas as pd
import pytest

from convexity.data import DataEnvelope, ProviderRegistry
from convexity.data.protocols import (
    EconomicSeriesProvider,
    PriceHistoryProvider,
    RiskFreeRateProvider,
)
from convexity.exceptions import ProviderUnavailableError
from convexity.rates import RiskFreeSeries


class _FakeRateProvider:
    """A minimal object satisfying RiskFreeRateProvider structurally.

    The fetch signature matches the protocol exactly so a static checker also
    recognises the conformance, not only the runtime isinstance check.
    """

    def __init__(self, name: str = "fake_rates") -> None:
        self._name = name

    @property
    def name(self) -> str:
        return self._name

    terms_url = "https://example.test"
    attribution = "Fake provider for tests"
    requires_auth = False
    research_only = False

    def fetch_risk_free(
        self,
        *,
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        offline: bool = False,
        use_cache: bool = True,
    ) -> DataEnvelope[RiskFreeSeries]:
        raise NotImplementedError


class _NotAProvider:
    """Missing the required metadata; must be rejected."""


class TestRegistration:
    def test_starts_empty(self) -> None:
        assert len(ProviderRegistry()) == 0

    def test_register_and_get(self) -> None:
        registry = ProviderRegistry()
        provider = _FakeRateProvider()
        registry.register(provider)
        assert registry.get("fake_rates") is provider
        assert "fake_rates" in registry
        assert registry.names() == ["fake_rates"]

    def test_duplicate_registration_rejected(self) -> None:
        registry = ProviderRegistry()
        registry.register(_FakeRateProvider())
        with pytest.raises(ValueError, match="already registered"):
            registry.register(_FakeRateProvider())

    def test_non_provider_rejected(self) -> None:
        registry = ProviderRegistry()
        with pytest.raises(TypeError, match="Provider protocol"):
            registry.register(_NotAProvider())  # type: ignore[arg-type]

    def test_get_unknown_raises_with_known_list(self) -> None:
        registry = ProviderRegistry()
        registry.register(_FakeRateProvider("alpha"))
        with pytest.raises(ProviderUnavailableError, match="alpha"):
            registry.get("beta")

    def test_unregister(self) -> None:
        registry = ProviderRegistry()
        registry.register(_FakeRateProvider())
        registry.unregister("fake_rates")
        assert "fake_rates" not in registry

    def test_unregister_unknown_raises(self) -> None:
        with pytest.raises(ProviderUnavailableError):
            ProviderRegistry().unregister("nope")


class TestCapabilityLookup:
    def test_risk_free_providers_discovered(self) -> None:
        registry = ProviderRegistry()
        provider = _FakeRateProvider()
        registry.register(provider)
        found = registry.risk_free_providers()
        assert len(found) == 1
        assert found[0] is provider
        # It does not offer other capabilities.
        assert registry.price_history_providers() == []
        assert registry.economic_series_providers() == []

    def test_protocols_are_runtime_checkable(self) -> None:
        provider = _FakeRateProvider()
        assert isinstance(provider, RiskFreeRateProvider)
        assert not isinstance(provider, PriceHistoryProvider)
        assert not isinstance(provider, EconomicSeriesProvider)
