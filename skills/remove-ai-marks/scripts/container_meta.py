#!/usr/bin/env python3
"""Inspect or clean AI provenance metadata in document containers.

Formats: SVG, PDF inspection, DOCX, ODT, HTML, and Markdown frontmatter.
"""

from __future__ import annotations

import io
import json
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, NoReturn
from common import atomic_write_bytes, atomic_write_text, read_bytes_input
from image_meta import AI_META_HINTS, C2PA_MARKERS

# Frontmatter / meta keys that often carry AI provenance
HIGH_CONFIDENCE_FRONTMATTER_KEYS = frozenset(
    {
        "ai_generated",
        "ai-generated",
        "synthid",
        "c2pa",
        "content_credentials",
        "contentcredentials",
        "digital_source_type",
        "digitalsourcetype",
    }
)

CONTEXTUAL_FRONTMATTER_KEYS = frozenset(
    {
        "ai",
        "generator",
        "created_with",
        "createdwith",
        "model",
        "llm",
        "provenance",
    }
)

AI_META_NAME_RE = re.compile(
    r"ai[-_ ]?generated|claude|anthropic|openai|chatgpt|gemini|synthid|"
    r"c2pa|content.?credential|digital.?source|trainedAlgorithmicMedia|aigc",
    re.I,
)

SVG_DROP_TAGS = frozenset(
    {
        "{http://www.w3.org/2000/svg}metadata",
        "metadata",
        "{http://www.w3.org/1999/02/22-rdf-syntax-ns#}RDF",
        "{adobe:ns:meta/}xmpmeta",
    }
)


@dataclass
class ContainerInspectReport:
    path: str
    format: str
    has_c2pa: bool
    has_ai_metadata: bool
    findings: list[str] = field(default_factory=list)
    details: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "format": self.format,
            "has_c2pa": self.has_c2pa,
            "has_ai_metadata": self.has_ai_metadata,
            "findings": self.findings,
            "details": self.details,
        }


def detect_container_format(path: Path, data: bytes | None = None) -> str:
    ext = path.suffix.lower()
    if ext in (".svg",):
        return "svg"
    if ext in (".pdf",):
        return "pdf"
    if ext in (".docx",):
        return "docx"
    if ext in (".odt",):
        return "odt"
    if ext in (".html", ".htm"):
        return "html"
    if ext in (".md", ".markdown", ".mdx"):
        return "markdown"
    if data is not None:
        if data[:4] == b"%PDF":
            return "pdf"
        if data[:100].lstrip().startswith(b"<") and b"svg" in data[:500].lower():
            return "svg"
        if data[:2] == b"PK":
            # zip-based; sniff
            try:
                with zipfile.ZipFile(io.BytesIO(data)) as zf:
                    names = _zip_member_names(zf)
                    if "word/document.xml" in names:
                        return "docx"
                    if "content.xml" in names and "meta.xml" in names:
                        return "odt"
            except zipfile.BadZipFile:
                pass
    return "unknown"


def _blob_hits(blob: bytes) -> tuple[bool, bool, list[str]]:
    lower = blob.lower()
    findings: list[str] = []
    has_c2pa = False
    has_ai = False
    for n in C2PA_MARKERS:
        if n.lower() in lower:
            has_c2pa = True
            findings.append(f"marker:{n.decode('ascii', errors='replace')}")
    for n in AI_META_HINTS:
        if n.lower() in lower:
            has_ai = True
            label = n.decode("ascii", errors="replace")
            if label not in {f.split(":", 1)[-1] for f in findings}:
                findings.append(f"ai:{label}")
    return has_c2pa, has_ai or has_c2pa, findings[:30]


def _contains_markers(blob: bytes, markers: tuple[bytes, ...]) -> list[str]:
    lower = blob.lower()
    return [
        marker.decode("ascii", errors="replace")
        for marker in markers
        if marker.lower() in lower
    ]


# ---------------------------------------------------------------------------
# Markdown frontmatter
# ---------------------------------------------------------------------------

_FM_RE = re.compile(r"\A---\r?\n(.*?)\r?\n---\r?\n?", re.DOTALL)


def _parse_simple_yaml_keys(block: str) -> list[tuple[str, str, int]]:
    """Return list of (key, full_line, line_index) for top-level keys only."""
    rows: list[tuple[str, str, int]] = []
    for i, line in enumerate(block.splitlines()):
        if not line.strip() or line.strip().startswith("#"):
            continue
        if line[0] in (" ", "\t", "-"):
            continue  # nested / list — leave alone
        m = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if m:
            rows.append((m.group(1), line, i))
    return rows


def _frontmatter_is_ai(key: str, value: str) -> bool:
    normalized = key.lower()
    if normalized in HIGH_CONFIDENCE_FRONTMATTER_KEYS:
        return True
    if normalized in CONTEXTUAL_FRONTMATTER_KEYS:
        return bool(AI_META_NAME_RE.search(value))
    if AI_META_NAME_RE.search(normalized):
        return True
    return False


def inspect_markdown(text: str) -> tuple[bool, bool, list[str], dict]:
    findings: list[str] = []
    has_ai = False
    m = _FM_RE.match(text)
    if not m:
        return False, False, [], {"has_frontmatter": False}
    block = m.group(1)
    keys = []
    for key, _line, _i in _parse_simple_yaml_keys(block):
        keys.append(key)
        val = _line.split(":", 1)[1] if ":" in _line else ""
        if _frontmatter_is_ai(key, val):
            has_ai = True
            findings.append(f"frontmatter key: {key}")
    c2pa = any("c2pa" in f.lower() or "content" in f.lower() for f in findings)
    return c2pa, has_ai, findings, {"has_frontmatter": True, "keys": keys}


def clean_markdown(text: str) -> tuple[str, list[str]]:
    actions: list[str] = []
    m = _FM_RE.match(text)
    if not m:
        return text, ["no YAML frontmatter"]
    block = m.group(1)
    body = text[m.end() :]
    kept: list[str] = []
    keep_nested = True
    for line in block.splitlines():
        if not line.strip() or line.strip().startswith("#"):
            if keep_nested:
                kept.append(line)
            continue
        if line[0] in (" ", "\t", "-"):
            if keep_nested:
                kept.append(line)
            continue
        km = re.match(r"^([A-Za-z0-9_.-]+)\s*:", line)
        if km:
            key = km.group(1)
            val = line.split(":", 1)[1] if ":" in line else ""
            if _frontmatter_is_ai(key, val):
                actions.append(f"drop frontmatter key: {key}")
                keep_nested = False
                continue
            keep_nested = True
            kept.append(line)
        else:
            keep_nested = True
            kept.append(line)
    if not actions:
        actions.append("no AI frontmatter keys removed")
    # strip trailing empty nested orphans already handled
    new_block = "\n".join(kept).strip("\n")
    if new_block:
        out = f"---\n{new_block}\n---\n{body}"
    else:
        out = body.lstrip("\n")
        actions.append("removed empty frontmatter block")
    return out, actions


# ---------------------------------------------------------------------------
# HTML
# ---------------------------------------------------------------------------

_META_TAG_RE = re.compile(
    r"<meta\b[^>]*>",
    re.I,
)
_JSONLD_RE = re.compile(
    r"(?P<open><script\b[^>]*type\s*=\s*[\"']application/ld\+json[\"'][^>]*>)"
    r"(?P<body>.*?)(?P<close></script>)",
    re.I | re.DOTALL,
)
_HTML_ATTR_RE = re.compile(
    r"([A-Za-z_:][\w:.-]*)\s*=\s*([\"'])(.*?)\2",
    re.DOTALL,
)


def _html_meta_is_ai(tag: str) -> bool:
    attrs = {key.lower(): value for key, _quote, value in _HTML_ATTR_RE.findall(tag)}
    name = attrs.get("name") or attrs.get("property") or ""
    content = attrs.get("content", "")
    return bool(name and _frontmatter_is_ai(name, content))


def _json_scalar_text(value: Any) -> str:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return str(value)
    try:
        return json.dumps(value, ensure_ascii=False)
    except (TypeError, ValueError):
        return ""


def _clean_jsonld_value(value: Any) -> tuple[Any, list[str]]:
    removed: list[str] = []
    if isinstance(value, dict):
        cleaned: dict[Any, Any] = {}
        for key, child in value.items():
            key_text = str(key)
            if _frontmatter_is_ai(key_text, _json_scalar_text(child)):
                removed.append(key_text)
                continue
            new_child, child_removed = _clean_jsonld_value(child)
            cleaned[key] = new_child
            removed.extend(child_removed)
        return cleaned, removed
    if isinstance(value, list):
        cleaned_list: list[Any] = []
        for child in value:
            new_child, child_removed = _clean_jsonld_value(child)
            cleaned_list.append(new_child)
            removed.extend(child_removed)
        return cleaned_list, removed
    return value, removed


def inspect_html(text: str) -> tuple[bool, bool, list[str], dict]:
    findings: list[str] = []
    has_ai = False
    has_c2pa = False
    for tag in _META_TAG_RE.findall(text):
        if _html_meta_is_ai(tag):
            has_ai = True
            findings.append(f"meta: {tag[:120]}")
            if re.search(r"c2pa|content.?credential", tag, re.I):
                has_c2pa = True
    for m in _JSONLD_RE.finditer(text):
        try:
            parsed = json.loads(m.group("body"))
        except (json.JSONDecodeError, TypeError, RecursionError):
            continue
        try:
            _cleaned, removed = _clean_jsonld_value(parsed)
        except RecursionError:
            continue
        if removed:
            has_ai = True
            findings.append(f"json-ld provenance fields: {', '.join(removed[:8])}")
            if any(re.search(r"c2pa|content.?credential", key, re.I) for key in removed):
                has_c2pa = True
    # data-ai* attributes
    for m in re.finditer(r"\bdata-ai[\w-]*\s*=\s*[\"'][^\"']*[\"']", text, re.I):
        has_ai = True
        findings.append(f"attr: {m.group(0)[:80]}")
    return has_c2pa, has_ai, findings, {}


def clean_html(text: str) -> tuple[str, list[str]]:
    actions: list[str] = []

    def _meta_sub(m: re.Match[str]) -> str:
        tag = m.group(0)
        if _html_meta_is_ai(tag):
            actions.append(f"drop meta: {tag[:80]}")
            return ""
        return tag

    out = _META_TAG_RE.sub(_meta_sub, text)

    def _jsonld_sub(m: re.Match[str]) -> str:
        try:
            parsed = json.loads(m.group("body"))
        except (json.JSONDecodeError, TypeError, RecursionError):
            return m.group(0)
        try:
            cleaned, removed = _clean_jsonld_value(parsed)
        except RecursionError:
            return m.group(0)
        if not removed:
            return m.group(0)
        actions.append(f"drop json-ld fields: {', '.join(removed[:8])}")
        body = (
            json.dumps(cleaned, ensure_ascii=False, separators=(",", ":"))
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )
        return f"{m.group('open')}{body}{m.group('close')}"

    out = _JSONLD_RE.sub(_jsonld_sub, out)
    out2, n = re.subn(r"\sdata-ai[\w-]*\s*=\s*[\"'][^\"']*[\"']", "", out, flags=re.I)
    if n:
        actions.append(f"drop data-ai* attributes x{n}")
        out = out2
    if not actions:
        actions.append("no HTML AI meta removed")
    return out, actions


# ---------------------------------------------------------------------------
# SVG
# ---------------------------------------------------------------------------

def inspect_svg(data: bytes) -> tuple[bool, bool, list[str], dict]:
    findings: list[str] = []
    has_c2pa = False
    has_ai = False
    try:
        text = data.decode("utf-8", errors="replace")
        blocks = re.findall(
            r"<metadata\b[^>]*>.*?</metadata\s*>|"
            r"<x:xmpmeta\b[^>]*>.*?</x:xmpmeta\s*>|"
            r"<!--.*?-->",
            text,
            re.I | re.DOTALL,
        )
        for block in blocks:
            c2pa, ai, hits = _blob_hits(block.encode("utf-8"))
            has_c2pa = has_c2pa or c2pa
            has_ai = has_ai or ai
            findings.extend(f"svg metadata: {hit}" for hit in hits)
        if blocks and not (has_ai or has_c2pa):
            findings.append("SVG metadata present without an AI marker")
    except Exception as e:
        findings.append(f"svg decode note: {e}")
    return has_c2pa, has_ai or has_c2pa, findings, {}


def clean_svg(data: bytes) -> tuple[bytes, list[str]]:
    actions: list[str] = []
    text = data.decode("utf-8", errors="surrogateescape")
    def _metadata_sub(match: re.Match[str]) -> str:
        block = match.group(0)
        _c2pa, has_ai, _hits = _blob_hits(block.encode("utf-8"))
        if has_ai:
            actions.append("drop SVG metadata with AI or C2PA markers")
            return ""
        return block

    text = re.sub(
        r"<metadata\b[^>]*>.*?</metadata\s*>",
        _metadata_sub,
        text,
        flags=re.I | re.DOTALL,
    )
    text = re.sub(
        r"<x:xmpmeta\b[^>]*>.*?</x:xmpmeta\s*>",
        _metadata_sub,
        text,
        flags=re.I | re.DOTALL,
    )
    # Drop comments that look like provenance
    def _cmt(m: re.Match[str]) -> str:
        body = m.group(0)
        _c2pa, has_ai, _hits = _blob_hits(body.encode("utf-8"))
        if has_ai:
            actions.append("drop SVG comment with AI markers")
            return ""
        return body

    text = re.sub(r"<!--.*?-->", _cmt, text, flags=re.DOTALL)
    if not actions:
        actions.append("no SVG metadata removed")
    return text.encode("utf-8", errors="surrogateescape"), actions


# ---------------------------------------------------------------------------
# DOCX / ODT (zip + XML)
# ---------------------------------------------------------------------------

DOCX_META_PARTS = (
    "docProps/core.xml",
    "docProps/app.xml",
    "docProps/custom.xml",
)
MAX_ZIP_DECOMPRESSED_BYTES = 256 * 1024 * 1024
MAX_ZIP_MEMBERS = 10_000


def _check_zip_archive(zf: zipfile.ZipFile) -> None:
    if len(zf.infolist()) > MAX_ZIP_MEMBERS:
        raise ValueError(
            f"zip member count exceeds cap ({MAX_ZIP_MEMBERS}); refusing to process"
        )


def _zip_member_names(zf: zipfile.ZipFile) -> set[str]:
    infos = zf.infolist()
    if len(infos) > MAX_ZIP_MEMBERS:
        raise ValueError(
            f"zip member count exceeds cap ({MAX_ZIP_MEMBERS}); refusing to process"
        )
    return {info.filename for info in infos}


def _check_zip_budget(info: zipfile.ZipInfo, budget: list[int]) -> None:
    """Bound archive supplied declared decompressed sizes."""
    if info.file_size < 0:
        raise ValueError("zip member reports a negative size")
    budget[0] += info.file_size
    if budget[0] > MAX_ZIP_DECOMPRESSED_BYTES:
        raise ValueError(
            "zip decompressed size exceeds cap "
            f"({MAX_ZIP_DECOMPRESSED_BYTES} bytes); refusing to process"
        )


def _read_member(
    zf: zipfile.ZipFile,
    info: zipfile.ZipInfo,
    actual_budget: list[int],
) -> bytes:
    remaining = MAX_ZIP_DECOMPRESSED_BYTES - actual_budget[0]
    if remaining < 0:
        raise ValueError("zip decompressed size exceeds cap; refusing to process")
    with zf.open(info) as handle:
        data = handle.read(remaining + 1)
    if len(data) > remaining:
        raise ValueError(
            f"zip member {info.filename} exceeds the remaining decompressed cap"
        )
    actual_budget[0] += len(data)
    return data


def inspect_docx(data: bytes) -> tuple[bool, bool, list[str], dict]:
    findings: list[str] = []
    has_c2pa = False
    has_ai = False
    parts: list[str] = []
    budget = [0]
    actual_budget = [0]
    details_preserved: list[dict[str, Any]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            _check_zip_archive(zf)
            parts = [info.filename for info in zf.infolist()]
            for info in zf.infolist():
                _check_zip_budget(info, budget)
                name = info.filename.lower()
                if not (
                    name.startswith("docprops/")
                    or name.startswith("customxml/")
                    or "c2pa" in name
                    or "provenance" in name
                ):
                    continue
                raw = _read_member(
                    zf,
                    info,
                    actual_budget,
                )
                c2, ai, hits = _blob_hits(raw)
                if c2 or ai:
                    if name.startswith("customxml/"):
                        preserved = {
                            "part": info.filename,
                            "has_c2pa": c2,
                            "has_ai_metadata": ai,
                            "findings": hits[:6],
                        }
                        details_preserved.append(preserved)
                        if c2:
                            has_c2pa = True
                        if ai:
                            has_ai = True
                        findings.append(
                            f"preserved (not removed) {info.filename}: "
                            f"{', '.join(hits[:6])}"
                        )
                        continue
                    if c2:
                        has_c2pa = True
                    if ai:
                        has_ai = True
                    findings.append(f"{info.filename}: {', '.join(hits[:6])}")
            # always flag customXml presence lightly
            custom = [n for n in parts if n.startswith("customXml/")]
            if custom:
                findings.append(f"customXml parts: {len(custom)}")
    except zipfile.BadZipFile:
        return False, False, ["not a valid DOCX zip"], {}
    return has_c2pa, has_ai or has_c2pa, findings, {
        "parts": len(parts),
        "preserved_custom_xml_signals": details_preserved,
    }


def clean_docx(data: bytes) -> tuple[bytes, list[str]]:
    actions: list[str] = []
    out_buf = io.BytesIO()
    budget = [0]
    actual_budget = [0]
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(
        out_buf, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        _check_zip_archive(zin)
        for info in zin.infolist():
            name = info.filename
            _check_zip_budget(info, budget)
            raw = _read_member(
                zin,
                info,
                actual_budget,
            )
            if name in DOCX_META_PARTS or name.startswith("docProps/"):
                text = raw.decode("utf-8", errors="replace")
                # Scrub known AI generator fields via simple regex on XML text nodes
                new = text
                for pat, repl, label in (
                    (
                        r"(<dc:creator[^>]*>)(.*?)(</dc:creator>)",
                        None,
                        "dc:creator",
                    ),
                    (
                        r"(<cp:lastModifiedBy[^>]*>)(.*?)(</cp:lastModifiedBy>)",
                        None,
                        "cp:lastModifiedBy",
                    ),
                    (
                        r"(<Application[^>]*>)(.*?)(</Application>)",
                        None,
                        "Application",
                    ),
                    (
                        r"(<AppVersion[^>]*>)(.*?)(</AppVersion>)",
                        None,
                        "AppVersion",
                    ),
                ):
                    def _sub(m: re.Match[str], _label=label) -> str:
                        inner = m.group(2)
                        if AI_META_NAME_RE.search(inner) or AI_META_NAME_RE.search(_label):
                            actions.append(f"scrub {name} field {_label}")
                            return m.group(1) + m.group(3)
                        # Always clear Application if it looks like AI
                        if _label in ("Application", "AppVersion") and re.search(
                            r"claude|openai|anthropic|gemini|chatgpt|synthid|copilot",
                            inner,
                            re.I,
                        ):
                            actions.append(f"scrub {name} field {_label}")
                            return m.group(1) + m.group(3)
                        return m.group(0)

                    new = re.sub(pat, _sub, new, flags=re.I | re.DOTALL)
                raw = new.encode("utf-8")
            zout.writestr(info, raw)
    if not actions:
        actions.append("no DOCX metadata parts removed")
    return out_buf.getvalue(), actions


def inspect_odt(data: bytes) -> tuple[bool, bool, list[str], dict]:
    findings: list[str] = []
    has_c2pa = False
    has_ai = False
    budget = [0]
    actual_budget = [0]
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            _check_zip_archive(zf)
            for info in zf.infolist():
                _check_zip_budget(info, budget)
                name = info.filename.lower()
                if name not in {
                    "meta.xml",
                    "meta-inf/manifest.xml",
                    "meta-inf/documentsignatures.xml",
                } and "c2pa" not in name and "provenance" not in name:
                    continue
                raw = _read_member(
                    zf,
                    info,
                    actual_budget,
                )
                c2, ai, hits = _blob_hits(raw)
                if c2 or ai:
                    if c2:
                        has_c2pa = True
                    if ai:
                        has_ai = True
                    findings.append(f"{info.filename}: {', '.join(hits[:6])}")
    except zipfile.BadZipFile:
        return False, False, ["not a valid ODT zip"], {}
    return has_c2pa, has_ai or has_c2pa, findings, {}


def clean_odt(data: bytes) -> tuple[bytes, list[str]]:
    actions: list[str] = []
    out_buf = io.BytesIO()
    budget = [0]
    actual_budget = [0]
    with zipfile.ZipFile(io.BytesIO(data)) as zin, zipfile.ZipFile(
        out_buf, "w", compression=zipfile.ZIP_DEFLATED
    ) as zout:
        _check_zip_archive(zin)
        for info in zin.infolist():
            name = info.filename
            _check_zip_budget(info, budget)
            raw = _read_member(
                zin,
                info,
                actual_budget,
            )
            if name == "meta.xml":
                text = raw.decode("utf-8", errors="replace")
                def _generator(match: re.Match[str]) -> str:
                    if AI_META_NAME_RE.search(match.group(0)):
                        actions.append("drop AI meta:generator")
                        return ""
                    return match.group(0)

                text = re.sub(
                    r"<meta:generator\b[^>]*>.*?</meta:generator\s*>",
                    _generator,
                    text,
                    flags=re.I | re.DOTALL,
                )
                # scrub creator-like if AI
                def _creator(m: re.Match[str]) -> str:
                    if AI_META_NAME_RE.search(m.group(0)):
                        actions.append("scrub creator-like meta")
                        return ""
                    return m.group(0)

                text = re.sub(
                    r"<dc:creator\b[^>]*>.*?</dc:creator\s*>",
                    _creator,
                    text,
                    flags=re.I | re.DOTALL,
                )
                raw = text.encode("utf-8")
            zout.writestr(info, raw)
    if not actions:
        actions.append("no ODT metadata removed")
    return out_buf.getvalue(), actions


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------

def inspect_pdf(_path: Path, data: bytes) -> tuple[bool, bool, list[str], dict]:
    findings: list[str] = []
    c2pa_hits = _contains_markers(data, C2PA_MARKERS)
    has_c2pa = bool(c2pa_hits)
    has_ai = has_c2pa
    findings.extend(f"pdf-bytes:{hit}" for hit in c2pa_hits)
    # XMP packet scan
    for match in re.finditer(
        rb"<x:xmpmeta\b.*?</x:xmpmeta\s*>",
        data,
        re.I | re.DOTALL,
    ):
        packet = match.group(0)
        _c2pa, packet_ai, hits = _blob_hits(packet)
        if packet_ai:
            has_ai = True
            findings.extend(f"pdf-xmp:{hit}" for hit in hits)
        else:
            findings.append("PDF XMP packet present without an AI marker")
    return has_c2pa, has_ai or has_c2pa, findings, {}


def clean_pdf(_path: Path, _dest: Path) -> NoReturn:
    """Refuse PDF rewriting because byte deletion can corrupt cross references."""
    raise ValueError(
        "PDF cleaning is disabled in the hardened fork; inspect only and use a separately audited PDF tool"
    )


# ---------------------------------------------------------------------------
# Unified API
# ---------------------------------------------------------------------------

def inspect_container(
    path: Path,
    data: bytes | None = None,
) -> ContainerInspectReport:
    if data is None:
        data = read_bytes_input(path)
    fmt = detect_container_format(path, data)
    details: dict[str, Any] = {}

    if fmt == "svg":
        has_c2pa, has_ai, findings, details = inspect_svg(data)
    elif fmt == "pdf":
        has_c2pa, has_ai, findings, details = inspect_pdf(path, data)
    elif fmt == "docx":
        has_c2pa, has_ai, findings, details = inspect_docx(data)
    elif fmt == "odt":
        has_c2pa, has_ai, findings, details = inspect_odt(data)
    elif fmt == "html":
        text = data.decode("utf-8", errors="replace")
        has_c2pa, has_ai, findings, details = inspect_html(text)
    elif fmt == "markdown":
        text = data.decode("utf-8", errors="replace")
        has_c2pa, has_ai, findings, details = inspect_markdown(text)
    else:
        has_c2pa, has_ai, findings = False, False, [f"unsupported container: {fmt}"]

    return ContainerInspectReport(
        path=str(path),
        format=fmt,
        has_c2pa=has_c2pa,
        has_ai_metadata=has_ai,
        findings=findings,
        details=details,
    )


def clean_container(
    path: Path,
    dest: Path,
    *,
    also_layer_a_text: bool = True,
    expected_existing: tuple[int, int] | None = None,
    data: bytes | None = None,
) -> dict[str, Any]:
    """Clean container metadata; optionally Layer-A scrub text bodies for md/html."""
    from text_unicode import clean_text  # local import to avoid cycles

    if data is None:
        data = read_bytes_input(path)
    fmt = detect_container_format(path, data)
    actions: list[str] = []
    meta: dict[str, Any] = {"format": fmt}

    if fmt == "svg":
        cleaned, actions = clean_svg(data)
        atomic_write_bytes(cleaned, dest, expected_existing=expected_existing)
    elif fmt == "pdf":
        clean_pdf(path, dest)
    elif fmt == "docx":
        cleaned, actions = clean_docx(data)
        atomic_write_bytes(cleaned, dest, expected_existing=expected_existing)
    elif fmt == "odt":
        cleaned, actions = clean_odt(data)
        atomic_write_bytes(cleaned, dest, expected_existing=expected_existing)
    elif fmt == "html":
        text = data.decode("utf-8", errors="surrogateescape")
        text, actions = clean_html(text)
        if also_layer_a_text:
            text2, stats = clean_text(text)
            if stats["removed_count"] or stats["replaced_count"]:
                actions.append(
                    f"layer A text: removed={stats['removed_count']} replaced={stats['replaced_count']}"
                )
                text = text2
        atomic_write_text(text, dest, expected_existing=expected_existing)
    elif fmt == "markdown":
        text = data.decode("utf-8", errors="surrogateescape")
        text, actions = clean_markdown(text)
        if also_layer_a_text:
            text2, stats = clean_text(text)
            if stats["removed_count"] or stats["replaced_count"]:
                actions.append(
                    f"layer A text: removed={stats['removed_count']} replaced={stats['replaced_count']}"
                )
                text = text2
        atomic_write_text(text, dest, expected_existing=expected_existing)
    else:
        raise ValueError(f"unsupported container format: {fmt}")

    if fmt in {"svg", "docx", "odt"}:
        output_data = cleaned
    else:
        output_data = text.encode("utf-8", errors="surrogateescape")
    after = inspect_container(dest, output_data)
    if fmt == "docx":
        preserved = after.details.get(
            "preserved_custom_xml_signals",
            [],
        )
        meta["preserved_custom_xml_signals"] = preserved
        expected_c2pa_findings = {
            marker
            for item in preserved
            if item.get("has_c2pa")
            for marker in item.get("findings", [])
        }
        expected_ai_findings = {
            marker
            for item in preserved
            if item.get("has_ai_metadata")
            for marker in item.get("findings", [])
        }
        unexpected_findings = [
            finding
            for finding in after.findings
            if not finding.startswith("preserved (not removed) ")
            and not finding.startswith("customXml parts:")
        ]
        has_unexpected = bool(unexpected_findings)
        preserved_c2pa = bool(expected_c2pa_findings) and not has_unexpected
        preserved_ai = bool(expected_ai_findings) and not has_unexpected
    else:
        preserved_c2pa = False
        preserved_ai = False
    return {
        "input": str(path),
        "output": str(dest),
        "format": fmt,
        "actions": actions,
        "bytes_in": len(data),
        "bytes_out": dest.stat().st_size,
        "still_has_c2pa": after.has_c2pa and not preserved_c2pa,
        "still_has_ai_metadata": after.has_ai_metadata and not preserved_ai,
        "post_findings": after.findings,
        "meta": meta,
    }
