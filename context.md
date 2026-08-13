# Current context

## Source

This repository is the hardened Blizzardbase fork of
`guillaumemeyer/watermarks-remover`. The reviewed upstream baseline is
`a443019bc81c3616e1eb83bf7d8ab1911c526ddf`.

## Current behavior

1. Runtime scripts use the Python standard library and make no network or
   external executable call.
2. Default Unicode cleaning preserves joiners, direction controls, variation
   selectors, tags, special spaces, and lookalike letters.
3. Image and document cleanup is targeted by default.
4. DOCX custom XML is preserved.
5. PDF is inspection only.
6. Rewrite support creates an offline prompt only.
7. Input is bounded. Symbolic links are refused. Output is atomic and refuses
   unverified replacement. Backups do not overwrite older backups.

## Verification contract

The complete tests and offline smoke target must pass. Static review must find
no network client, credential handling, installer path, subprocess execution,
or mutable continuous integration action in the installed skill.

## Known limits

The skill cannot detect or remove statistical text marks, pixel marks, audio
marks, video marks, soft binding, private vendor signals, or model training
backdoors. A clean report does not prove origin or authorship.
