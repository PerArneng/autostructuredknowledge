---
name: process-document
description: >-
  Process the next document in the ASK pipeline: pick the next unprocessed file
  from inbox/, convert it to Markdown, extract its structured data into
  schema-validated YAML, authoring or extending JSON Schemas in schemas/ as
  needed, validate, and log the change. Use this whenever the user wants to
  process the inbox, handle "the next document", extract structured data from a
  document, turn a document/PDF/receipt/invoice into YAML, build up or refine the
  ASK schemas, or advance the ASK pipeline — even if they don't name this skill
  or say "ASK" explicitly. If a request involves moving documents from inbox/
  toward structured yaml/ output, this skill applies.
---

# Process a document (ASK pipeline)

This skill turns one inbox document into structured, schema-validated knowledge.
The repo is the pipeline: `inbox/` holds raw documents, `markdown/` holds their
text rendering, `schemas/` holds JSON Schemas (one per data *type*), `yaml/`
holds the extracted data, and `log/` records what each run changed. Three helper
scripts already exist (`scripts/next.py`, `scripts/convert.py`,
`scripts/validate.py`) — use them; don't reimplement their logic.

**Process exactly one document per invocation.** Picking one file, taking it all
the way to validated YAML, and logging it keeps each run small and auditable. The
user re-invokes the skill (or loops it) to handle the next one. If anything is
ambiguous about what data a document holds, prefer asking the user over guessing.

Run every command from the repo root.

## Workflow

### 1. Select the next document

```sh
uv run scripts/next.py
```

It prints the repo-root-relative path of the first inbox file with no YAML output
yet (e.g. `inbox/2026/invoices/invoice.pdf`). **Empty output means the inbox is
fully processed** — report that and stop; there is nothing to do.

### 2. Convert to Markdown

Derive the Markdown path by mirroring `inbox/` → `markdown/` and swapping the
extension to `.md` (`inbox/2026/invoices/invoice.pdf` →
`markdown/2026/invoices/invoice.md`), then:

```sh
uv run scripts/convert.py --input-file <inbox-path> --md-file <markdown-path>
```

Read the resulting Markdown. This text is what you reason over — the original
binary is not re-read.

### 3. Identify the data type(s)

Decide what *kinds of structured data* the document contains. The type describes
the **data, not the file name**: an `invoice.pdf` yields type `invoice`; a
calendar file yields `calendar_event`; a scanned receipt yields `receipt`. A
single document may contain more than one type (e.g. an invoice plus the vendor's
contact card) — extract each.

Use lowercase `snake_case` type names so they map cleanly to schema and file
names.

### 4. Resolve the schema for each type

Data-type schemas live flat in `schemas/live/<type>.json`, named by type and
shared across all documents of that type. `schemas/live/` is the gitignored home
for these dynamically-authored schemas — keep it distinct from `schemas/ask/`,
which holds stable hand-authored ASK contracts (e.g. the log schema) you must not
treat as fair game to edit here. List what exists first:

```sh
ls schemas/live/
```

For each type, choose one path:
- **Fits as-is** → use the existing schema unchanged.
- **Exists but missing fields** the document clearly provides → **extend** it
  (add the new properties; mark them `required` if such documents reliably carry
  them).
- **No schema yet** → **author** `schemas/live/<type>.json`.

Write real JSON Schema (draft 2020-12). A good schema is *strong*, not permissive
— the point of ASK is trustworthy structure, so resist making everything
optional just to make validation pass. Aim for:
- `"$schema": "https://json-schema.org/draft/2020-12/schema"`, a `title`, and
  `"type": "object"`.
- Typed properties with `description`s; use `"format": "date"` /
  `"date-time"` for dates, `"format": "email"` for emails, numeric types for
  amounts, etc.
- A `required` list covering the fields these documents dependably have.
- `"additionalProperties": false` so unexpected keys are caught — loosen this
  only with a concrete reason.

### 5. Write the YAML

One YAML file per extracted record, mirroring the inbox structure, named:

```
yaml/<mirror-path>/<base>_<name>.<type>.yaml
```

- `<base>` = the inbox file's base name (stem), e.g. `invoice`.
- `<name>` = a short instance slug you choose from distinguishing content
  (vendor + number, date, etc.), **lowercase letters and digits only**
  (`[a-z0-9]`, no spaces or punctuation).
- `<type>` = the schema type, so the type is visible in the file name.

Example: `yaml/2026/invoices/invoice_acme0042.invoice.yaml`. Multiple extractions
→ multiple files (`..._acme0042.invoice.yaml`, `..._acmecontact.contact.yaml`).
Fill the YAML with the data read from the Markdown, conforming to the schema.

**Quote dates and date-like values** (`issue_date: "2024-03-25"`). Unquoted, YAML
parses them into native date objects, which then fail a schema's
`"type": "string"` / `"format": "date"` check. Keeping them quoted strings keeps
the YAML aligned with the schema.

### 6. Validate the touched types

Validate **only the type(s) you created or updated this run** — pass each with
its own `--type`:

```sh
uv run scripts/validate.py --type <type> [--type <other-type> ...]
```

This checks every `yaml/**/*.<type>.yaml` (so it re-checks *existing* files of
those types, since a schema edit can break them) and leaves unrelated types
alone. Resolve any failure by where it comes from:
- **A file you just wrote fails** → fix the YAML; it's a fresh extraction error.
- **An existing file fails** → judge which side is wrong:
  - the file is genuinely outdated or wrong (e.g. a stale date, a missing field
    it should have) → correct the file, backtracking to its Markdown/source;
  - or your schema change was **too tight** → loosen that specific constraint
    while keeping the schema as strong as reasonable.

Re-run until validation is green for every touched type.

### 7. Migrate existing files in bulk (only if needed)

If a schema change means **many** existing YAML files need the same mechanical
edit, don't hand-edit them one by one. Write a throwaway PEP-723 uv script under
`temp/` (which is gitignored), run it to migrate the files, confirm validation
passes, then delete the script. Keep ad-hoc migration code out of `scripts/`.

### 8. Log what changed

Record the run as a **structured YAML log** so the audit trail is itself
machine-checkable. Write it mirroring the inbox path, with the current date and
time before `.log.yaml`:

```
log/<mirror-path>/<base>_<YYYYMMDD_HHMMSS>.log.yaml
```

Example: `log/2026/invoices/invoice_20260622_143005.log.yaml`. Get the timestamp
from the system clock (`date +%Y%m%d_%H%M%S`); use ISO 8601 for the `timestamp`
field inside (`2026-06-22T14:30:05`).

The log must conform to **`schemas/ask/log.json`** — an ASK-internal schema, kept
separate from the data-type schemas under `schemas/<type>.json`. Its fields:
`timestamp`, `document` (`inbox`, `markdown`), `types`, `schema_changes`
(each `type` / `action` of `created|extended|unchanged` / `path` / optional
`summary`), `yaml_written`, optional `migrations`, `validation` (`passed` plus
optional `types_validated` / `details`), and optional `notes`. Read the schema
itself if unsure.

`schemas/ask/log.json` is a **stable contract — do not edit it or migrate past
logs.** Conform to it. If a run genuinely cannot be expressed within it, write
the best-fitting log you can, then **tell the user** the log schema falls short
and suggest a concrete change (which field, why) — but leave the schema unchanged
and let the user decide.

Then validate every log:

```sh
uv run scripts/validate.py --logs
```

This checks all `log/**/*.log.yaml` against `schemas/ask/log.json`. Fix the log
you just wrote until it passes.

### 9. Report and stop

Give the user a short summary (document processed, types extracted, schema
changes, files written, validation status) and stop. Re-invoke the skill for the
next document.
