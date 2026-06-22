# Auto Structured Knowledge (ASK)

ASK turns arbitrary documents into structured, schema-validated YAML. Drop a file
into `inbox/` — any format, any nesting — and the pipeline converts it to
Markdown, maps it onto a JSON Schema for its data type, and emits YAML that the
schema guarantees. The repository *is* the pipeline: each stage is a folder, and a
document's relative path stays stable from `inbox/` all the way to `yaml/`.

## The envelope

Every extracted record is wrapped in a common **envelope** — a Kubernetes-CRD-like
header — so each YAML file is self-describing and carries its provenance:

```yaml
name: SuperStore Invoice 33504           # human-readable record name
type: invoice                            # the data type (== live schema name)
created: "2026-06-23T00:28:03"           # ISO 8601 date-time, quoted, no timezone
source:
  fileName: invoice_Arthur_Wiediger_33504.pdf   # original file in inbox/
  sha256: a5bffcb5ede00cef410db8483f014aea7cbfd01c12cd183b7bdee2f5578d246b
data:                                    # the type-specific payload
  invoice_number: "33504"
  issue_date: "2012-07-13"
  # ... fields defined by the live invoice schema ...
```

- The envelope itself is defined by **`schemas/ask/base.json`** (a stable contract).
- The `data` payload is defined by a per-type **live schema**, `schemas/live/<type>.json`.
- Validation runs against a **combined schema** that fuses the two, so the header
  *and* the payload are checked together in one pass.

## Folders

Tracked in git: `inbox/`, `scripts/`, and `schemas/ask/`. Everything else is
gitignored and regenerated from `inbox/`.

| Folder              | Role |
|---------------------|------|
| `inbox/`            | Input documents. Drop files here to process. |
| `markdown/`         | Markdown renderings of inbox documents. |
| `schemas/ask/`      | Stable hand-authored ASK contracts: `base.json` (envelope), `log.json`. |
| `schemas/live/`     | Dynamic per-type payload schemas, `schemas/live/<type>.json`. |
| `schemas/combined/` | Generated `base_and_<type>.json` (envelope + live); what validation checks. |
| `yaml/`             | Structured YAML output (envelope records). |
| `log/`              | Per-document change logs, one per processing run. |
| `scripts/`          | Pipeline scripts (see below). |
| `temp/`             | Scratch for one-off migration scripts; clear when done. |

## Requirements

- [`uv`](https://docs.astral.sh/uv/) — every script is a self-contained
  [PEP-723](https://peps.python.org/pep-0723/) script; `uv` fetches its
  dependencies on first run. No project virtualenv to manage.

Run all commands from the repository root. Most scripts take `--help` for their
options (`next.py` takes no arguments).

## Pipeline

One document at a time. The judgment-heavy extraction step is performed by the
`process-document` skill (see `.claude/skills/process-document/`), which drives the
scripts below.

1. **`next.py`** — print the next inbox file with no YAML yet (empty when done).

   ```sh
   uv run scripts/next.py
   ```

2. **`convert.py`** — render one document to Markdown via
   [`markitdown`](https://github.com/microsoft/markitdown).

   ```sh
   uv run scripts/convert.py --input-file <inbox-path> --md-file <markdown-path>
   ```

3. **Extract** (judgment work) — read the Markdown, identify the data type(s),
   author or extend `schemas/live/<type>.json`, and write the envelope YAML.

4. **`sha256.py`** — compute a source file's SHA-256 for the envelope's
   `source.sha256`.

   ```sh
   uv run scripts/sha256.py --file <inbox-path>
   ```

5. **`combine_schema.py`** — fuse `schemas/ask/base.json` with each live schema
   into `schemas/combined/base_and_<type>.json`. Regenerates only when missing or
   stale; never hand-edit the combined output.

   ```sh
   uv run scripts/combine_schema.py [--type <type>] [--force]
   ```

6. **`validate.py`** — refresh the combined schema(s), then validate the touched
   types (envelope + payload). `--logs` validates the run logs instead.

   ```sh
   uv run scripts/validate.py --type <type> [--type <other> ...]
   uv run scripts/validate.py --logs
   ```

7. **Log** — record the run as a structured YAML log under `log/`, conforming to
   `schemas/ask/log.json`.

## Naming contract

For `inbox/2026/invoices/invoice.pdf` (base `invoice`, type `invoice`):

| Artifact        | Path |
|-----------------|------|
| Markdown        | `markdown/2026/invoices/invoice.md` |
| Live schema     | `schemas/live/invoice.json` — by data **type**, shared across docs. |
| Combined schema | `schemas/combined/base_and_invoice.json` — generated. |
| YAML            | `yaml/2026/invoices/invoice_<name>.<type>.yaml` — `<name>` is a lowercase `[a-z0-9]` slug; a doc may yield several. |
| Log             | `log/2026/invoices/invoice_<YYYYMMDD_HHMMSS>.log.yaml` |

A single document may yield several records (multiple types, or several of one
type). Each gets its own YAML file and repeats the same `source` block.

## Conventions

- A live schema describes the `data` payload **only** — never repeat the envelope
  fields (`name`, `type`, `created`, `source`) in it.
- Schemas should be *strong*: draft 2020-12, a sensible `required` list,
  `additionalProperties: false`. Resist making everything optional just to pass.
- Quote dates and date-like values in YAML (`"2024-03-25"`,
  `created: "2026-06-22T14:30:05"`) so they stay strings for `format: date` and the
  envelope's `created` pattern, rather than being parsed into native date objects.
- Don't hand-edit generated files (`markdown/`, `yaml/`, `log/`, `schemas/live/`,
  `schemas/combined/`) — regenerate them from `inbox/`.

## Quick start

```sh
# 1. See what's next
uv run scripts/next.py

# 2. Convert it to Markdown
uv run scripts/convert.py \
  --input-file inbox/2026/invoices/invoice.pdf \
  --md-file   markdown/2026/invoices/invoice.md

# 3. Extract: author schemas/live/<type>.json and write the envelope YAML
#    (filling source.sha256 from `uv run scripts/sha256.py --file <inbox-path>`)

# 4. Validate the type you touched
uv run scripts/validate.py --type invoice
```
