#!/usr/bin/env python3
"""Refuse to stage files that must never enter version control.

A pre-commit guard, not a substitute for one. ``.gitignore`` and
``.git/info/exclude`` already keep these paths out of the working index; this
catches the case where someone reaches past them with ``git add -f``, and the
case where a genuinely new category of secret has no ignore rule yet.

The cost asymmetry justifies the duplication: a rejected commit costs seconds,
whereas a credential or a licensed dataset in git history survives deletion and
must be treated as compromised.

Invoked by pre-commit with the staged paths as arguments.
"""

from __future__ import annotations

import re
import sys

# (pattern, why it must not be committed)
FORBIDDEN: tuple[tuple[str, str], ...] = (
    (r"(^|/)ref/", "private working directory"),
    (r"(^|/)\.env($|\.)", "environment file (may contain credentials)"),
    (r"\.(pem|key|p12|pfx|jks)$", "credential material"),
    (r"(^|/)secrets?\.(toml|yaml|yml|json|ini)$", "secrets file"),
    (r"(^|/)\.convexity-cache/", "provider response cache"),
    (r"(^|/)\.venv/", "virtual environment"),
    (r"(^|/)__pycache__/", "bytecode cache"),
    (r"\.pyc$", "bytecode"),
    # This project ships no market data. A data file under test fixtures is far
    # more likely to be captured provider output -- which may be licensed -- than
    # something we are entitled to redistribute.
    (r"\.(csv|parquet|feather|h5|hdf5|xlsx|pkl|pickle)$", "possible provider data"),
)


def main(paths: list[str]) -> int:
    """Check staged paths and report any that are forbidden."""
    failures: list[str] = []

    for path in paths:
        for pattern, reason in FORBIDDEN:
            if re.search(pattern, path):
                failures.append(f"  {path}\n      -> {reason}")
                break

    if failures:
        print("Refusing to commit. These staged paths must never be tracked:\n")
        print("\n".join(failures))
        print(
            "\nIf a data file is genuinely redistributable and required, add an "
            "explicit exception to scripts/check_staged.py in the same commit, "
            "with the licence recorded in docs/providers/provider-matrix.md."
        )
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
