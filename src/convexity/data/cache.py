"""A safe, offline-capable local cache for provider responses.

The cache stores raw response bytes, base64-encoded inside a small JSON record.
It never uses :mod:`pickle`: a cache is exactly the kind of untrusted store where
unpickling arbitrary objects would be a remote-code-execution risk.

Keys are hashed to a fixed-length hex digest before they become a filename, so a
caller-supplied key can never escape the cache directory through ``..`` or an
absolute path. That hashing *is* the path-traversal defence.

Writes are atomic: the record is written to a temporary file in the same
directory and then ``os.replace``d over the target, so a crash mid-write leaves
the previous entry intact rather than a truncated one. A record that is corrupt
or unreadable is treated as a cache miss, never an error.
"""

from __future__ import annotations

import base64
import enum
import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    from collections.abc import Callable

__all__ = ["CacheState", "FileCache"]


class CacheState(enum.Enum):
    """How a provider response was obtained, recorded in its provenance.

    Attributes
    ----------
    HIT
        Served from the cache during a normally cache-enabled call.
    MISS
        Not in the cache; fetched from the network and then stored.
    BYPASS
        The cache was deliberately not consulted; fetched from the network.
    OFFLINE
        Offline mode was in force and the entry was served from the cache
        instead of a network call that was not permitted to happen.
    """

    HIT = "hit"
    MISS = "miss"
    BYPASS = "bypass"
    OFFLINE = "offline"


def _utc_now() -> datetime:
    return datetime.now(UTC)


class FileCache:
    """A JSON-backed, atomic, traversal-safe response cache.

    Parameters
    ----------
    root
        Directory to store cache records in. Created if it does not exist.
    clock
        Callable returning the current UTC time. Injected so tests can control
        cache age deterministically; defaults to the real clock.

    Examples
    --------
    >>> import tempfile
    >>> cache = FileCache(tempfile.mkdtemp())
    >>> cache.get("missing") is None
    True
    >>> cache.set("k", b'{"x": 1}')
    >>> payload, age = cache.get("k")
    >>> payload
    b'{"x": 1}'
    """

    def __init__(
        self, root: str | Path, *, clock: Callable[[], datetime] = _utc_now
    ) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._clock = clock

    def _path_for(self, key: str) -> Path:
        digest = hashlib.sha256(key.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: str) -> tuple[bytes, pd.Timedelta] | None:
        """Return ``(payload, age)`` for a key, or ``None`` on miss or corruption.

        Parameters
        ----------
        key
            The cache key. Hashed before use, so any string is safe.

        Returns
        -------
        tuple of (bytes, pandas.Timedelta) or None
            The stored payload and its age, or ``None`` if the key is absent or
            the record cannot be read.
        """
        path = self._path_for(key)
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
            stored_at = pd.Timestamp(record["stored_at"])
            payload = base64.b64decode(record["payload"])
        except (OSError, ValueError, KeyError):
            # Missing, unreadable, malformed JSON, or bad base64: all a miss.
            return None
        age = pd.Timestamp(self._clock()) - stored_at
        return payload, age

    def set(self, key: str, payload: bytes) -> None:
        """Store a payload atomically under a key.

        Parameters
        ----------
        key
            The cache key. Hashed before use.
        payload
            Raw response bytes to store.
        """
        path = self._path_for(key)
        record = {
            "stored_at": pd.Timestamp(self._clock()).isoformat(),
            "payload": base64.b64encode(payload).decode("ascii"),
        }
        # Write to a unique temp file in the same directory, then atomically
        # replace: a reader never sees a half-written record.
        tmp = path.with_name(f"{path.name}.{os.getpid()}.tmp")
        tmp.write_text(json.dumps(record), encoding="utf-8")
        os.replace(tmp, path)
