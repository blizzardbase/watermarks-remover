# Harden remove ai marks

## Purpose

Create an auditable Blizzardbase fork of `guillaumemeyer/watermarks-remover` that is safe to install as a Codex skill. The installed skill must remain local by default, preserve legitimate document content, avoid vulnerable optional dependencies, and be pinned to one reviewed merge commit.

## Baseline evidence

| Evidence | Baseline |
| --- | --- |
| Upstream revision | `a443019bc81c3616e1eb83bf7d8ab1911c526ddf` |
| Upstream age | Created 11 August 2026 |
| Upstream tests | 45 passed locally |
| Upstream CI | Green at the baseline revision |
| Runtime dependencies | Python standard library for the core path |
| Optional dependency risk | `Pillow==10.4.0` returned 17 unique OSV findings, including 13 high severity findings, on 13 August 2026 |
| Confirmed data integrity defects | Default Unicode cleaning altered emoji, Persian shaping, and narrow nonbreaking spaces. DOCX cleaning deleted all `customXml` parts. Markdown cleaning could leave nested YAML without its parent key. |

## Scope

1. Remove the optional reverse SynthID installer, scorer, Docker build, dependency manifest, and automatic execution path.
2. Remove direct HTTP model calls and API key handling from the rewrite helper. Keep offline prompt generation only.
3. Make Unicode cleaning conservative by default. Preserve joiners, variation selectors, bidirectional controls, tag characters, and special spaces unless the caller explicitly selects aggressive cleaning.
4. Preserve every DOCX `customXml` part and fix nested Markdown frontmatter handling.
5. Apply bounded input sizes to every entry point, reject symbolic link inputs and outputs, keep backups without overwriting an older backup, and use atomic output replacement.
6. Pin continuous integration actions to immutable revisions and add focused safety tests.
7. Add the standard repository handoff files and update all affected documentation in the same pull request.

## Exclusions

1. No pixel, audio, or video watermark detection or removal.
2. No external model call, file upload, paid request, or credential configuration.
3. No installation of `exiftool`, `c2patool`, Docker images, Python packages, or reverse SynthID.
4. No attempt to prove that output will evade a private vendor detector.
5. No change to upstream history and no force push.

## File ownership

The root Codex agent owns every repository change, all Git state, the pull request, the merge, the exact commit installation, and the Notion record. No subagent or parallel worktree is authorized for this task.

## Ordered milestones and acceptance criteria

### Milestone 1: Remove external execution surfaces

Acceptance criteria:

1. The installed skill contains no reverse SynthID setup or scorer code.
2. Python source contains no HTTP client import and no API key argument or environment lookup.
3. The rewrite helper emits a prompt without making a model call.

### Milestone 2: Make cleaning conservative and bounded

Acceptance criteria:

1. Family emoji, emoji presentation selectors, Persian joiners, and narrow nonbreaking spaces remain unchanged with default settings.
2. Aggressive Unicode cleaning is explicit and test covered.
3. Legitimate DOCX `customXml` survives cleaning.
4. A dropped Markdown key cannot leave nested child lines behind.
5. All command entry points reject oversized or symbolic link inputs before reading them.
6. Output replacement is atomic and refuses a symbolic link destination.

### Milestone 3: Ship documentation and immutable automation

Acceptance criteria:

1. `README.md`, `SKILL.md`, `context.md`, `CLAUDE.md`, `AGENTS.md`, `.gitignore`, and `.env.example` describe the same behavior.
2. Continuous integration actions use full commit revisions.
3. Core operation still requires no runtime package installation.

### Milestone 4: Verify and publish

Acceptance criteria:

1. The complete test suite passes.
2. Offline smoke checks pass with every rewrite related environment variable removed.
3. Static searches find no network client, API key, reverse SynthID, credential, or installer path in the installed skill.
4. The full branch diff contains no secret, personal data, or unrelated change.
5. CodeRabbit has no unresolved actionable comment and required checks are green.
6. The pull request is merged and local `main` matches `origin/main`.

### Milestone 5: Install and register

Acceptance criteria:

1. The Codex skill is installed from the exact reviewed merge commit in `blizzardbase/watermarks-remover`.
2. Installed file hashes match the same files at that commit.
3. A clean offline smoke check succeeds from the installed path.
4. The Installed Tools Notion row records the source, audited revision, install method, limitations, and review date.

## Verification commands and expected results

| Command | Expected result |
| --- | --- |
| `python3 -m pytest -q` | Every test passes |
| `python3 skills/remove-ai-marks/scripts/rewrite_text.py tests/fixtures/sample_watermarked.txt` | Prints an offline prompt and performs no network call |
| `python3 skills/remove-ai-marks/scripts/clean_text.py tests/fixtures/sample_watermarked.txt --stats` | Writes a separate cleaned file and reports deterministic counts |
| `python3 skills/remove-ai-marks/scripts/inspect_file.py tests/fixtures/sample_ai.md --json` | Produces local JSON findings without a model or network call |
| `rg -n -e urllib -e requests -e httpx -e API_KEY -e 'reverse\.SynthID' -e setup_synthid skills/remove-ai-marks` | No executable network, credential, or reverse SynthID path remains |
| `git diff --check` | No whitespace error |
| `git status --short` | Only intended branch changes before commit, then clean after commit |

## Rollback

Before merge, close the pull request and delete the feature branch. After merge, revert the merge through a new pull request. If installation verification fails, move the newly installed skill directory to Trash and leave the Installed Tools row marked as needing audit. No previous `remove-ai-marks` installation exists to restore.

## Authority matrix

| Action | Authority |
| --- | --- |
| Edit, test, commit, push, open and update the pull request | Approved |
| Resolve CodeRabbit comments and merge when green | Approved |
| Install the exact reviewed merge commit | Approved |
| Add or update the Installed Tools Notion row | Approved |
| Live model call, file upload, spending, force push, destructive unrelated action | Stop and request approval |

## Progress

1. 13 August 2026: Audited upstream revision and created the `blizzardbase/watermarks-remover` fork.
2. 13 August 2026: Created branch `codex/harden-remove-ai-marks` and recorded this plan.
3. 13 August 2026: Removed external execution and dependency paths. Added conservative defaults, bounded input, atomic output, exclusive backups, archive limits, and targeted container cleaning.
4. 13 August 2026: Added repository context files, updated behavior documentation, pinned continuous integration actions, and added a hash locked development manifest.
5. 13 August 2026: Completed 45 focused tests, offline smoke checks, syntax parsing, static execution surface searches, ignore checks, and whitespace verification locally.
6. 13 August 2026: Opened pull request 1. Continuous integration passed. CodeRabbit found 11 actionable issues plus six lower priority notes. All valid findings were addressed, including credential persistence, read races, output races, nested JSON safety, archive bounds, snapshot reuse, residual status handling, unknown binary rejection, and preserved DOCX signal reporting. The focused suite now contains 51 passing tests.
7. 13 August 2026: CodeRabbit rechecked the fixes and found one additional major reporting issue. DOCX inspection now reports preserved custom XML signals honestly while cleanup status excludes only those intentionally preserved parts. Unexpected residual metadata still fails cleanup status.
8. 13 August 2026: Continuous integration and CodeRabbit completed without an unresolved actionable finding. Pull request 1 was squash merged as `dc31f434b93776a431890bcf7659a002fb330178`, then local `main` was synchronized with `origin/main`.
9. 13 August 2026: Installed the skill from the exact merge revision into `/Users/itshv/.codex/skills/remove-ai-marks`. All 15 installed file hashes matched the Git objects at that revision. The installed offline rewrite, cleaning, and inspection smoke checks passed.
10. 13 August 2026: Reconciled the personal Installed Tools register and added the [watermarks remover record](https://app.notion.com/p/3bb7ed8960258120a007cf780ceb4118). The record contains the source, install method, audited revision, limitations, review date, and security findings.

## Discoveries

1. The latest upstream release predates two security changes that exist only on `main`.
2. The core scripts are readable Python with no compiled payload or installation hook.
3. Generic values such as an article title containing a vendor name produced false positives when the whole frontmatter or HTML tag was searched. Inspection and cleaning now require a provenance key plus a matching value, or a high confidence key.
4. An APP11 JPEG segment is not provenance by itself. The hardened path requires a C2PA marker before classifying or removing it.
5. A symbolic link check alone has a time of check race. In place writes now bind replacement to the original device and inode captured while creating the backup.

## Decision log

1. Install only from an exact Blizzardbase merge commit.
2. Remove the optional scorer instead of attempting to repair its large external dependency surface in this change.
3. Keep rewrite support offline because Harish already has a separate prose humanizer capability.
4. Refuse existing output destinations unless the caller selected in place mode and the destination identity still matches the backed up file.
5. Preserve generic SVG metadata, image EXIF and comments, HTML generator fields, ODT generator fields, and DOCX custom XML unless a high confidence AI provenance marker is present.
6. Treat intentionally preserved DOCX custom XML signals as reported limitations instead of failed cleanup, while unexpected residual signals still fail.
7. Fail closed on operating systems without descriptor level no follow support.

## Push inspection log

1. Before commit `23785297cdac067681f2ab0a206c6a0051a8fb32`, inspected the complete diff, secret patterns, ignored secret filenames, static execution surfaces, and unrelated changes. Pushed the initial hardening branch.
2. Before commit `1418c25832f6391011a02f7a68b01adf8bde8b10`, inspected the review fix diff and reran 50 tests, offline smoke checks, syntax parsing, static execution surface searches, secret searches, and whitespace verification. Pushed the reviewed fixes.
3. Before commit `8eb38fa82cbf084beb22c104300827fc04990527`, inspected the DOCX reporting fix and reran 51 tests, offline smoke checks, secret searches, and whitespace verification. Pushed the second review fix.
4. Before the final reviewed push, inspected the documentation fixes, reran whitespace and secret checks, and confirmed that continuous integration and CodeRabbit were green. Pull request 1 was squash merged as `dc31f434b93776a431890bcf7659a002fb330178`.
5. Before the final documentation push, inspected the complete diff against `origin/main`, reran whitespace and secret checks, and confirmed that the only change records the merge, installation verification, and Installed Tools outcome.

## Outcomes

Complete. [Pull request 1](https://github.com/blizzardbase/watermarks-remover/pull/1) was reviewed, passed every required check, and was squash merged as `dc31f434b93776a431890bcf7659a002fb330178`. The exact revision is installed at `/Users/itshv/.codex/skills/remove-ai-marks`; all 15 installed files match their Git object hashes and the offline smoke checks pass. The [Installed Tools record](https://app.notion.com/p/3bb7ed8960258120a007cf780ceb4118) records the source, exact pin, install method, review evidence, and limitations.

The installed skill remains deliberately conservative. PDF support is inspection only. Pixel, audio, video, and statistical text marks remain outside scope. Broad Unicode and metadata removal requires explicit options.
