# Watermarks Remover

This is the hardened Blizzardbase fork of
[`guillaumemeyer/watermarks-remover`](https://github.com/guillaumemeyer/watermarks-remover).
It inspects and conservatively cleans invisible Unicode and AI provenance
metadata from content that you own or are authorized to edit.

The installed skill uses the Python standard library. It does not invoke a
network client, model API, package installer, Docker image, or external
executable. It never claims that a result is human written or undetectable.

## Supported operations

| Format | Inspection | Default cleaning |
| --- | --- | --- |
| Text and source files | Invisible and format Unicode | Soft hyphen, zero width space, and byte order mark |
| Markdown | Unicode and selected frontmatter | High confidence AI provenance keys |
| HTML | Unicode and selected metadata | Matching meta fields, JSON LD fields, and `data-ai*` attributes |
| PNG | C2PA and AI metadata chunks | Only matching chunks |
| JPEG | C2PA and AI metadata segments | Only matching segments |
| SVG | AI provenance inside metadata blocks | Only matching metadata blocks and comments |
| DOCX | AI provenance in property and custom XML parts | Matching document property values only |
| ODT | AI provenance in metadata parts | Matching generator and creator fields only |
| PDF | Byte and XMP inspection | Inspection only |

DOCX custom XML is always preserved. Unrelated image metadata is preserved by
default. PDF rewriting is disabled because byte deletion can corrupt cross
references.

## Requirements

Runtime use requires Python 3.10 or newer and no package installation.

Development uses a hash locked test environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
make test
make smoke
```

## Skill installation

Install only from the Blizzardbase fork and a full reviewed commit revision.
Do not install from a branch or tag that can move. The Codex skill path is
`skills/remove-ai-marks`.

Restart Codex after installation so it discovers the skill.

## Commands

Set the script path for a repository checkout or installed skill:

```bash
SCRIPTS="skills/remove-ai-marks/scripts"
```

Inspect before making a change:

```bash
python3 "$SCRIPTS/inspect_file.py" document.md --json
python3 "$SCRIPTS/inspect_text.py" notes.txt --json
python3 "$SCRIPTS/inspect_image.py" image.png --json
```

Write a separate output:

```bash
python3 "$SCRIPTS/clean_file.py" document.md -o document.cleaned.md
python3 "$SCRIPTS/clean_text.py" notes.txt -o notes.cleaned.txt --stats
python3 "$SCRIPTS/clean_image.py" image.png -o image.cleaned.png --json
```

The scripts reject symbolic link inputs and outputs. Input is limited to 256
MiB by default and 512 MiB at the hard maximum. A lower local limit can be set
with `WATERMARKS_MAX_INPUT_BYTES`.

### Explicit broad changes

These options can alter legitimate content or metadata. Use them only when the
caller explicitly requests the wider change.

```bash
python3 "$SCRIPTS/clean_text.py" notes.txt --aggressive-unicode
python3 "$SCRIPTS/clean_text.py" notes.txt --normalize-spaces
python3 "$SCRIPTS/clean_text.py" notes.txt --aggressive-homoglyphs
python3 "$SCRIPTS/clean_text.py" notes.txt --nfkc
python3 "$SCRIPTS/clean_image.py" image.png --strip-all-metadata
```

`--in-place` creates a new exclusive backup. An existing backup is never
overwritten. Normal use should prefer a separate output.

### Offline rewrite prompt

`rewrite_text.py` creates a prompt only. It never calls a model or reads an API
key.

```bash
python3 "$SCRIPTS/rewrite_text.py" draft.md -o rewrite.prompt.txt
```

Rewriting changes wording and can change meaning. It should happen only when
the caller asks for it. Code mode instructs the model to preserve identifiers
and executable behavior.

## Verification and limits

Always inspect the output and report the exact actions. A clean inspection only
means that the patterns implemented here were not found. It does not prove
origin or authorship.

This project does not detect or remove statistical text marks, pixel marks,
audio marks, video marks, soft binding, private vendor signals, or model
training backdoors. It does not include reverse engineered detectors.

Do not use it to evade a disclosure duty, commit academic fraud, or remove
provenance from content you may not alter. See
[`references/ethics.md`](skills/remove-ai-marks/references/ethics.md).

## Security design

1. File input is bounded before full processing.
2. Symbolic link input and output are refused.
3. New output uses exclusive creation. In place output uses atomic verified
   replacement. Existing destinations are refused outside in place mode.
4. Backups use exclusive names and never replace an earlier backup.
5. Zip based formats have decompressed size and member count caps.
6. Image and document cleaning is targeted by default.
7. Continuous integration actions use immutable commit revisions.
8. Test packages are exact and hash locked.

## License and lineage

The project remains under the MIT license. The fork preserves upstream history
and records hardening changes through reviewed pull requests.
