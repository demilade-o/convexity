# Data providers

The computational core of `convexity` never touches the network. Data retrieval
lives entirely in `convexity.data`, behind explicit provider objects, and
importing the package or calling a metric performs no I/O. That separation is
enforced mechanically — the architecture contracts fail CI if any analytics
module imports a networking dependency.

!!! danger "Free to access is not the same as openly licensed"
    An adapter fetching data does not grant you rights over it. Those come from
    the provider and from whoever owns the underlying series. Read the
    [provider matrix](../providers/provider-matrix.md) before using any adapter,
    and read the provider's own current terms.

## Every fetch carries its provenance

A provider never returns a bare Series or DataFrame. It returns a
[`DataEnvelope`](../reference/api.md#convexity.data.models.DataEnvelope): the
normalised, package-owned data bound to a
[`Provenance`](../reference/api.md#convexity.data.models.Provenance) record
saying where it came from, for what request, when it was retrieved, under what
terms, and whether it came from the network or the cache.

The reason is reproducibility. A number is only trustworthy if you can later say
exactly how you obtained it, and provenance stored on the envelope — not in
`DataFrame.attrs`, which the first `resample` would silently drop — survives the
transformations a real analysis applies.

## Capabilities, not vendors

Providers declare what they can supply through
[capability protocols](../reference/api.md#convexity.data.protocols): a rate
provider and a price provider have genuinely different contracts. Callers depend
on the capability — `RiskFreeRateProvider`, `PriceHistoryProvider` — so a
provider can be added, mocked, or swapped without touching calling code. The
[`ProviderRegistry`](../reference/api.md#convexity.data.registry.ProviderRegistry)
looks providers up by name or by capability.

## Reliability and offline operation

Networked providers fetch through a retrying transport with per-request timeouts,
bounded retries, exponential backoff with jitter, and respect for a server's
`Retry-After`. Only transient failures — connection errors, `429`, `5xx` — are
retried; a `404` is not.

Responses are cached in a
[`FileCache`](../reference/api.md#convexity.data.cache.FileCache) that writes
atomically, stores JSON (never `pickle`), and hashes keys to safe filenames so a
crafted key cannot escape the cache directory. With `offline=True`, a provider
serves only from the cache and never opens a connection — the right mode for
reproducible or air-gapped work.

## The shipped rate provider

[`TreasuryFiscalDataProvider`](../reference/api.md#convexity.data.providers.treasury.TreasuryFiscalDataProvider)
reads the U.S. Treasury Fiscal Data API — official, JSON, and **requiring no API
key** — and returns a `RiskFreeSeries` of USD rates.

```python
import httpx
from convexity.data._transport import RetryingTransport
from convexity.data.cache import FileCache
from convexity.data.providers.treasury import TreasuryFiscalDataProvider

provider = TreasuryFiscalDataProvider(
    RetryingTransport(httpx.Client()),
    cache=FileCache("~/.cache/convexity"),
)
envelope = provider.fetch_risk_free()          # DataEnvelope[RiskFreeSeries]
series = envelope.data
print(envelope.provenance.attribution)
```

It is honest about what it returns: the Treasury *average interest rate* is a
rate on the outstanding stock of bills, published monthly — a coarse short-rate
proxy, not a new-issue yield. That caveat is surfaced in the envelope's
`warnings`, not buried.

A key-free provider is a deliberate first choice: it can be smoke-tested for real
by anyone who checks out the repository, so the claim "this integration works" is
independently verifiable rather than resting on someone's secret.

## The Yahoo research adapter

[`YahooFinanceProvider`](../reference/api.md#convexity.data.providers.yahoo.YahooFinanceProvider)
is available behind `convexity[yahoo]` and is labelled **research and personal
use only**. It is not affiliated with or endorsed by Yahoo, it is never a test or
build dependency, and no Yahoo data is ever cached to disk, shipped, or
redistributed by this project. If your use is commercial or you need a
reliability guarantee, use a provider you have a contract with.
