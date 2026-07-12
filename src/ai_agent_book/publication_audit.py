"""Automated publication artifact checks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from bs4 import BeautifulSoup


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
