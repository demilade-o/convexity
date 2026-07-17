"""The normalised data envelope: data that knows where it came from.

Every provider fetch returns a :class:`DataEnvelope`, never a bare Series or
DataFrame. The reason is reproducibility: a number is only trustworthy if you can
say which provider served it, for what request, when it was retrieved, under what
licence, and whether it came from a live call or a cache. Losing that context is
how a research result becomes impossible to reproduce a year later.

Provenance is stored on the envelope, not in ``DataFrame.attrs``, because attrs
are silently dropped by most pandas operations -- the first ``.resample()`` or
merge would discard exactly the audit trail that matters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Mapping

    import pandas as pd

from convexity.data.cache import CacheState

__all__ = ["DataEnvelope", "Provenance"]


def _freeze(mapping: Mapping[str, str] | None) -> Mapping[str, str]:
    """Return a read-only copy so envelope provenance cannot be edited in place."""
    return MappingProxyType(dict(mapping) if mapping else {})


@dataclass(frozen=True, eq=False)
class Provenance:
    """Where a piece of data came from, and under what terms.

    Attributes
    ----------
    provider
        Provider name, matching its :attr:`~convexity.data.protocols.Provider.name`.
    dataset
        Dataset or series identifier within the provider.
    retrieved_at
        UTC timestamp at which the data was obtained (from the live source or the
        cache write, as applicable).
    source_url
        The exact URL the data was fetched from, secrets stripped.
    terms_url
        Link to the provider's terms of use.
    attribution
        Attribution text the provider requires to be displayed.
    units
        Units of the returned values, for example ``"decimal annual rate"``.
    cache_state
        Whether this response came from the network or the cache. See
        :class:`~convexity.data.cache.CacheState`.
    currency
        ISO 4217 code where applicable, else ``None``.
    frequency
        Observation frequency label where known, else ``None``.
    cache_age
        Age of the cached entry when served from cache, else ``None``.
    request_params
        The request parameters, stored read-only. Never contains credentials.
    field_mapping
        Raw-source field name to normalised field name, stored read-only.
    warnings
        Any quality or licensing warnings raised during retrieval.
    research_only
        Whether the provider is licensed for research/personal use only.

    Notes
    -----
    Equality is by identity (``eq=False``); a provenance record is a description
    of one retrieval event, not a value to be compared.
    """

    provider: str
    dataset: str
    retrieved_at: pd.Timestamp
    source_url: str
    terms_url: str
    attribution: str
    units: str
    cache_state: CacheState
    currency: str | None = None
    frequency: str | None = None
    cache_age: pd.Timedelta | None = None
    request_params: Mapping[str, str] = field(default_factory=dict)
    field_mapping: Mapping[str, str] = field(default_factory=dict)
    warnings: tuple[str, ...] = ()
    research_only: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "request_params", _freeze(self.request_params))
        object.__setattr__(self, "field_mapping", _freeze(self.field_mapping))


@dataclass(frozen=True, eq=False)
class DataEnvelope[T]:
    """Retrieved data bound to its :class:`Provenance`.

    Attributes
    ----------
    data
        The normalised, package-owned payload -- a Series, DataFrame, or a domain
        model such as :class:`~convexity.rates.RiskFreeSeries`. Never a
        provider-specific object.
    provenance
        The provenance record for this retrieval.

    Examples
    --------
    >>> import pandas as pd
    >>> from convexity.data import CacheState
    >>> prov = Provenance(
    ...     provider="example", dataset="demo",
    ...     retrieved_at=pd.Timestamp("2024-01-01", tz="UTC"),
    ...     source_url="https://example.test/demo", terms_url="https://example.test",
    ...     attribution="Example", units="decimal", cache_state=CacheState.MISS)
    >>> env = DataEnvelope(pd.Series([0.05]), prov)
    >>> env.provenance.cache_state.value
    'miss'
    """

    data: T
    provenance: Provenance
