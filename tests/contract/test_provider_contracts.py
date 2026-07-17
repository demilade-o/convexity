"""Every provider must satisfy the same capability contract.

Contract tests check the *shape* a provider promises -- its metadata and the
capability protocols it claims -- independently of any one provider's wiring. A
new provider added later is held to exactly these assertions.
"""

from __future__ import annotations

import httpx
import pytest

from convexity.data._transport import RetryingTransport
from convexity.data.protocols import (
    EconomicSeriesProvider,
    PriceHistoryProvider,
    Provider,
    RiskFreeRateProvider,
)
from convexity.data.providers.treasury import TreasuryFiscalDataProvider
from convexity.data.providers.yahoo import YahooFinanceProvider


def _all_providers() -> list[Provider]:
    return [
        TreasuryFiscalDataProvider(RetryingTransport(httpx.Client())),
        YahooFinanceProvider(),
    ]


@pytest.mark.parametrize("provider", _all_providers(), ids=lambda p: p.name)
class TestProviderMetadataContract:
    def test_satisfies_provider_protocol(self, provider: Provider) -> None:
        assert isinstance(provider, Provider)

    def test_name_is_nonempty(self, provider: Provider) -> None:
        assert provider.name.strip()

    def test_terms_url_is_a_link(self, provider: Provider) -> None:
        assert provider.terms_url.startswith("https://")

    def test_attribution_is_substantive(self, provider: Provider) -> None:
        # Attribution is a licence obligation, not decoration.
        assert len(provider.attribution) > 20

    def test_auth_and_research_flags_are_bool(self, provider: Provider) -> None:
        assert isinstance(provider.requires_auth, bool)
        assert isinstance(provider.research_only, bool)


class TestDeclaredCapabilities:
    def test_treasury_is_a_risk_free_provider(self) -> None:
        provider = TreasuryFiscalDataProvider(RetryingTransport(httpx.Client()))
        assert isinstance(provider, RiskFreeRateProvider)
        assert not isinstance(provider, PriceHistoryProvider)

    def test_yahoo_is_a_price_history_provider(self) -> None:
        provider = YahooFinanceProvider()
        assert isinstance(provider, PriceHistoryProvider)
        assert not isinstance(provider, RiskFreeRateProvider)
        assert not isinstance(provider, EconomicSeriesProvider)

    def test_research_only_flags_are_honest(self) -> None:
        # An official government source is not research-only; a personal-use
        # scraper is. The flag must match reality, because callers gate on it.
        assert (
            TreasuryFiscalDataProvider(RetryingTransport(httpx.Client())).research_only
            is False
        )
        assert YahooFinanceProvider().research_only is True
