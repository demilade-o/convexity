"""Single source of truth for the package version.

Read at build time by Hatchling (``[tool.hatch.version] path``) and re-exported
as :data:`convexity.__version__`. See ``docs/adr/0005-versioning.md``.
"""

from __future__ import annotations

__version__ = "0.1.0"
