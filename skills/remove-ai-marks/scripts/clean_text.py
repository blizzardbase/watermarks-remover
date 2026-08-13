#!/usr/bin/env python3
"""Strip invisible Unicode / normalize space homoglyphs (Layer A)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import (  # noqa: E402
    atomic_write_text,
    cleaned_path,
    create_backup,
    eprint,
    read_text_input,
    write_text_output,
)
from text_unicode import clean_text  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", nargs="?", default="-", help="Input text file, or - for stdin")
    p.add_argument("-o", "--output", help="Output path (default: stdout or *.cleaned.*)")
    p.add_argument("--nfkc", action="store_true", help="Apply Unicode NFKC after scrub")
    p.add_argument(
        "--aggressive-homoglyphs",
        action="store_true",
        help="Map Cyrillic/fullwidth Latin confusables to ASCII Latin",
    )
    p.add_argument(
        "--normalize-spaces",
        action="store_true",
        help="Rewrite special spaces to U+0020",
    )
    p.add_argument(
        "--aggressive-unicode",
        action="store_true",
        help="Also remove joiners, direction controls, tags, and variation selectors",
    )
    p.add_argument("--stats", action="store_true", help="Print stats JSON to stderr")
    p.add_argument(
        "--in-place",
        action="store_true",
        help="Overwrite input file (creates .bak backup)",
    )
    args = p.parse_args()

    if args.in_place and args.path in (None, "-"):
        eprint("--in-place requires a file path")
        return 2

    try:
        text = read_text_input(args.path)
    except (OSError, ValueError) as exc:
        eprint(f"error: {exc}")
        return 2

    cleaned, stats = clean_text(
        text,
        nfkc=args.nfkc,
        aggressive_homoglyphs=args.aggressive_homoglyphs,
        normalize_spaces=args.normalize_spaces,
        aggressive_unicode=args.aggressive_unicode,
    )

    out = args.output
    expected_existing = None
    if args.in_place:
        src = Path(args.path)
        try:
            bak, expected_existing = create_backup(src)
        except (OSError, ValueError) as exc:
            eprint(f"error: {exc}")
            return 2
        eprint(f"backup={bak}")
        out = str(src)
    elif out is None and args.path not in (None, "-"):
        out = str(cleaned_path(Path(args.path)))

    try:
        if expected_existing is not None:
            atomic_write_text(cleaned, out, expected_existing=expected_existing)
        else:
            write_text_output(cleaned, out)
    except (OSError, ValueError) as exc:
        eprint(f"error: {exc}")
        return 2

    if args.stats:
        eprint(json.dumps(stats, indent=2, ensure_ascii=False))
    else:
        eprint(
            f"removed={stats['removed_count']} replaced={stats['replaced_count']} "
            f"len {stats['input_length']}->{stats['output_length']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
