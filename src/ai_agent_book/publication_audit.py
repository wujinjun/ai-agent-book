"""Automated publication artifact checks."""

from __future__ import annotations

import posixpath
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit
from xml.etree import ElementTree

from bs4 import BeautifulSoup
from pypdf import PdfReader


@dataclass(frozen=True, slots=True, order=True)
class AuditIssue:
    path: str
    code: str
    detail: str


def audit_html(site_dir: Path) -> list[AuditIssue]:
    """Audit local HTML links, images, identifiers, and unrendered diagrams."""

    site_dir = site_dir.resolve()
    issues: list[AuditIssue] = []
    for html_path in sorted(site_dir.rglob("*.html")):
        relative = html_path.relative_to(site_dir).as_posix()
        soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
        identifiers: set[str] = set()
        for element in soup.find_all(id=True):
            identifier = str(element["id"])
            if identifier in identifiers:
                issues.append(AuditIssue(relative, "duplicate-id", identifier))
            identifiers.add(identifier)

        for image in soup.find_all("img"):
            if not image.get("alt"):
                issues.append(AuditIssue(relative, "missing-alt", str(image.get("src", ""))))
            target = _local_target(site_dir, html_path, str(image.get("src", "")))
            if target is not None and not target.is_file():
                issues.append(AuditIssue(relative, "broken-image", str(image.get("src", ""))))

        for link in soup.find_all("a", href=True):
            href = str(link["href"])
            target = _local_target(site_dir, html_path, href)
            if target is not None and not _existing_html_target(target):
                issues.append(AuditIssue(relative, "broken-link", href))

        if soup.select_one("pre.mermaid, code.mermaid, .language-mermaid") is not None:
            issues.append(AuditIssue(relative, "raw-mermaid", "unrendered Mermaid source"))
    return sorted(issues)


def audit_epub(epub_path: Path) -> list[AuditIssue]:
    """Audit EPUB structure plus SVG/PNG picture resources."""

    issues: list[AuditIssue] = []
    with zipfile.ZipFile(epub_path) as archive:
        names = set(archive.namelist())
        if archive.read("mimetype") != b"application/epub+zip":
            issues.append(AuditIssue(epub_path.name, "invalid-mimetype", "mimetype"))
        if "EPUB/nav.xhtml" not in names:
            issues.append(AuditIssue(epub_path.name, "missing-nav", "EPUB/nav.xhtml"))
        opf = ElementTree.fromstring(archive.read("EPUB/content.opf"))
        manifest_paths = {
            "EPUB/" + str(item.attrib["href"])
            for item in opf.findall(".//{*}manifest/{*}item")
            if "href" in item.attrib
        }
        if not opf.findall(".//{*}spine/{*}itemref"):
            issues.append(AuditIssue(epub_path.name, "missing-spine", "EPUB/content.opf"))

        for chapter_name in sorted(name for name in names if name.endswith(".xhtml")):
            soup = BeautifulSoup(archive.read(chapter_name), "xml")
            if soup.select_one("pre.mermaid, code.mermaid, .language-mermaid"):
                issues.append(AuditIssue(chapter_name, "raw-mermaid", "Mermaid source"))
            for picture in soup.find_all("picture"):
                source = picture.find("source", attrs={"type": "image/svg+xml"})
                image = picture.find("img")
                if source is None or image is None:
                    issues.append(AuditIssue(chapter_name, "invalid-picture", str(picture)))
                    continue
                for reference, code in (
                    (str(source.get("srcset", "")), "broken-svg"),
                    (str(image.get("src", "")), "broken-png"),
                ):
                    resolved = posixpath.normpath(
                        posixpath.join(posixpath.dirname(chapter_name), reference)
                    )
                    if resolved not in names or resolved not in manifest_paths:
                        issues.append(AuditIssue(chapter_name, code, reference))
                if not image.get("alt"):
                    issues.append(
                        AuditIssue(chapter_name, "missing-alt", str(image.get("src", "")))
                    )
    return sorted(issues)


def audit_pdf(
    pdf_path: Path,
    *,
    min_pages: int = 20,
    required_text: tuple[str, ...] = (),
) -> list[AuditIssue]:
    """Audit PDF dimensions, page count, and required extractable text."""

    issues: list[AuditIssue] = []
    reader = PdfReader(pdf_path)
    if len(reader.pages) < min_pages:
        issues.append(AuditIssue(pdf_path.name, "too-few-pages", str(len(reader.pages))))
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    for required in required_text:
        if required not in text:
            issues.append(AuditIssue(pdf_path.name, "missing-text", required))
    for index, page in enumerate(reader.pages, start=1):
        width = float(page.mediabox.width)
        height = float(page.mediabox.height)
        if abs(width - 595.28) > 2 or abs(height - 841.89) > 2:
            issues.append(
                AuditIssue(pdf_path.name, "non-a4-page", f"page {index}: {width}x{height}")
            )
            break
    return sorted(issues)


def _local_target(site_dir: Path, source: Path, reference: str) -> Path | None:
    if not reference or reference.startswith(("mailto:", "tel:", "data:", "javascript:")):
        return None
    parsed = urlsplit(reference)
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if path.startswith("/"):
        return site_dir / path.lstrip("/")
    if not path:
        return source
    return (source.parent / path).resolve()


def _existing_html_target(target: Path) -> bool:
    if target.is_file():
        return True
    return target.is_dir() and (target / "index.html").is_file()
