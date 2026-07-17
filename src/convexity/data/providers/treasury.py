"""U.S. Treasury Fiscal Data: a key-free official rate provider.

The Fiscal Data API (<https://fiscaldata.treasury.gov/api-documentation/>) serves
U.S. federal financial data as JSON, requires no API key, and is U.S. Government
work. This adapter reads the *Average Interest Rates on U.S. Treasury Securities*
dataset and returns the Treasury Bills row as a USD risk-free proxy.

Honesty about what this is
--------------------------
``avg_interest_rate_amt`` is the average interest rate on the *outstanding stock*
of a security type, not a new-issue bill yield. It is a legitimate, official,
key-free short-rate proxy and it is documented as exactly that -- a portfolio
average, published monthly -- in the provenance warnings, so a caller is never
misled into treating it as a current-coupon yield.

No data ships with this package. The adapter fetches at runtime, on the caller's
behalf and under their acceptance of the Fiscal Data terms. Contract tests use
constructed fixtures that mimic the documented response shape, never captured
responses.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import TYPE_CHECKING

import pandas as pd

from convexity.conventions import Compounding, DayCount
from convexity.data.cache import CacheState
from convexity.data.models import DataEnvelope, Provenance
from convexity.exceptions import ProviderResponseError, ProviderUnavailableError
from convexity.rates import RateInstrument, RiskFreeSeries

if TYPE_CHECKING:
    from collections.abc import Callable

    from convexity.data._transport import RetryingTransport
    from convexity.data.cache import FileCache

__all__ = ["TreasuryFiscalDataProvider"]


def _utc_now() -> datetime:
    return datetime.now(UTC)


class TreasuryFiscalDataProvider:
    """Risk-free USD rates from the U.S. Treasury Fiscal Data API.

    Parameters
    ----------
    transport
        The HTTP transport to fetch through. Injected, so tests supply a mocked
        client and production supplies a real one with connection reuse.
    cache
        Optional response cache. When present, responses are cached and an
        offline call can be served from it.
    clock
        UTC clock, injected for deterministic provenance timestamps in tests.

    Notes
    -----
    Satisfies :class:`~convexity.data.protocols.RiskFreeRateProvider`.
    """

    #: API base, documented and stable.
    BASE_URL = "https://api.fiscaldata.treasury.gov/services/api/fiscal_service"
    #: Average Interest Rates on U.S. Treasury Securities.
    ENDPOINT = "/v2/accounting/od/avg_interest_rates"
    TERMS_URL = "https://fiscaldata.treasury.gov/api-documentation/"

    # Provider metadata, constant for this provider. These class attributes
    # satisfy the read-only properties of the Provider protocol structurally.
    name = "us_treasury_fiscal_data"
    terms_url = TERMS_URL
    attribution = (
        "Source: U.S. Department of the Treasury, Bureau of the Fiscal Service, "
        "Fiscal Data (fiscaldata.treasury.gov). U.S. Government work; no "
        "endorsement of this library is implied."
    )
    requires_auth = False
    research_only = False

    def __init__(
        self,
        transport: RetryingTransport,
        *,
        cache: FileCache | None = None,
        clock: Callable[[], datetime] = _utc_now,
    ) -> None:
        self._transport = transport
        self._cache = cache
        self._clock = clock

    # -- capability --------------------------------------------------------- #

    def fetch_risk_free(
        self,
        *,
        security_desc: str = "Treasury Bills",
        start: pd.Timestamp | None = None,
        end: pd.Timestamp | None = None,
        offline: bool = False,
        use_cache: bool = True,
    ) -> DataEnvelope[RiskFreeSeries]:
        """Fetch a USD risk-free rate history wrapped in provenance.

        Parameters
        ----------
        security_desc
            Security description to select, matching the dataset's own labels.
            Defaults to ``"Treasury Bills"``.
        start, end
            Optional inclusive date bounds.
        offline
            If ``True``, serve only from the cache and never touch the network.
            Raises if no cached copy exists.
        use_cache
            If ``False``, bypass the cache and fetch live.

        Returns
        -------
        DataEnvelope[RiskFreeSeries]
            The rate series and its provenance.

        Raises
        ------
        ProviderUnavailableError
            In offline mode with no cached copy.
        ProviderResponseError
            If the response cannot be parsed into a rate series.
        """
        params = self._build_params(security_desc, start, end)
        payload, state, age = self._load(params, offline=offline, use_cache=use_cache)
        rates = self._parse(payload)
        series = RiskFreeSeries(
            rates,
            currency="USD",
            tenor="ON",
            compounding=Compounding.SIMPLE,
            day_count=DayCount.ACT_365F,
            instrument=RateInstrument.TREASURY_BILL,
            source=f"{self.name}/avg_interest_rates/{security_desc}",
            retrieved_at=pd.Timestamp(self._clock()),
            terms_url=self.TERMS_URL,
        )
        provenance = Provenance(
            provider=self.name,
            dataset="avg_interest_rates",
            retrieved_at=pd.Timestamp(self._clock()),
            source_url=f"{self.BASE_URL}{self.ENDPOINT}",
            terms_url=self.TERMS_URL,
            attribution=self.attribution,
            units="decimal annual rate",
            cache_state=state,
            currency="USD",
            frequency="monthly",
            cache_age=age,
            request_params=params,
            field_mapping={
                "record_date": "observation date",
                "avg_interest_rate_amt": "annual rate (percent, divided by 100)",
            },
            warnings=(
                "avg_interest_rate_amt is the average rate on the outstanding "
                "stock of the security type, published monthly -- a portfolio "
                "average, not a new-issue bill yield. Treat it as a coarse "
                "short-rate proxy.",
            ),
            research_only=False,
        )
        return DataEnvelope(series, provenance)

    # -- internals ---------------------------------------------------------- #

    def _build_params(
        self, security_desc: str, start: pd.Timestamp | None, end: pd.Timestamp | None
    ) -> dict[str, str]:
        filters = [f"security_desc:eq:{security_desc}"]
        if start is not None:
            filters.append(f"record_date:gte:{pd.Timestamp(start).date()}")
        if end is not None:
            filters.append(f"record_date:lte:{pd.Timestamp(end).date()}")
        return {
            "fields": "record_date,security_desc,avg_interest_rate_amt",
            "filter": ",".join(filters),
            "sort": "record_date",
            # This monthly series is small; a single large page is complete and
            # avoids non-deterministic multi-page assembly.
            "page[size]": "10000",
        }

    def _cache_key(self, params: dict[str, str]) -> str:
        return f"{self.name}{self.ENDPOINT}?{json.dumps(params, sort_keys=True)}"

    def _load(
        self, params: dict[str, str], *, offline: bool, use_cache: bool
    ) -> tuple[bytes, CacheState, pd.Timedelta | None]:
        key = self._cache_key(params)
        if offline:
            cached = self._cache.get(key) if self._cache is not None else None
            if cached is None:
                msg = (
                    "offline mode is set but no cached response exists for this "
                    "request. Run once online to populate the cache, or disable "
                    "offline mode."
                )
                raise ProviderUnavailableError(msg)
            payload, age = cached
            return payload, CacheState.OFFLINE, age

        if use_cache and self._cache is not None:
            cached = self._cache.get(key)
            if cached is not None:
                payload, age = cached
                return payload, CacheState.HIT, age
            payload = self._fetch(params)
            self._cache.set(key, payload)
            return payload, CacheState.MISS, None

        return self._fetch(params), CacheState.BYPASS, None

    def _fetch(self, params: dict[str, str]) -> bytes:
        response = self._transport.get(f"{self.BASE_URL}{self.ENDPOINT}", params=params)
        if response.status_code != 200:
            msg = (
                f"Treasury Fiscal Data returned {response.status_code} for "
                f"{self.ENDPOINT}. The dataset or filter may be wrong."
            )
            raise ProviderResponseError(msg)
        return response.content

    def _parse(self, payload: bytes) -> pd.Series:
        try:
            document = json.loads(payload)
            records = document["data"]
        except (ValueError, KeyError, TypeError) as exc:
            msg = (
                f"could not parse the Treasury Fiscal Data response: {exc}. The API "
                f"schema may have changed; expected a JSON object with a 'data' array."
            )
            raise ProviderResponseError(msg) from exc

        if not records:
            msg = (
                "Treasury Fiscal Data returned no rows for the request. Check the "
                "security_desc label and any date bounds."
            )
            raise ProviderResponseError(msg)

        try:
            dates = pd.to_datetime([row["record_date"] for row in records])
            values = [float(row["avg_interest_rate_amt"]) / 100.0 for row in records]
        except (KeyError, ValueError, TypeError) as exc:
            msg = (
                f"unexpected row shape in the Treasury Fiscal Data response: {exc}. "
                f"Expected 'record_date' and numeric 'avg_interest_rate_amt' fields."
            )
            raise ProviderResponseError(msg) from exc

        return pd.Series(values, index=pd.DatetimeIndex(dates)).sort_index()
