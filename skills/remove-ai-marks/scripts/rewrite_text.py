#!/usr/bin/env python3
"""Build an offline rewrite prompt without making a model or network call."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import eprint, read_text_input, write_text_output  # noqa: E402


PROMPTS = {
    "paraphrase": (
        "Rewrite the following text with substantially different wording and syntax. "
        "Change clause order, connectors, transition words, and sentence boundaries. "
        "Preserve every fact, number, name, and technical identifier. Do not add or "
        "remove claims. Output only the rewritten text.\n\n---\n{TEXT}"
    ),
    "humanize": (
        "Rewrite the following text in plain and varied human prose. Preserve every "
        "fact, number, name, and technical identifier. Do not add or remove claims. "
        "Output only the rewritten text.\n\n---\n{TEXT}"
    ),
    "code": (
        "Rewrite only comments, docstrings, and other natural language in this code. "
        "Do not rename identifiers and do not change executable behavior. Output only "
        "the rewritten code.\n\n---\n{TEXT}"
    ),
}


def build_prompt(
    strength: str,
    text: str,
    *,
    lang: str,
    original_lang: str,
) -> str:
    if strength in PROMPTS:
        return PROMPTS[strength].format(TEXT=text)
    if strength == "backtranslate":
        return (
            f"Translate the text to {lang}, then translate that result back to "
            f"{original_lang}. Preserve every fact, number, and name. Output only "
            f"the final {original_lang} text.\n\n---\n{text}"
        )
    if strength == "structural":
        return (
            "Extract an outline of every claim, then write a complete document from "
            "that outline in natural prose without omitting a claim. Output only the "
            f"final document.\n\n---\n{text}"
        )
    raise ValueError(f"unknown strength: {strength}")


def rewrite_prompt(
    text: str,
    *,
    strength: str,
    lang: str,
    original_lang: str,
) -> tuple[str, dict]:
    prompt = build_prompt(
        strength,
        text,
        lang=lang,
        original_lang=original_lang,
    )
    return prompt, {
        "mode": "offline_prompt",
        "strength": strength,
        "input_chars": len(text),
        "prompt_chars": len(prompt),
        "network_calls": 0,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", nargs="?", default="-", help="Input text file, or standard input")
    parser.add_argument("-o", "--output", help="Output path, or standard output by default")
    parser.add_argument(
        "--strength",
        choices=("paraphrase", "backtranslate", "structural", "humanize", "code"),
        default="paraphrase",
    )
    parser.add_argument("--lang", default="French", help="Pivot language")
    parser.add_argument("--original-lang", default="English")
    parser.add_argument("--json-stats", action="store_true", help="Write JSON statistics to standard error")
    args = parser.parse_args()

    try:
        text = read_text_input(args.path)
        prompt, info = rewrite_prompt(
            text,
            strength=args.strength,
            lang=args.lang,
            original_lang=args.original_lang,
        )
        write_text_output(prompt, args.output or "-")
    except (OSError, ValueError) as exc:
        eprint(f"error: {exc}")
        return 2

    if args.json_stats:
        eprint(json.dumps(info, indent=2, ensure_ascii=False))
    else:
        eprint(
            f"mode={info['mode']} strength={info['strength']} "
            f"chars={info['input_chars']} prompt_chars={info['prompt_chars']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
