# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Print the SHA-256 hex digest of a file.

Used to fill an ASK record's `source.sha256` provenance field. Prints only the
lowercase 64-character hex digest to stdout (clean for capture), matching the
base schema's `^[a-f0-9]{64}$` pattern.

Run with:
    uv run scripts/sha256.py --file inbox/2026/invoices/invoice.pdf
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

# --------------------------------------------------------------------------- #
# Pure business logic (no filesystem, deterministic)
# --------------------------------------------------------------------------- #


def digest(stream, chunk_size: int = 65536) -> str:
    """SHA-256 hex digest of a binary stream, read in chunks."""
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(chunk_size), b""):
        h.update(chunk)
    return h.hexdigest()


# --------------------------------------------------------------------------- #
# Impure wrappers (filesystem / process exit)
# --------------------------------------------------------------------------- #


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Print the SHA-256 hex digest of a file.")
    parser.add_argument("--file", type=Path, required=True, help="File to hash.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if not args.file.is_file():
        print(f"error: not a file: {args.file}", file=sys.stderr)
        sys.exit(1)
    with args.file.open("rb") as stream:
        print(digest(stream))


if __name__ == "__main__":
    main()
