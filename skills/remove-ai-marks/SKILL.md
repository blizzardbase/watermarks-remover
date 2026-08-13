---
name: remove-ai-marks
description: >
  Inspect and conservatively clean invisible Unicode or AI provenance metadata
  from text, PNG, JPEG, SVG, DOCX, ODT, HTML, Markdown, and PDF files. Use when
  the user asks to inspect or remove AI metadata, C2PA data, Content Credentials,
  or suspicious invisible Unicode from content they own or may edit.
---

# Remove AI marks

Use this skill only for content the user owns or is authorized to alter. Do not
help evade a disclosure requirement, commit academic fraud, or claim that a
clean result proves human authorship.

The scripts are local and use the Python standard library. They make no network
call, model call, package installation, or external executable call.

Resolve `SCRIPTS` to the absolute `scripts` directory inside this skill.

## Required workflow

1. Confirm that the requested file or text is within the user authorized scope.
2. Inspect first and summarize the exact findings.
3. Use conservative defaults and write a separate output.
4. Use a broad option only when the user explicitly requests that wider change.
5. Inspect the output and report actions, residual findings, and limitations.

Do not automatically clean every file in a directory. Resolve the exact files
in scope before processing them.

## Inspection

```bash
python3 "$SCRIPTS/inspect_file.py" FILE --json
python3 "$SCRIPTS/inspect_text.py" FILE --json
python3 "$SCRIPTS/inspect_image.py" FILE --json
```

An inspection exit status of `1` means that a matching signal was found. It is
not a script failure.

## Conservative cleaning

```bash
python3 "$SCRIPTS/clean_file.py" INPUT -o OUTPUT
python3 "$SCRIPTS/clean_text.py" INPUT -o OUTPUT --stats
python3 "$SCRIPTS/clean_image.py" INPUT -o OUTPUT --json
```

Default text cleaning removes only soft hyphen, zero width space, and byte
order mark. It preserves joiners, direction controls, variation selectors,
tag characters, special spaces, and lookalike letters.

Default image cleaning removes only segments that contain a matching AI or
C2PA marker. It preserves unrelated EXIF, comments, and text metadata.

DOCX cleaning preserves all custom XML and document content. Markdown cleaning
removes nested children when their parent provenance key is removed. HTML JSON
LD cleaning removes only matching fields. PDF is inspection only.

## Broad options

The following options may change legitimate language shaping, presentation,
spacing, identifiers, or metadata. Require an explicit user request.

```bash
python3 "$SCRIPTS/clean_text.py" INPUT --aggressive-unicode
python3 "$SCRIPTS/clean_text.py" INPUT --normalize-spaces
python3 "$SCRIPTS/clean_text.py" INPUT --aggressive-homoglyphs
python3 "$SCRIPTS/clean_text.py" INPUT --nfkc
python3 "$SCRIPTS/clean_image.py" INPUT --strip-all-metadata
```

Use `--in-place` only when the user requests replacement. It creates a new
backup without overwriting an older backup.

## Rewrite requests

Rewriting is never automatic. If the user explicitly asks to rewrite text,
`rewrite_text.py` can create an offline prompt:

```bash
python3 "$SCRIPTS/rewrite_text.py" INPUT -o PROMPT
```

The helper does not call a model. Use the current assistant for the rewrite,
then check every fact, number, name, and identifier against the source. Code
mode changes comments and docstrings only and instructs the model not to rename
identifiers or alter behavior.

## Reporting

State:

1. The input and output paths.
2. The exact fields, chunks, segments, or codepoints removed.
3. Whether any matching signal remains.
4. Which broad options were used.
5. That this tool cannot prove origin, authorship, or undetectability.

Read `references/removal-matrix.md` for supported formats and
`references/ethics.md` for the use boundary.
