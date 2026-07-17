"""Provenance and the data envelope: immutable, and never a place secrets hide.

Provenance is the audit trail a reproducible result depends on, so it must not be
mutable after the fact. The mapping fields are frozen on construction; attempting
to edit them is an error, not a silent success.
"""

from __future__ import annotations

import pandas as pd
import pytest

from convexity.data import CacheState, DataEnvelope, Provenance


def _provenance(**overrides: object) -> Provenance:
    base: dict[str, object] = {
        "provider": "example",
        "dataset": "demo",
        "retrieved_at": pd.Timestamp("2024-01-01", tz="UTC"),
        "source_url": "https://example.test/demo",
        "terms_url": "https://example.test/terms",
        "attribution": "Example",
        "units": "decimal",
        "cache_state": CacheState.MISS,
    }
    base.update(overrides)
    return Provenance(**base)  # type: ignore[arg-type]


class TestProvenance:
    def test_request_params_frozen(self) -> None:
        prov = _provenance(request_params={"a": "1"})
        with pytest.raises(TypeError):
            prov.request_params["b"] = "2"  # type: ignore[index]

    def test_field_mapping_frozen(self) -> None:
        prov = _provenance(field_mapping={"raw": "clean"})
        with pytest.raises(TypeError):
            prov.field_mapping["x"] = "y"  # type: ignore[index]

    def test_mapping_is_copied_not_aliased(self) -> None:
        source = {"a": "1"}
        prov = _provenance(request_params=source)
        source["a"] = "mutated"
        # The envelope's copy is unaffected by later edits to the caller's dict.
        assert prov.request_params["a"] == "1"

    def test_dataclass_is_frozen(self) -> None:
        prov = _provenance()
        with pytest.raises((AttributeError, TypeError)):
            prov.provider = "other"  # type: ignore[misc]

    def test_defaults_are_empty_not_shared(self) -> None:
        a = _provenance()
        b = _provenance()
        assert a.request_params == {}
        assert a.warnings == ()
        assert a.research_only is False
        assert a.request_params is not b.request_params


class TestDataEnvelope:
    def test_binds_data_to_provenance(self) -> None:
        series = pd.Series([0.05, 0.04])
        env = DataEnvelope(series, _provenance())
        pd.testing.assert_series_equal(env.data, series)
        assert env.provenance.provider == "example"

    def test_frozen(self) -> None:
        env = DataEnvelope(pd.Series([1.0]), _provenance())
        with pytest.raises((AttributeError, TypeError)):
            env.data = pd.Series([2.0])  # type: ignore[misc]
