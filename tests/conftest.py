"""Shared fixtures.

The whole suite runs with sockets disabled (``--disable-socket`` in
``pyproject.toml``), so any accidental network call in library code fails loudly
here rather than silently passing in CI and breaking for users offline.
"""

from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture
def monthly_index() -> pd.DatetimeIndex:
    """Twelve month-end observations in 2024."""
    return pd.date_range("2024-01-31", periods=12, freq="ME")


@pytest.fixture
def hand_worked_returns(monthly_index: pd.DatetimeIndex) -> pd.Series:
    """Eleven months at +1% and one at -3%.

    Chosen because every quantity in the Sortino chain is exact in decimal
    arithmetic, so the test asserts against a derivation rather than a recorded
    output. See ``tests/unit/test_performance_sortino.py`` for the working.
    """
    return pd.Series([0.01] * 11 + [-0.03], index=monthly_index)


@pytest.fixture
def mixed_returns(monthly_index: pd.DatetimeIndex) -> pd.Series:
    """A series with both gains and losses and a genuine drawdown."""
    return pd.Series([0.01, 0.02, -0.01, 0.03] * 3, index=monthly_index)


@pytest.fixture
def all_positive(monthly_index: pd.DatetimeIndex) -> pd.Series:
    """A series that never falls: no downside, no drawdown."""
    return pd.Series([0.01] * 12, index=monthly_index)
