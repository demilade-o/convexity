"""Concrete data providers.

These modules import optional networking dependencies (``httpx``, and for the
Yahoo adapter ``yfinance``), so they are imported explicitly by the caller and
never by the analytics core. The import contracts in ``pyproject.toml`` forbid any
core or rate module from importing this subpackage.
"""

from __future__ import annotations

__all__: list[str] = []
