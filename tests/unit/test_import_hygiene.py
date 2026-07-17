"""Importing the package must load no networking, in a fresh interpreter.

The guarantee that analytics never touch the network starts at import time: a
user who runs ``import convexity`` on a locked-down box, or inside a function that
must not perform I/O, must not pull in httpx, the data layer, or yfinance. A
subprocess proves it against a clean module table, not one this test session has
already populated.
"""

from __future__ import annotations

import subprocess
import sys


def test_importing_convexity_loads_no_networking() -> None:
    code = (
        "import sys, convexity\n"
        "for mod in ('httpx', 'yfinance', 'convexity.data', "
        "'convexity.data.providers.treasury'):\n"
        "    assert mod not in sys.modules, mod + ' was imported'\n"
        "print('clean')\n"
    )
    result = subprocess.run(  # noqa: S603 - fixed command, no external input
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "clean"
