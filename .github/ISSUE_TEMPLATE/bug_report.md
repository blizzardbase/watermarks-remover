---
name: Bug report
about: Report a defect in watermarks-remover (text/image cleaning, skill docs, or scripts)
title: "[bug] "
labels: bug
assignees: ""
---

## What happened

A clear description of the unexpected behaviour.

## What you expected

What should have happened instead.

## Steps to reproduce

1.
2.
3.

## Environment

- OS and arch:
- Python version (`python3 --version`):
- Exact commit revision:
- How you run the skill (Codex skill path or repository scripts):

## Input type

- [ ] Text (paste / `.txt` / `.md` / other)
- [ ] Image (PNG / JPEG)
- [ ] Document (SVG / PDF / DOCX / ODT / HTML / Markdown)
- Layer involved: Unicode / image metadata / document metadata / offline rewrite prompt

## Diagnostics

Paste relevant CLI output (redact private content):

```bash
SCRIPTS=skills/remove-ai-marks/scripts
python3 "$SCRIPTS/inspect_file.py" path
# or:
python3 "$SCRIPTS/inspect_text.py" path/or/-
python3 "$SCRIPTS/inspect_image.py" path.png
```

## Extra context

Sample files (if shareable), screenshots, or related issues. Do not paste secrets, private documents, or material you do not own.
