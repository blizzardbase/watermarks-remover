"""Tests for SVG/HTML/MD/DOCX/ODT container cleaners."""

from __future__ import annotations

import io
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "skills" / "remove-ai-marks" / "scripts"
sys.path.insert(0, str(SCRIPTS))

from container_meta import (  # noqa: E402
    clean_container,
    clean_docx,
    clean_html,
    clean_markdown,
    clean_odt,
    clean_svg,
    inspect_container,
    inspect_html,
    inspect_markdown,
    inspect_svg,
)


def test_markdown_frontmatter():
    text = """---
title: Hello
generator: Claude
ai_generated: true
---
Body\u200b text.
"""
    _c2, has_ai, findings, _d = inspect_markdown(text)
    assert has_ai
    assert any("generator" in f or "ai" in f.lower() for f in findings)
    cleaned, actions = clean_markdown(text)
    assert "generator:" not in cleaned
    assert "ai_generated:" not in cleaned
    assert "title: Hello" in cleaned
    assert any("drop" in a for a in actions)


def test_markdown_drops_nested_children_with_parent():
    text = "---\ntitle: Kept\nai_generated:\n  model: Claude\n  score: 1\n---\nBody\n"
    cleaned, actions = clean_markdown(text)
    assert "title: Kept" in cleaned
    assert "ai_generated" not in cleaned
    assert "model: Claude" not in cleaned
    assert "score: 1" not in cleaned
    assert actions


def test_markdown_preserves_generic_generator_and_arbitrary_values():
    text = "---\ngenerator: Hugo\ntitle: OpenAI field notes\n---\nBody\n"
    _c2, has_ai, _findings, _details = inspect_markdown(text)
    cleaned, actions = clean_markdown(text)
    assert not has_ai
    assert cleaned == text
    assert actions == ["no AI frontmatter keys removed"]


def test_html_meta_strip():
    html = """<html><head>
<meta name="generator" content="ChatGPT">
<meta name="viewport" content="width=device-width">
<meta name="description" content="ok">
</head><body data-ai-model="gpt">Hi</body></html>"""
    _c2, has_ai, findings, _ = inspect_html(html)
    assert has_ai
    cleaned, actions = clean_html(html)
    assert "ChatGPT" not in cleaned
    assert "viewport" in cleaned
    assert "data-ai-model" not in cleaned
    assert any("drop" in a for a in actions)


def test_html_preserves_generic_generator_and_descriptive_content():
    html = (
        '<meta name="generator" content="Hugo">'
        '<meta name="description" content="OpenAI field notes">'
    )
    _c2, has_ai, _findings, _details = inspect_html(html)
    cleaned, actions = clean_html(html)
    assert not has_ai
    assert cleaned == html
    assert actions == ["no HTML AI meta removed"]


def test_html_jsonld_removes_only_provenance_field():
    html = (
        '<script type="application/ld+json">'
        '{"name":"OpenAI field notes","generator":"ChatGPT","count":2}'
        "</script>"
    )
    cleaned, actions = clean_html(html)
    assert '"name":"OpenAI field notes"' in cleaned
    assert '"count":2' in cleaned
    assert '"generator"' not in cleaned
    assert any("json-ld" in action for action in actions)


def test_html_jsonld_escapes_script_terminator():
    html = (
        '<script type="application/ld+json">'
        '{"name":"a<\\/script><script>x<\\/script>","generator":"ChatGPT"}'
        "</script>"
    )
    cleaned, _actions = clean_html(html)
    assert cleaned.count("<script") == 1
    assert "</script>" not in cleaned[: cleaned.rindex("</script>")]


def test_svg_metadata():
    svg = b"""<?xml version="1.0"?>
<svg xmlns="http://www.w3.org/2000/svg">
  <metadata>c2pa contentcredentials Anthropic</metadata>
  <circle cx="1" cy="1" r="1"/>
</svg>"""
    has_c2pa, has_ai, findings, _ = inspect_svg(svg)
    assert has_c2pa or has_ai
    cleaned, actions = clean_svg(svg)
    assert b"<metadata" not in cleaned.lower() or b"c2pa" not in cleaned.lower()
    assert b"<circle" in cleaned
    assert any("metadata" in a or "drop" in a for a in actions)


def test_svg_preserves_generic_metadata():
    svg = b'<svg><metadata><title>Artist notes</title></metadata><text>OpenAI</text></svg>'
    has_c2pa, has_ai, _findings, _details = inspect_svg(svg)
    cleaned, actions = clean_svg(svg)
    assert not has_c2pa
    assert not has_ai
    assert cleaned == svg
    assert actions == ["no SVG metadata removed"]


def test_svg_inspect_and_clean_share_marker_source():
    svg = b"<svg><metadata>trainedAlgorithmicMedia</metadata></svg>"
    _has_c2pa, has_ai, _findings, _details = inspect_svg(svg)
    cleaned, actions = clean_svg(svg)
    assert has_ai
    assert b"trainedAlgorithmicMedia" not in cleaned
    assert actions


def _make_docx_with_app(app_name: str = "Claude AI Writer") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr(
            "[Content_Types].xml",
            """<?xml version="1.0"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="xml" ContentType="application/xml"/>
  <Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>
  <Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>
  <Override PartName="/customXml/item1.xml" ContentType="application/xml"/>
</Types>""",
        )
        zf.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"><w:body><w:p><w:r><w:t>Hello</w:t></w:r></w:p></w:body></w:document>',
        )
        zf.writestr(
            "docProps/app.xml",
            f'<?xml version="1.0"?><Properties><Application>{app_name}</Application></Properties>',
        )
        zf.writestr(
            "customXml/item1.xml",
            '<?xml version="1.0"?><root>c2pa contentcredentials</root>',
        )
    return buf.getvalue()


def test_docx_strips_app_and_preserves_customxml():
    data = _make_docx_with_app()
    cleaned, actions = clean_docx(data)
    assert "scrub docProps/app.xml field Application" in actions
    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        names = zf.namelist()
        assert "word/document.xml" in names
        assert "customXml/item1.xml" in names
        assert b"c2pa contentcredentials" in zf.read("customXml/item1.xml")
        app = zf.read("docProps/app.xml").decode()
        assert "Claude" not in app


def test_docx_reports_preserved_customxml_separately(tmp_path: Path):
    src = tmp_path / "source.docx"
    dest = tmp_path / "cleaned.docx"
    src.write_bytes(_make_docx_with_app())
    result = clean_container(src, dest)
    assert not result["still_has_c2pa"]
    assert not result["still_has_ai_metadata"]
    preserved = result["meta"]["preserved_custom_xml_signals"]
    assert preserved
    assert preserved[0]["part"] == "customXml/item1.xml"
    report = inspect_container(dest)
    assert report.has_c2pa
    assert report.has_ai_metadata
    assert any("preserved (not removed)" in item for item in report.findings)


def test_docx_unexpected_residual_still_fails_clean_status(tmp_path: Path):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("word/document.xml", "<w:document/>")
        zf.writestr("docProps/other.xml", "<root>c2pa</root>")
        zf.writestr("customXml/item1.xml", "<root>c2pa</root>")
    src = tmp_path / "source.docx"
    dest = tmp_path / "cleaned.docx"
    src.write_bytes(buf.getvalue())
    result = clean_container(src, dest)
    assert result["still_has_c2pa"]


def _make_odt(generator: str = "Anthropic Claude") -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("mimetype", "application/vnd.oasis.opendocument.text")
        zf.writestr(
            "meta.xml",
            f'<?xml version="1.0"?><office:document-meta xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" xmlns:meta="urn:oasis:names:tc:opendocument:xmlns:meta:1.0"><meta:generator>{generator}</meta:generator></office:document-meta>',
        )
        zf.writestr(
            "content.xml",
            '<?xml version="1.0"?><office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0"/>',
        )
        zf.writestr(
            "META-INF/manifest.xml",
            '<?xml version="1.0"?><manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0"/>',
        )
    return buf.getvalue()


def test_odt_drops_generator(tmp_path: Path):
    data = _make_odt()
    cleaned, actions = clean_odt(data)
    assert any("generator" in a for a in actions)
    with zipfile.ZipFile(io.BytesIO(cleaned)) as zf:
        meta = zf.read("meta.xml").decode()
        assert "Claude" not in meta
        assert "meta:generator" not in meta or "Anthropic" not in meta


def test_clean_container_markdown_file(tmp_path: Path):
    src = tmp_path / "x.md"
    src.write_text("---\ngenerator: OpenAI\n---\nHi\u200b\n", encoding="utf-8")
    dest = tmp_path / "x.cleaned.md"
    result = clean_container(src, dest)
    assert dest.is_file()
    body = dest.read_text(encoding="utf-8")
    assert "generator" not in body
    assert "\u200b" not in body
    assert result["format"] == "markdown"


def test_inspect_container_svg(tmp_path: Path):
    src = tmp_path / "a.svg"
    src.write_bytes(
        b'<svg xmlns="http://www.w3.org/2000/svg"><metadata>c2pa</metadata></svg>'
    )
    report = inspect_container(src)
    assert report.format == "svg"
    assert report.has_c2pa or report.has_ai_metadata


def test_fixtures_md_html_svg_roundtrip(tmp_path: Path):
    root = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
    for name in ("sample_ai.md", "sample_ai.html", "sample_meta.svg"):
        src = root / name
        dest = tmp_path / f"{name}.cleaned{src.suffix}"
        result = clean_container(src, dest)
        assert dest.is_file()
        assert result["format"] in ("markdown", "html", "svg")
        # AI-ish keys/tags should be reduced
        body = dest.read_bytes().lower()
        assert b"chatgpt" not in body
        assert b"generator: claude" not in body


def test_pdf_is_inspect_only(tmp_path: Path):
    from container_meta import clean_pdf, inspect_pdf

    xmp = (
        b"<?xpacket begin='' id='W5M0MpCehiHzreSzNTczkc9d'?>"
        b"<x:xmpmeta xmlns:x='adobe:ns:meta/'>"
        b"<rdf:RDF xmlns:rdf='http://www.w3.org/1999/02/22-rdf-syntax-ns#'>"
        b"<rdf:Description>"
        b"<digitalSourceType>trainedAlgorithmicMedia</digitalSourceType>"
        b"</rdf:Description></rdf:RDF></x:xmpmeta>"
        b"<?xpacket end='w'?>"
    )
    # Minimal-ish PDF skeleton (not renderable; enough for byte-level tools)
    pdf = (
        b"%PDF-1.4\n"
        b"1 0 obj<<>>endobj\n"
        b"trailer<<>>\n"
        + xmp
        + b"\n%%EOF\n"
    )
    src = tmp_path / "t.pdf"
    dest = tmp_path / "t.cleaned.pdf"
    src.write_bytes(pdf)
    has_c2pa, has_ai, findings, _ = inspect_pdf(src, pdf)
    assert has_ai or has_c2pa or findings
    with pytest.raises(ValueError, match="disabled"):
        clean_pdf(src, dest)
    assert not dest.exists()
