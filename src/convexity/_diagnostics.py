"""Environment diagnostics.

A bug report that says "the number looks wrong" is unactionable without knowing
which NumPy and pandas produced it -- as this project learned when pandas 3.0
changed its default datetime resolution and silently altered frequency
inference. :func:`show_versions` exists so a reporter can paste one block.
"""

from __future__ import annotations

import platform
import sys
from importlib import metadata

from convexity._version import __version__

__all__ = ["show_versions", "versions"]

# Optional dependencies are reported when present and marked absent otherwise:
# "which extras are installed" is frequently the answer to a provider bug.
_PACKAGES = ("numpy", "pandas", "httpx", "yfinance")


def versions() -> dict[str, str]:
    """Return environment information as a plain dictionary.

    Returns
    -------
    dict of str to str
        Package, interpreter, and platform versions. Optional dependencies that
        are not installed are reported as ``"not installed"`` rather than
        omitted, so their absence is visible.

    Examples
    --------
    >>> info = versions()
    >>> info["convexity"] == __version__
    True
    """
    info: dict[str, str] = {
        "convexity": __version__,
        "python": sys.version.split()[0],
        "python_build": platform.python_implementation(),
        "os": f"{platform.system()} {platform.release()}",
        "machine": platform.machine(),
    }

    for package in _PACKAGES:
        try:
            info[package] = metadata.version(package)
        except metadata.PackageNotFoundError:
            info[package] = "not installed"

    return info


def show_versions() -> None:
    """Print environment information for inclusion in a bug report.

    Examples
    --------
    >>> show_versions()  # doctest: +ELLIPSIS
    convexity...
    """
    info = versions()
    width = max(len(key) for key in info)
    for key, value in info.items():
        print(f"{key.ljust(width)} : {value}")
