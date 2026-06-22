# /// script
# requires-python = ">=3.10"
# dependencies = ["markitdown[all]"]
# ///
"""Convert a single document to Markdown.

Given one input document and one Markdown destination, convert the input with
the markitdown package and write the result. Choosing paths (and mirroring the
inbox/ structure under markdown/) is the caller's responsibility.

Run with:
    uv run scripts/convert.py --input-file inbox/receipt.pdf --md-file markdown/receipt.md
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


def convert(md, input_file: Path) -> str:
    """Convert a document to Markdown text using markitdown."""
    return md.convert(str(input_file)).text_content


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Convert a document to Markdown.")
    parser.add_argument("--input-file", type=Path, required=True, help="Source document to convert.")
    parser.add_argument("--md-file", type=Path, required=True, help="Markdown file to write.")
    return parser.parse_args()


def main() -> None:
    from markitdown import MarkItDown

    args = parse_args()

    try:
        text = convert(MarkItDown(), args.input_file)
    except Exception as exc:  # markitdown raises for unsupported / unreadable files
        print(f"error: could not convert {args.input_file}: {exc}", file=sys.stderr)
        sys.exit(1)

    args.md_file.parent.mkdir(parents=True, exist_ok=True)
    args.md_file.write_text(text, encoding="utf-8")
    print(f"converted {args.input_file} -> {args.md_file}")


if __name__ == "__main__":
    main()
