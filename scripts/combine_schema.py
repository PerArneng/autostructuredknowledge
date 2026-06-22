# /// script
# requires-python = ">=3.10"
# dependencies = []
# ///
"""Combine the base envelope schema with each live data-type schema.

Every extracted ASK record is an envelope (`schemas/ask/base.json`) whose `data`
field holds a type-specific payload. To validate both at once, this fuses the
base schema with `schemas/live/<type>.json` into a single combined schema at
`schemas/combined/base_and_<type>.json`: the live schema is embedded under
`data` and the envelope's `type` is pinned to the type name.

Combined schemas are regenerated whenever they are missing or out of date (the
base schema or the live schema is newer) — pass `--force` to rewrite regardless.
With no `--type`, every schema in `schemas/live/` is processed.

Run with:
    uv run scripts/combine_schema.py                 # all live types
    uv run scripts/combine_schema.py --type invoice  # one type
    uv run scripts/combine_schema.py --force
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

# --------------------------------------------------------------------------- #
# Pure business logic (no filesystem, deterministic)
# --------------------------------------------------------------------------- #


def combined_name(type_name: str) -> str:
    """File name of the combined schema for a data type."""
    return f"base_and_{type_name}.json"


def embed_data_schema(live: dict[str, Any]) -> dict[str, Any]:
    """A live schema prepared for embedding as the `data` subschema.

    Strips top-level `$schema`/`$id` so it nests cleanly inside the envelope
    rather than declaring itself a separate schema resource.
    """
    embedded = dict(live)
    embedded.pop("$schema", None)
    embedded.pop("$id", None)
    return embedded


def combine(base: dict[str, Any], live: dict[str, Any], type_name: str) -> dict[str, Any]:
    """Fuse the base envelope with a live schema into one combined schema."""
    combined = json.loads(json.dumps(base))  # deep copy
    props = combined.setdefault("properties", {})
    props["data"] = embed_data_schema(live)
    props.setdefault("type", {})["const"] = type_name
    combined["title"] = f"{base.get('title', 'ASK Document Envelope')} + {live.get('title', type_name)}"
    combined["description"] = (
        f"Combined schema: the ASK envelope with its `data` payload validated by "
        f"the live `{type_name}` schema. Generated from schemas/ask/base.json and "
        f"schemas/live/{type_name}.json — do not edit by hand."
    )
    return combined


# --------------------------------------------------------------------------- #
# Impure wrappers (filesystem / process exit)
# --------------------------------------------------------------------------- #


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def is_stale(out_path: Path, *sources: Path) -> bool:
    """True if the combined schema is missing or older than any source."""
    if not out_path.exists():
        return True
    out_mtime = out_path.stat().st_mtime
    return any(src.stat().st_mtime > out_mtime for src in sources)


def live_types(live_dir: Path) -> list[str]:
    """All data-type names with a live schema, sorted."""
    return sorted(p.stem for p in live_dir.glob("*.json"))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Combine schemas/ask/base.json with live schemas into schemas/combined/."
    )
    parser.add_argument(
        "--type",
        action="append",
        dest="types",
        default=[],
        metavar="TYPE",
        help="Data type to combine (repeatable). Defaults to every schema in schemas/live/.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Rewrite combined schemas even if they are up to date.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    base_path = root / "schemas" / "ask" / "base.json"
    live_dir = root / "schemas" / "live"
    combined_dir = root / "schemas" / "combined"

    base = load_json(base_path)
    types = args.types or live_types(live_dir)
    if not types:
        print("(no live schemas to combine)")
        return

    combined_dir.mkdir(parents=True, exist_ok=True)
    for type_name in types:
        live_path = live_dir / f"{type_name}.json"
        out_path = combined_dir / combined_name(type_name)
        if not live_path.exists():
            print(f"error: no live schema for type '{type_name}': {live_path}", file=sys.stderr)
            sys.exit(1)
        if not args.force and not is_stale(out_path, base_path, live_path):
            print(f"up-to-date {type_name}")
            continue
        live = load_json(live_path)
        combined = combine(base, live, type_name)
        out_path.write_text(json.dumps(combined, indent=2) + "\n", encoding="utf-8")
        print(f"combined {type_name} -> {out_path.relative_to(root)}")


if __name__ == "__main__":
    main()
