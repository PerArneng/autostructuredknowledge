# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Print the next unprocessed inbox file.

Scans inbox/ recursively and prints the repo-root-relative path of the first
file that has no corresponding YAML output yet. A source is "processed" when one
or more YAML files mirror its path with a `_*.yaml` suffix, e.g.
`inbox/2026/invoices/invoice.pdf` is done once any `yaml/2026/invoices/invoice_*.yaml`
exists. Prints nothing (exit 0) when everything is processed, so a loop can do:

    while f=$(uv run scripts/next.py); [ -n "$f" ]; do ...process "$f"...; done

Run with: uv run scripts/next.py
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

# --------------------------------------------------------------------------- #
# Pure business logic (no filesystem, deterministic)
# --------------------------------------------------------------------------- #


def yaml_glob(src: Path, inbox: Path, yaml_dir: Path) -> tuple[Path, str]:
    """Directory + glob pattern that a source's YAML outputs would mirror."""
    rel = src.relative_to(inbox)
    return yaml_dir / rel.parent, f"{src.stem}_*.yaml"


def is_ignored(src: Path) -> bool:
    """Dotfiles like .gitkeep are not documents to process."""
    return src.name.startswith(".")


def is_processed(matches: Sequence[Path]) -> bool:
    """A source is processed when at least one YAML output exists for it."""
    return len(matches) > 0


def find_next(
    srcs: Sequence[Path],
    inbox: Path,
    yaml_dir: Path,
    matcher: Callable[[Path, str], Sequence[Path]],
) -> Path | None:
    """First non-ignored source with no YAML matches; None if all processed."""
    for src in srcs:
        if is_ignored(src):
            continue
        directory, pattern = yaml_glob(src, inbox, yaml_dir)
        if not is_processed(matcher(directory, pattern)):
            return src
    return None


# --------------------------------------------------------------------------- #
# Impure wrappers (filesystem only — no business rules)
# --------------------------------------------------------------------------- #


def discover(inbox: Path) -> list[Path]:
    """All files under inbox/, recursively, sorted for deterministic order."""
    return sorted(p for p in inbox.rglob("*") if p.is_file())


def glob_yaml(directory: Path, pattern: str) -> list[Path]:
    """YAML files matching pattern in directory (empty if it does not exist)."""
    return sorted(directory.glob(pattern))


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    inbox = root / "inbox"
    yaml_dir = root / "yaml"

    nxt = find_next(discover(inbox), inbox, yaml_dir, glob_yaml)
    if nxt is not None:
        print(nxt.relative_to(root))


if __name__ == "__main__":
    main()
