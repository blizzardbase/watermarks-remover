"""Tests for the offline rewrite prompt helper."""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "remove-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from rewrite_text import build_prompt, rewrite_prompt  # noqa: E402


def test_build_prompt_paraphrase_is_word_choice_plus_syntax():
    p = build_prompt("paraphrase", "Hello world facts 42.", lang="French", original_lang="English")
    assert "Hello world facts 42." in p
    assert "clause order" in p
    assert "connectors" in p


def test_build_prompt_humanize_and_code_contain_text():
    for strength, keyword in (("humanize", "human prose"), ("code", "comments")):
        p = build_prompt(strength, "ABC 123", lang="French", original_lang="English")
        assert "ABC 123" in p
        assert keyword in p


def test_build_prompt_unknown_strength_raises():
    with pytest.raises(ValueError):
        build_prompt("nope", "ABC", lang="French", original_lang="English")


def test_rewrite_prompt_is_offline():
    out, info = rewrite_prompt(
        "Sample prose about water marks.",
        strength="paraphrase",
        lang="French",
        original_lang="English",
    )
    assert info["mode"] == "offline_prompt"
    assert "Sample prose" in out
    assert info["network_calls"] == 0


def test_structural_and_backtranslate_prompts():
    for strength in ("structural", "backtranslate"):
        p = build_prompt(strength, "ABC 123", lang="German", original_lang="English")
        assert "ABC 123" in p


def test_source_has_no_network_or_process_imports_or_api_key():
    source = (SCRIPTS / "rewrite_text.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".", 1)[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".", 1)[0])
    assert not imported.intersection(
        {"urllib", "requests", "httpx", "socket", "subprocess"}
    )
    assert "api_key" not in source.lower()
