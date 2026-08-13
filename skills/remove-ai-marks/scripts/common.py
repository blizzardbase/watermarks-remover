#!/usr/bin/env python3
"""Shared bounded input and atomic output helpers."""

from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any


DEFAULT_MAX_INPUT_BYTES = 256 * 1024 * 1024
HARD_MAX_INPUT_BYTES = 512 * 1024 * 1024


def eprint(*args: object) -> None:
    print(*args, file=sys.stderr)


def input_limit_bytes() -> int:
    raw = os.environ.get("WATERMARKS_MAX_INPUT_BYTES")
    if not raw:
        return DEFAULT_MAX_INPUT_BYTES
    try:
        requested = int(raw)
    except ValueError as exc:
        raise ValueError("WATERMARKS_MAX_INPUT_BYTES must be an integer") from exc
    if requested <= 0:
        raise ValueError("WATERMARKS_MAX_INPUT_BYTES must be positive")
    return min(requested, HARD_MAX_INPUT_BYTES)


def _read_regular_file(path: Path) -> bytes:
    if path.is_symlink():
        raise ValueError(f"refusing symbolic link input: {path}")

    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags)
    except OSError as exc:
        raise ValueError(f"cannot open input: {path}: {exc}") from exc

    limit = input_limit_bytes()
    try:
        info = os.fstat(fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"not a regular file: {path}")
        if info.st_size > limit:
            raise ValueError(f"refusing input larger than {limit} bytes: {path}")

        data = bytearray()
        while len(data) <= limit:
            chunk = os.read(fd, min(1024 * 1024, limit + 1 - len(data)))
            if not chunk:
                break
            data.extend(chunk)
        if len(data) > limit:
            raise ValueError(f"refusing input larger than {limit} bytes: {path}")
        return bytes(data)
    finally:
        os.close(fd)


def read_bytes_input(path: str | Path) -> bytes:
    return _read_regular_file(Path(path))


def read_text_input(path: str | None) -> str:
    if path is None or path == "-":
        limit = input_limit_bytes()
        binary = getattr(sys.stdin, "buffer", None)
        if binary is not None:
            raw = binary.read(limit + 1)
            if len(raw) > limit:
                raise ValueError(f"refusing standard input larger than {limit} bytes")
            return raw.decode("utf-8", errors="surrogateescape")

        text = sys.stdin.read(limit + 1)
        if len(text.encode("utf-8", errors="surrogateescape")) > limit:
            raise ValueError(f"refusing standard input larger than {limit} bytes")
        return text
    return read_bytes_input(path).decode("utf-8", errors="surrogateescape")


def atomic_write_bytes(
    data: bytes,
    path: str | Path,
    *,
    expected_existing: tuple[int, int] | None = None,
) -> None:
    out = Path(path)
    if out.is_symlink():
        raise ValueError(f"refusing symbolic link output: {out}")
    out.parent.mkdir(parents=True, exist_ok=True)

    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{out.name}.",
        suffix=".tmp",
        dir=out.parent,
    )
    temporary = Path(temporary_name)
    try:
        with os.fdopen(fd, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        if out.is_symlink():
            raise ValueError(f"refusing symbolic link output: {out}")
        if out.exists():
            current = out.stat(follow_symlinks=False)
            if not stat.S_ISREG(current.st_mode):
                raise ValueError(f"refusing nonregular output: {out}")
        if expected_existing is not None:
            try:
                current = out.stat(follow_symlinks=False)
            except FileNotFoundError as exc:
                raise ValueError(f"output changed before replacement: {out}") from exc
            if not stat.S_ISREG(current.st_mode) or (
                current.st_dev,
                current.st_ino,
            ) != expected_existing:
                raise ValueError(f"output changed before replacement: {out}")
        elif out.exists():
            raise ValueError(
                f"refusing to replace existing output without in place mode: {out}"
            )
        os.replace(temporary, out)
    finally:
        if temporary.exists():
            temporary.unlink()


def atomic_write_text(
    text: str,
    path: str | Path,
    *,
    expected_existing: tuple[int, int] | None = None,
) -> None:
    atomic_write_bytes(
        text.encode("utf-8", errors="surrogateescape"),
        path,
        expected_existing=expected_existing,
    )


def create_backup(path: str | Path) -> tuple[Path, tuple[int, int]]:
    src = Path(path)
    if src.is_symlink():
        raise ValueError(f"refusing symbolic link input: {src}")

    source_flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
    source_fd = os.open(src, source_flags)
    try:
        info = os.fstat(source_fd)
        if not stat.S_ISREG(info.st_mode):
            raise ValueError(f"not a regular file: {src}")
        limit = input_limit_bytes()
        if info.st_size > limit:
            raise ValueError(f"refusing input larger than {limit} bytes: {src}")

        for index in range(1000):
            suffix = ".bak" if index == 0 else f".bak.{index}"
            candidate = src.with_suffix(src.suffix + suffix)
            flags = (
                os.O_WRONLY
                | os.O_CREAT
                | os.O_EXCL
                | getattr(os, "O_NOFOLLOW", 0)
            )
            try:
                backup_fd = os.open(candidate, flags, 0o600)
            except FileExistsError:
                continue

            try:
                copied = 0
                while True:
                    chunk = os.read(source_fd, 1024 * 1024)
                    if not chunk:
                        break
                    copied += len(chunk)
                    if copied > limit:
                        raise ValueError(
                            f"refusing input larger than {limit} bytes: {src}"
                        )
                    view = memoryview(chunk)
                    while view:
                        written = os.write(backup_fd, view)
                        if written <= 0:
                            raise OSError("backup write made no progress")
                        view = view[written:]
                os.fsync(backup_fd)
                return candidate, (info.st_dev, info.st_ino)
            except Exception:
                candidate.unlink(missing_ok=True)
                raise
            finally:
                os.close(backup_fd)
        raise ValueError(f"could not allocate a backup name for: {src}")
    finally:
        os.close(source_fd)


def write_text_output(text: str, path: str | None) -> None:
    if path is None or path == "-":
        sys.stdout.write(text)
        if text and not text.endswith("\n"):
            sys.stdout.write("\n")
        return
    atomic_write_text(text, path)


def emit_json(data: Any) -> None:
    json.dump(data, sys.stdout, indent=2, ensure_ascii=False)
    sys.stdout.write("\n")


def cleaned_path(src: Path, suffix: str = ".cleaned") -> Path:
    """path/to/file.ext -> path/to/file.cleaned.ext"""
    return src.with_name(f"{src.stem}{suffix}{src.suffix}")
