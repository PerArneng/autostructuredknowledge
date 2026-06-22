# /// script
# requires-python = ">=3.10"
# dependencies = ["jsonschema", "pyyaml"]
# ///
"""Validate extracted YAML against its JSON Schema.

Data types (`--type`): each YAML output is named `<base>_<name>.<type>.yaml` and
governed by `schemas/live/<type>.json`. This validates every `yaml/**/*.<type>.yaml`
for each requested type. Pass only the type(s) touched in a processing run — a
schema edit can break existing files of that type, but unrelated types are left
alone.

Logs (`--logs`): processing logs are named `<base>_<ts>.log.yaml` and governed
by the ASK-internal schema `schemas/ask/log.json`. This validates every
`log/**/*.log.yaml`.

Run with:
    uv run scripts/validate.py --type receipt [--type invoice ...]
    uv run scripts/validate.py --logs
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator
from jsonschema import FormatChecker

# --------------------------------------------------------------------------- #
# Pure business logic (no filesystem, deterministic)
# --------------------------------------------------------------------------- #


def yaml_glob_for_type(type_name: str) -> str:
    """Glob (relative to the yaml root) for every file of a given type."""
    return f"**/*.{type_name}.yaml"


def log_glob() -> str:
    """Glob (relative to the log root) for every structured log file."""
    return "**/*.log.yaml"


def validate_doc(instance: Any, schema: dict[str, Any]) -> list[str]:
    """Return human-readable validation errors for one document (empty = valid)."""
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    errors = sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    return [f"{'/'.join(str(p) for p in e.path) or '<root>'}: {e.message}" for e in errors]


# --------------------------------------------------------------------------- #
# Impure wrappers (filesystem / process exit)
# --------------------------------------------------------------------------- #


def load_schema(path: Path) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"schema not found: {path}")
    import json

    return json.loads(path.read_text(encoding="utf-8"))


def validate_files(files: list[Path], schema: dict[str, Any], root: Path) -> tuple[int, int]:
    """Validate each file against the schema; return (checked, failures)."""
    checked = 0
    failures = 0
    for path in files:
        checked += 1
        rel = path.relative_to(root)
        instance = yaml.safe_load(path.read_text(encoding="utf-8"))
        errors = validate_doc(instance, schema)
        if errors:
            failures += 1
            print(f"FAIL {rel}")
            for err in errors:
                print(f"    {err}")
        else:
            print(f"PASS {rel}")
    return checked, failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate YAML outputs against their JSON Schemas.")
    parser.add_argument(
        "--type",
        action="append",
        dest="types",
        default=[],
        metavar="TYPE",
        help="Data type to validate (repeatable). Validates yaml/**/*.<type>.yaml vs schemas/live/<type>.json.",
    )
    parser.add_argument(
        "--logs",
        action="store_true",
        help="Validate processing logs (log/**/*.log.yaml) against schemas/ask/log.json.",
    )
    args = parser.parse_args()
    if not args.types and not args.logs:
        parser.error("nothing to validate: pass --type <type> and/or --logs")
    return args


def main() -> None:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    schemas_dir = root / "schemas"

    checked = 0
    failures = 0

    for type_name in args.types:
        schema = load_schema(schemas_dir / "live" / f"{type_name}.json")
        files = sorted((root / "yaml").glob(yaml_glob_for_type(type_name)))
        if not files:
            print(f"(no files for type '{type_name}')")
            continue
        c, f = validate_files(files, schema, root)
        checked += c
        failures += f

    if args.logs:
        schema = load_schema(schemas_dir / "ask" / "log.json")
        files = sorted((root / "log").glob(log_glob()))
        if not files:
            print("(no log files)")
        else:
            c, f = validate_files(files, schema, root)
            checked += c
            failures += f

    print(f"\n{checked} checked, {failures} failed")
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
