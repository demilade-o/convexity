"""The response cache: atomic, offline-capable, and corruption-tolerant.

The cache is a security surface (it deserialises stored data) and a correctness
surface (a stale or corrupt entry must never masquerade as a fresh one). These
tests pin both: a controllable clock drives the age arithmetic, and deliberately
corrupt records must read back as a miss rather than an exception.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import pandas as pd
import pytest

from convexity.data.cache import CacheState, FileCache


class _Clock:
    """A movable UTC clock for deterministic cache-age assertions."""

    def __init__(self, start: datetime) -> None:
        self.now = start

    def __call__(self) -> datetime:
        return self.now

    def advance(self, **kwargs: float) -> None:
        self.now += timedelta(**kwargs)


@pytest.fixture
def clock() -> _Clock:
    return _Clock(datetime(2024, 1, 1, tzinfo=UTC))


class TestRoundTrip:
    def test_miss_on_absent_key(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path)
        assert cache.get("nope") is None

    def test_stores_and_reads_back_exact_bytes(
        self, tmp_path: Path, clock: _Clock
    ) -> None:
        cache = FileCache(tmp_path, clock=clock)
        cache.set("k", b'{"rate": 0.05}')
        result = cache.get("k")
        assert result is not None
        payload, age = result
        assert payload == b'{"rate": 0.05}'
        assert age == pd.Timedelta(0)

    def test_age_reflects_elapsed_time(self, tmp_path: Path, clock: _Clock) -> None:
        cache = FileCache(tmp_path, clock=clock)
        cache.set("k", b"data")
        clock.advance(hours=6)
        result = cache.get("k")
        assert result is not None
        _, age = result
        assert age == pd.Timedelta(hours=6)

    def test_overwrite_replaces_value(self, tmp_path: Path, clock: _Clock) -> None:
        cache = FileCache(tmp_path, clock=clock)
        cache.set("k", b"first")
        cache.set("k", b"second")
        result = cache.get("k")
        assert result is not None
        assert result[0] == b"second"


class TestSafety:
    def test_creates_missing_root(self, tmp_path: Path) -> None:
        nested = tmp_path / "a" / "b" / "cache"
        FileCache(nested)
        assert nested.is_dir()

    def test_traversal_key_stays_within_root(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path)
        # A key crafted to escape the directory is hashed to a hex filename, so
        # nothing is written outside the cache root.
        cache.set("../../etc/passwd", b"x")
        written = list(tmp_path.iterdir())
        assert len(written) == 1
        assert written[0].parent == tmp_path
        assert written[0].suffix == ".json"

    def test_corrupt_record_reads_as_miss(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path)
        cache.set("k", b"payload")
        # Corrupt the stored JSON on disk.
        stored = next(tmp_path.glob("*.json"))
        stored.write_text("this is not json", encoding="utf-8")
        assert cache.get("k") is None

    def test_record_missing_fields_reads_as_miss(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path)
        cache.set("k", b"payload")
        stored = next(tmp_path.glob("*.json"))
        stored.write_text('{"stored_at": "2024-01-01"}', encoding="utf-8")
        assert cache.get("k") is None

    def test_no_temp_files_left_after_set(self, tmp_path: Path) -> None:
        cache = FileCache(tmp_path)
        cache.set("k", b"payload")
        assert not list(tmp_path.glob("*.tmp"))


def test_cache_state_values() -> None:
    assert {s.value for s in CacheState} == {"hit", "miss", "bypass", "offline"}
