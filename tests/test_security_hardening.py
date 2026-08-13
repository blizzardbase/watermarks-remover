"""Tests for bounded input, safe output, backups, and archive limits."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "remove-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from common import atomic_write_text, create_backup, read_bytes_input  # noqa: E402
from container_meta import (  # noqa: E402
    MAX_ZIP_DECOMPRESSED_BYTES,
    MAX_ZIP_MEMBERS,
    _check_zip_archive,
    _check_zip_budget,
    inspect_docx,
)


def test_rejects_symbolic_link_input(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("secret", encoding="utf-8")
    link = tmp_path / "link.txt"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic link"):
        read_bytes_input(link)


def test_rejects_symbolic_link_output(tmp_path: Path):
    target = tmp_path / "target.txt"
    target.write_text("keep", encoding="utf-8")
    link = tmp_path / "output.txt"
    link.symlink_to(target)
    with pytest.raises(ValueError, match="symbolic link"):
        atomic_write_text("replace", link)
    assert target.read_text(encoding="utf-8") == "keep"


def test_rejects_oversized_input_from_environment(tmp_path: Path, monkeypatch):
    source = tmp_path / "large.txt"
    source.write_bytes(b"12345")
    monkeypatch.setenv("WATERMARKS_MAX_INPUT_BYTES", "4")
    with pytest.raises(ValueError, match="larger than 4 bytes"):
        read_bytes_input(source)


def test_backup_never_overwrites_an_older_backup(tmp_path: Path):
    source = tmp_path / "note.txt"
    source.write_text("first", encoding="utf-8")
    first, first_identity = create_backup(source)
    source.write_text("second", encoding="utf-8")
    second, second_identity = create_backup(source)
    assert first.name == "note.txt.bak"
    assert second.name == "note.txt.bak.1"
    assert first.read_text(encoding="utf-8") == "first"
    assert second.read_text(encoding="utf-8") == "second"
    assert first_identity == second_identity


def test_atomic_write_refuses_existing_output_without_in_place_identity(tmp_path: Path):
    output = tmp_path / "output.txt"
    output.write_text("old", encoding="utf-8")
    with pytest.raises(ValueError, match="without in place mode"):
        atomic_write_text("new", output)
    assert output.read_text(encoding="utf-8") == "old"


def test_atomic_write_refuses_changed_in_place_target(tmp_path: Path):
    output = tmp_path / "output.txt"
    output.write_text("original", encoding="utf-8")
    info = output.stat()
    expected = (info.st_dev, info.st_ino)
    replacement = tmp_path / "replacement.txt"
    replacement.write_text("attacker", encoding="utf-8")
    replacement.replace(output)
    with pytest.raises(ValueError, match="changed before replacement"):
        atomic_write_text("cleaned", output, expected_existing=expected)
    assert output.read_text(encoding="utf-8") == "attacker"


def test_zip_budget_rejects_oversized_member():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
        info = zf.infolist()[0]
    info.file_size = MAX_ZIP_DECOMPRESSED_BYTES + 1
    raised = False
    try:
        _check_zip_budget(info, [0])
    except ValueError:
        raised = True
    assert raised


def test_zip_budget_accumulates_across_members():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("a.xml", b"a")
        zf.writestr("b.xml", b"b")
    with zipfile.ZipFile(io.BytesIO(buf.getvalue())) as zf:
        infos = zf.infolist()
    for info in infos:
        info.file_size = MAX_ZIP_DECOMPRESSED_BYTES // 2 + 1024
    budget = [0]
    raised = False
    for info in infos:
        try:
            _check_zip_budget(info, budget)
        except ValueError:
            raised = True
            break
    assert raised


def test_zip_member_count_cap():
    class TooManyMembers:
        @staticmethod
        def infolist():
            return [None] * (MAX_ZIP_MEMBERS + 1)

    with pytest.raises(ValueError, match="member count"):
        _check_zip_archive(TooManyMembers())


def test_inspect_docx_with_ai_markers_does_not_crash():
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr(
            "docProps/app.xml",
            "<Properties><Application>Claude AI Writer</Application></Properties>",
        )
        zf.writestr(
            "docProps/core.xml",
            "<cp:coreProperties><dc:creator>Anthropic</dc:creator></cp:coreProperties>",
        )
    has_c2pa, has_ai, findings, _ = inspect_docx(buf.getvalue())
    assert has_ai
    assert findings
    assert not has_c2pa or has_ai
