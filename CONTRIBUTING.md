# Contributing

This fork accepts focused safety, correctness, documentation, and format
support changes.

## Requirements

1. Python 3.10 or newer.
2. No runtime package dependency.
3. A feature branch and pull request.
4. Passing tests and offline smoke checks.
5. Review by `@blizzardbase` before merge.

Set up the hash locked development environment:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.lock
python3 -m pytest -q
make smoke
```

## Repository layout

| Path | Purpose |
| --- | --- |
| `skills/remove-ai-marks/SKILL.md` | Agent workflow and safety boundary |
| `skills/remove-ai-marks/scripts/` | Local inspection and cleaning scripts |
| `skills/remove-ai-marks/references/` | Use boundary and supported behavior |
| `tests/` | Safety and correctness tests |
| `context.md` | Current implementation contract |

## Change rules

1. Preserve the invariants in `AGENTS.md` and `CLAUDE.md`.
2. Add or update focused tests.
3. Update every affected behavior document in the same pull request.
4. Keep default cleaning conservative.
5. Do not add network calls, credentials, installers, subprocess execution,
   external detectors, or runtime packages.
6. Do not commit private documents, credentials, or large binary fixtures.
7. Inspect the full diff and run `git diff --check` before push.

Use the bug and feature issue templates for reports that do not yet have a
code change.
