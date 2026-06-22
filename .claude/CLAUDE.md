# Auto Structured Knowledge (ASK)

ASK turns arbitrary documents into structured, schema-validated YAML. A document
dropped in `inbox/` is converted to Markdown, mapped onto a JSON Schema for its
data type, and emitted as YAML that schema guarantees.

## Folders

Each stage mirrors `inbox/`'s structure, so a document's relative path is stable
end to end. Tracked: `inbox/`, `scripts/`, and `schemas/ask/`. Gitignored (regenerated
from `inbox/`): `markdown/`, `yaml/`, `log/`, `temp/`, and `schemas/live/`.

| Folder      | Role |
|-------------|------|
| `inbox/`    | Input documents, any format, any nesting. Drop files here to process. |
| `markdown/` | Markdown renderings of inbox documents. |
| `schemas/`  | JSON Schemas. Stable ASK contracts under `schemas/ask/` (tracked); dynamic data-type schemas at `schemas/live/<type>.json` (gitignored, authored by the skill). |
| `yaml/`     | Structured YAML output. |
| `log/`      | Per-document change logs, one per processing run. |
| `scripts/`  | Pipeline scripts (`next.py`, `convert.py`, `validate.py`). |
| `temp/`     | Scratch for one-off migration scripts; clear when done. |

## Pipeline

One document at a time. Each script is a [PEP-723](https://peps.python.org/pep-0723/)
uv script — `uv run scripts/<x>.py --help` for details.

1. **`next.py`** — prints the next inbox file with no YAML yet (empty when done).
   Processed = any `yaml/<mirror>/<stem>_*.yaml` exists.
2. **`convert.py --input-file <in> --md-file <out>`** — one file to Markdown via
   [`markitdown`](https://github.com/microsoft/markitdown).
3. **`process-document` skill** — extraction (judgment work): read Markdown,
   identify data type(s), author/extend `schemas/live/<type>.json`, write YAML,
   validate, log.
4. **`validate.py --type <type> [...]`** — checks `yaml/**/*.<type>.yaml` against
   `schemas/live/<type>.json`. Scope to the types touched in a run. `--logs`
   validates `log/**/*.log.yaml` against `schemas/ask/log.json`.

## Naming contract

For `inbox/2026/invoices/invoice.pdf` (base `invoice`, type `invoice`):

| Artifact | Path |
|----------|------|
| Markdown | `markdown/2026/invoices/invoice.md` |
| Schema   | `schemas/live/invoice.json` — by data **type**, not file name; shared across docs. |
| YAML     | `yaml/2026/invoices/invoice_<name>.<type>.yaml` — `<name>` is a lowercase `[a-z0-9]` slug; a doc may yield several. |
| Log      | `log/2026/invoices/invoice_<YYYYMMDD_HHMMSS>.log.yaml` — structured, conforms to `schemas/ask/log.json`. |

## Conventions

- Schemas should be *strong* (draft 2020-12, sensible `required`,
  `additionalProperties: false`), not all-optional.
- Quote dates in YAML (`"2024-03-25"`) so they stay strings for `format: date`.
- Don't hand-edit generated files; regenerate from `inbox/`.
