# Claude context

## Purpose

Maintain the hardened Blizzardbase fork of `watermarks-remover`. The installed
skill inspects and conservatively cleans invisible Unicode and AI provenance
metadata from content the user owns or may edit.

## Safety invariants

1. Keep runtime operation local and based on the Python standard library.
2. Do not add network calls, model APIs, credentials, package installers,
   external executables, Docker paths, or reverse engineered detectors.
3. Preserve legitimate language shaping and unrelated metadata by default.
4. Keep PDF inspection only unless a separately audited implementation can
   safely rewrite complete PDF structures.
5. Preserve DOCX custom XML and document content.
6. Bound every input, refuse symbolic links and unverified replacement, use
   atomic output, and never overwrite an older backup.
7. Never claim human authorship, detector evasion, or complete provenance
   removal.
8. Keep `README.md`, `SKILL.md`, `context.md`, `AGENTS.md`, and this file aligned.

## Verification

```bash
python3 -m pytest -q
make smoke
git diff --check
```

Continuous integration actions must use immutable commit revisions. Test
packages must remain exact and hash locked.

## Git workflow

Use a feature branch, inspect the full diff and secret scan before every push,
open a pull request, resolve actionable review, merge only when checks pass,
then sync local `main`.
