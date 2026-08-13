# Remove AI marks installation verification

## Scope

Verified on 13 August 2026 after [pull request 1](https://github.com/blizzardbase/watermarks-remover/pull/1) was squash merged.

Upstream baseline: `a443019bc81c3616e1eb83bf7d8ab1911c526ddf`

Audited and installed revision: `dc31f434b93776a431890bcf7659a002fb330178`

At installation time, local `main` and `origin/main` both resolved to the installed revision.

Installed location: `$CODEX_HOME/skills/remove-ai-marks`

The official Codex skill installer copied the `skills/remove-ai-marks` directory from the exact audited revision. It materialized regular files with mode `0644`. The skill invokes every Python entry point through `python3`, so executable file mode is not required.

## Content integrity

Each line records the repository relative file, expected Git blob, installed content hash, and result. `git hash-object` produced every installed content hash.

```text
SKILL.md                              ba9745b5a9d4243a36ddd4093d1a2329cf5ce302  ba9745b5a9d4243a36ddd4093d1a2329cf5ce302  match
references/ethics.md                  befe3286c1461fbbe17bbcb611186d3d4304483b  befe3286c1461fbbe17bbcb611186d3d4304483b  match
references/mark-classes.md            ca7df7c73791ec739a26a3ddafe2e47be98f5765  ca7df7c73791ec739a26a3ddafe2e47be98f5765  match
references/removal-matrix.md          dcae6f79a094414811b0914bcac9bff64664d271  dcae6f79a094414811b0914bcac9bff64664d271  match
scripts/clean_file.py                 b6a71b82828f8899791efb02e7aef9d882ed6ee1  b6a71b82828f8899791efb02e7aef9d882ed6ee1  match
scripts/clean_image.py                0c86a8f45562a5e3497193109362c2429c9de4e3  0c86a8f45562a5e3497193109362c2429c9de4e3  match
scripts/clean_text.py                 1e5d91920ba839f18bb122b3535aabb1c3de9f6f  1e5d91920ba839f18bb122b3535aabb1c3de9f6f  match
scripts/common.py                     df90d8637c90d52aa022b1e07e57471f3f297570  df90d8637c90d52aa022b1e07e57471f3f297570  match
scripts/container_meta.py             22706d9f15b3ed1752fe1a22a2cbfe0702b81475  22706d9f15b3ed1752fe1a22a2cbfe0702b81475  match
scripts/image_meta.py                 b9b53bdc9a4bc584138a1269ef61309b54e53bd5  b9b53bdc9a4bc584138a1269ef61309b54e53bd5  match
scripts/inspect_file.py               b2427e444f05e4aea290b76976e3c5e362dddee7  b2427e444f05e4aea290b76976e3c5e362dddee7  match
scripts/inspect_image.py              3da1a167df741d1b662c0cf1e2ebafda869536e5  3da1a167df741d1b662c0cf1e2ebafda869536e5  match
scripts/inspect_text.py               940b38ff7309026fb24854d6b4cf86ef9c89bb27  940b38ff7309026fb24854d6b4cf86ef9c89bb27  match
scripts/rewrite_text.py               8eb7a27985bf27ade468929213de30c314fa8c1c  8eb7a27985bf27ade468929213de30c314fa8c1c  match
scripts/text_unicode.py               5fc7ca4ffa9746bb5b316b7f696333565fcc142b  5fc7ca4ffa9746bb5b316b7f696333565fcc142b  match
```

Result: 15 expected files, 15 installed files, 15 matching content hashes, and no extra file.

## Offline smoke verification

The commands below ran with Python bytecode writes disabled and the only supported runtime environment override removed.

```sh
PYTHONDONTWRITEBYTECODE=1 env -u WATERMARKS_MAX_INPUT_BYTES python3 "$CODEX_HOME/skills/remove-ai-marks/scripts/rewrite_text.py" tests/fixtures/sample_watermarked.txt --json-stats >/dev/null
PYTHONDONTWRITEBYTECODE=1 env -u WATERMARKS_MAX_INPUT_BYTES python3 "$CODEX_HOME/skills/remove-ai-marks/scripts/clean_text.py" tests/fixtures/sample_watermarked.txt -o - --stats >/dev/null
PYTHONDONTWRITEBYTECODE=1 env -u WATERMARKS_MAX_INPUT_BYTES python3 "$CODEX_HOME/skills/remove-ai-marks/scripts/inspect_file.py" tests/fixtures/sample_ai.md --json >/dev/null
```

The rewrite command exited `0`, reported `network_calls: 0`, read 42 characters, and generated an offline prompt containing 321 characters.

The cleaning command exited `0` and removed two characters named `ZERO WIDTH SPACE` plus one soft hyphen. It preserved the safe Unicode profile and performed no replacement.

The inspection command exited `1` as expected because the fixture contains an AI provenance signal.

## Registration

The personal Installed Tools register contains the [watermarks remover record](https://app.notion.com/p/3bb7ed8960258120a007cf780ceb4118). It records the audited source, exact revision, install method, capabilities, limitations, security findings, and review date.

## Deliberate limits

PDF support is inspection only. Pixel, audio, video, and statistical text marks are outside scope. Broad Unicode and metadata removal require explicit options.
