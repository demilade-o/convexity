#!/usr/bin/env python3
"""Verify the contents of built distributions before they can be published.

Checks, for both the wheel and the sdist:

* ``py.typed`` ships, so the package is recognised as typed by consumers;
* the licence and notice ship;
* nothing that should never leave a developer's machine is present -- local
  working directories, caches, credentials, virtual environments, or downloaded
  provider data.

The last check is the important one. This project distributes no market or
economic data, and a fixture captured from a provider could carry licensing
obligations that the project's own licence does not grant. A build that would
ship one must fail here rather than on PyPI, where it is permanent.

Run from the repository root with ``dist/`` already populated::

    python scripts/check_artefacts.py
"""

from __future__ import annotations

import re
import sys
import tarfile
import zipfile
from pathlib import Path

DIST = Path("dist")

REQUIRED_IN_WHEEL = ("convexity/py.typed", "convexity/__init__.py")

# Paths that must never appear in any artefact. Matched against POSIX-style
# member names with the leading distribution directory stripped.
FORBIDDEN_PATTERNS: tuple[tuple[str, str], ...] = (
    (r"(^|/)ref/", "private working directory"),
    (r"(^|/)\.git/", "git metadata"),
    (r"(^|/)\.venv/", "virtual environment"),
    (r"(^|/)__pycache__/", "bytecode cache"),
    (r"\.pyc$", "bytecode"),
    (r"(^|/)\.env($|\.)", "environment/credential file"),
    (r"\.(pem|key|p12|pfx)$", "credential material"),
    (r"(^|/)\.convexity-cache/", "provider response cache"),
    (r"(^|/)\.hypothesis/", "test database"),
    (r"(^|/)\.pytest_cache/", "test cache"),
    (r"(^|/)\.mypy_cache/", "type cache"),
    (r"(^|/)\.ruff_cache/", "lint cache"),
    # Bulk data formats have no business in a pure-Python analytics wheel; if one
    # appears it is almost certainly captured provider output.
    (r"\.(csv|parquet|feather|h5|hdf5|xlsx|pkl|pickle)$", "possible provider data"),
)


def _members(path: Path) -> list[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as zf:
            return zf.namelist()
    with tarfile.open(path) as tf:
        # Strip the top-level "convexity-x.y.z/" directory so patterns anchored
        # at the start behave the same for wheels and sdists.
        return [m.name.split("/", 1)[1] if "/" in m.name else m.name for m in tf]


def _check(path: Path) -> list[str]:
    failures: list[str] = []
    members = _members(path)

    for pattern, reason in FORBIDDEN_PATTERNS:
        hits = [m for m in members if re.search(pattern, m)]
        if hits:
            preview = ", ".join(hits[:3])
            failures.append(
                f"{path.name}: contains {reason} ({len(hits)} member(s)): {preview}"
            )

    if path.suffix == ".whl":
        for required in REQUIRED_IN_WHEEL:
            if not any(m == required for m in members):
                failures.append(f"{path.name}: missing required member {required!r}")
        if not any("licenses/LICENSE" in m or m.endswith("/LICENSE") for m in members):
            failures.append(f"{path.name}: no LICENSE in wheel metadata")
    else:
        for required in ("LICENSE", "NOTICE", "pyproject.toml"):
            if required not in members:
                failures.append(f"{path.name}: sdist missing {required!r}")
        if not any(m.startswith("src/convexity/") for m in members):
            failures.append(f"{path.name}: sdist ships no source")
        if "src/convexity/py.typed" not in members:
            failures.append(f"{path.name}: sdist missing py.typed")

    return failures


def main() -> int:
    """Check every artefact in dist/ and report failures."""
    artefacts = sorted(DIST.glob("*.whl")) + sorted(DIST.glob("*.tar.gz"))
    if not artefacts:
        print("FAIL: no artefacts found in dist/; run `uv build` first.")
        return 1

    all_failures: list[str] = []
    for artefact in artefacts:
        failures = _check(artefact)
        status = "FAIL" if failures else "ok"
        print(f"[{status}] {artefact.name} ({len(_members(artefact))} members)")
        all_failures.extend(failures)

    if all_failures:
        print("\nArtefact checks failed:")
        for failure in all_failures:
            print(f"  - {failure}")
        return 1

    print(f"\nAll {len(artefacts)} artefact(s) passed content checks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
