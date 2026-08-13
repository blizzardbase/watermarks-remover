#!/usr/bin/env python3
"""Unified inspect: text, images (PNG/JPEG), and containers (SVG/PDF/DOCX/ODT/HTML/MD)."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from common import emit_json, eprint, read_bytes_input  # noqa: E402
from container_meta import detect_container_format, inspect_container  # noqa: E402
from image_meta import detect_format as detect_image_format  # noqa: E402
from image_meta import inspect_image  # noqa: E402
from text_unicode import human_report, inspect_text  # noqa: E402

TEXT_EXTS = {".txt", ".text", ".md", ".markdown", ".mdx", ".html", ".htm", ".css", ".js", ".py", ".rs", ".go", ".json", ".yaml", ".yml", ".toml", ".csv"}
IMAGE_EXTS = {".png", ".jpg", ".jpeg"}
CONTAINER_EXTS = {".svg", ".pdf", ".docx", ".odt", ".html", ".htm", ".md", ".markdown", ".mdx"}


def classify(path: Path, data: bytes) -> str:
    if path.suffix.lower() in IMAGE_EXTS:
        return "image"
    if path.suffix.lower() in CONTAINER_EXTS:
        # html/md handled as container (metadata + optional text)
        return "container"
    if path.suffix.lower() in TEXT_EXTS:
        return "text"
    # magic sniff
    if detect_image_format(data) in ("png", "jpeg"):
        return "image"
    fmt = detect_container_format(path, data)
    if fmt != "unknown":
        return "container"
    return "text"


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("path", type=Path, help="File to inspect")
    p.add_argument("--json", action="store_true")
    p.add_argument("--aggressive", action="store_true", help="Text: flag confusables")
    p.add_argument(
        "--as",
        dest="force_type",
        choices=("text", "image", "container", "auto"),
        default="auto",
    )
    args = p.parse_args()

    try:
        data = read_bytes_input(args.path)
    except (OSError, ValueError) as exc:
        eprint(f"error: {exc}")
        return 2

    kind = args.force_type if args.force_type != "auto" else classify(args.path, data)

    if kind == "text":
        text = data.decode("utf-8", errors="surrogateescape")
        report = inspect_text(text, aggressive=args.aggressive)
        if args.json:
            emit_json({"kind": "text", **report.to_dict()})
        else:
            print(f"Kind: text")
            print(human_report(report))
        return 0 if report.suspicious_total == 0 else 1

    if kind == "image":
        report = inspect_image(args.path)
        if args.json:
            emit_json({"kind": "image", **report.to_dict()})
        else:
            print(f"Kind: image")
            print(f"Path: {report.path}")
            print(f"Format: {report.format}")
            print(f"C2PA: {report.has_c2pa}")
            print(f"AI metadata: {report.has_ai_metadata}")
            for f in report.findings:
                print(f"  - {f}")
        return 0 if not (report.has_c2pa or report.has_ai_metadata) else 1

    report = inspect_container(args.path)
    if args.json:
        emit_json({"kind": "container", **report.to_dict()})
    else:
        print(f"Kind: container")
        print(f"Path: {report.path}")
        print(f"Format: {report.format}")
        print(f"C2PA: {report.has_c2pa}")
        print(f"AI metadata: {report.has_ai_metadata}")
        for f in report.findings:
            print(f"  - {f}")
    return 0 if not (report.has_c2pa or report.has_ai_metadata) else 1


if __name__ == "__main__":
    raise SystemExit(main())
