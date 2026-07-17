"""A small registry for looking up providers by name or capability.

The registry holds no providers by default. A provider that requires a credential
or a network client is never constructed implicitly, so importing this module has
no side effects and an application decides for itself which providers to register.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from convexity.data.protocols import Provider
from convexity.exceptions import ProviderUnavailableError

if TYPE_CHECKING:
    from convexity.data.protocols import (
        EconomicSeriesProvider,
        PriceHistoryProvider,
        RiskFreeRateProvider,
    )

__all__ = ["ProviderRegistry"]


class ProviderRegistry:
    """Name-based and capability-based lookup of registered providers.

    Examples
    --------
    >>> registry = ProviderRegistry()
    >>> len(registry)
    0
    >>> "treasury" in registry
    False
    """

    def __init__(self) -> None:
        self._providers: dict[str, Provider] = {}

    def register(self, provider: Provider) -> None:
        """Register a provider under its :attr:`~Provider.name`.

        Parameters
        ----------
        provider
            Any object satisfying the :class:`~convexity.data.protocols.Provider`
            protocol.

        Raises
        ------
        TypeError
            If the object is not a valid provider.
        ValueError
            If a provider with the same name is already registered. Replacing one
            silently would let a later registration change which terms a fetch was
            made under.
        """
        # Defends against untyped runtime callers passing a non-provider. The
        # type checker proves this dead for well-typed code, which is exactly why
        # the branch is marked unreachable -- the guard is for the code mypy does
        # not see.
        if not isinstance(provider, Provider):
            msg = (  # type: ignore[unreachable]
                f"{provider!r} does not satisfy the Provider protocol; it must "
                f"expose name, terms_url, attribution, requires_auth and "
                f"research_only."
            )
            raise TypeError(msg)
        if provider.name in self._providers:
            msg = (
                f"a provider named {provider.name!r} is already registered; "
                f"unregister it first if replacement is intended."
            )
            raise ValueError(msg)
        self._providers[provider.name] = provider

    def unregister(self, name: str) -> None:
        """Remove a provider by name.

        Raises
        ------
        ProviderUnavailableError
            If no provider is registered under ``name``.
        """
        if name not in self._providers:
            raise ProviderUnavailableError(self._unknown_message(name))
        del self._providers[name]

    def get(self, name: str) -> Provider:
        """Return the provider registered under ``name``.

        Raises
        ------
        ProviderUnavailableError
            If no provider is registered under ``name``.
        """
        try:
            return self._providers[name]
        except KeyError:
            raise ProviderUnavailableError(self._unknown_message(name)) from None

    def names(self) -> list[str]:
        """Return the registered provider names, sorted."""
        return sorted(self._providers)

    def risk_free_providers(self) -> list[RiskFreeRateProvider]:
        """Return every registered provider offering risk-free rates."""
        from convexity.data.protocols import RiskFreeRateProvider

        return [
            p for p in self._providers.values() if isinstance(p, RiskFreeRateProvider)
        ]

    def economic_series_providers(self) -> list[EconomicSeriesProvider]:
        """Return every registered provider offering economic series."""
        from convexity.data.protocols import EconomicSeriesProvider

        return [
            p for p in self._providers.values() if isinstance(p, EconomicSeriesProvider)
        ]

    def price_history_providers(self) -> list[PriceHistoryProvider]:
        """Return every registered provider offering price histories."""
        from convexity.data.protocols import PriceHistoryProvider

        return [
            p for p in self._providers.values() if isinstance(p, PriceHistoryProvider)
        ]

    def _unknown_message(self, name: str) -> str:
        known = ", ".join(self.names()) or "none registered"
        return (
            f"no provider named {name!r} is registered (known: {known}). Register "
            f"one with ProviderRegistry.register(...) before requesting it."
        )

    def __contains__(self, name: object) -> bool:
        return name in self._providers

    def __len__(self) -> int:
        return len(self._providers)
