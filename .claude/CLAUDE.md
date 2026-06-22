# Auto Structured Knowledge (ASK)

ASK turns arbitrary documents into structured, schema-validated YAML. A document
dropped in `inbox/` is converted to Markdown, mapped onto a JSON Schema for its
data type, and emitted as YAML that schema guarantees.

Every record is wrapped in a common **envelope** (a Kubernetes-CRD-like header)
defined by `schemas/ask/base.json`: top-level `name`, `type`, `created`, and
`source` (originating file `fileName` + `sha256`), with the type-specific payload
nested under `data`. Validation runs against a *combined* schema that fuses the
base envelope with the data-type schema, so header and payload are checked together.

## Folders

Each stage mirrors `inbox/`'s structure, so a document's relative path is stable
end to end. Tracked: `inbox/`, `scripts/`, and `schemas/ask/`. Gitignored (regenerated
from `inbox/`): `markdown/`, `yaml/`, `log/`, `temp/`, `schemas/live/`, and
`schemas/combined/`.

| Folder      | Role |
|-------------|------|
| `inbox/`    | Input documents, any format, any nesting. Drop files here to process. |
| `markdown/` | Markdown renderings of inbox documents. |
| `schemas/`  | JSON Schemas. Stable ASK contracts under `schemas/ask/` (tracked: `base.json` envelope, `log.json`); dynamic data-type schemas at `schemas/live/<type>.json` and generated `schemas/combined/base_and_<type>.json` (both gitignored). |
| `yaml/`     | Structured YAML output (envelope records). |
| `log/`      | Per-document change logs, one per processing run. |
| `scripts/`  | Pipeline scripts (`next.py`, `convert.py`, `sha256.py`, `combine_schema.py`, `validate.py`). |
| `temp/`     | Scratch for one-off migration scripts; clear when done. |

## Pipeline

One document at a time. Each script is a [PEP-723](https://peps.python.org/pep-0723/)
uv script — `uv run scripts/<x>.py --help` for details.

1. **`next.py`** — prints the next inbox file with no YAML yet (empty when done).
   Processed = any `yaml/<mirror>/<stem>_*.yaml` exists.
2. **`convert.py --input-file <in> --md-file <out>`** — one file to Markdown via
   [`markitdown`](https://github.com/microsoft/markitdown).
3. **`process-document` skill** — extraction (judgment work): read Markdown,
   identify data type(s), author/extend `schemas/live/<type>.json`, write YAML
   (envelope form), validate, log.
4. **`sha256.py --file <in>`** — prints a source file's SHA-256, for the
   envelope's `source.sha256`.
5. **`combine_schema.py [--type <type>]`** — fuses `schemas/ask/base.json` with
   each `schemas/live/<type>.json` into `schemas/combined/base_and_<type>.json`.
   Regenerates when missing or stale; never hand-edit the combined output.
6. **`validate.py --type <type> [...]`** — refreshes the combined schema, then
   checks `yaml/**/*.<type>.yaml` against `schemas/combined/base_and_<type>.json`
   (envelope + payload). Scope to the types touched in a run. `--logs` validates
   `log/**/*.log.yaml` against `schemas/ask/log.json`.

## Naming contract

For `inbox/2026/invoices/invoice.pdf` (base `invoice`, type `invoice`):

| Artifact | Path |
|----------|------|
| Markdown | `markdown/2026/invoices/invoice.md` |
| Live schema | `schemas/live/invoice.json` — the `data` payload, by data **type** not file name; shared across docs. |
| Combined schema | `schemas/combined/base_and_invoice.json` — generated (base envelope + live); what `validate.py` checks against. |
| YAML     | `yaml/2026/invoices/invoice_<name>.<type>.yaml` — `<name>` is a lowercase `[a-z0-9]` slug; a doc may yield several. |
| Log      | `log/2026/invoices/invoice_<YYYYMMDD_HHMMSS>.log.yaml` — structured, conforms to `schemas/ask/log.json`. |

Each YAML file is an envelope — `name`, `type`, `created`, `source`, `data` —
where `data` holds the type-specific payload validated by the live schema.

## Conventions

- A live schema describes the `data` payload only; the envelope fields come from
  `schemas/ask/base.json`. Don't repeat envelope fields in a live schema.
- Schemas should be *strong* (draft 2020-12, sensible `required`,
  `additionalProperties: false`), not all-optional.
- Quote dates in YAML (`"2024-03-25"`, `created: "2026-06-22T14:30:05"`) so they
  stay strings for `format: date` / the envelope's `created` pattern.
- After authoring/extending a live schema, regenerate its combined schema
  (`combine_schema.py`); `validate.py` also refreshes it automatically.
- Don't hand-edit generated files (`schemas/combined/`, `markdown/`, `yaml/`,
  `log/`); regenerate from `inbox/`.
