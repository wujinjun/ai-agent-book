import json
import zipfile
from pathlib import Path

from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfgen.canvas import Canvas

from ai_agent_book.publication_audit import (
    audit_contact_sheets,
    audit_epub,
    audit_html,
    audit_pdf,
)
from scripts.build_pandoc import inject_epub_svg_fallbacks


def test_html_audit_reports_reader_breakages(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<html><body><a href="missing/">broken</a><img src="x.png">'
        '<code class="mermaid">A--B</code><h2 id="same">A</h2>'
        '<h3 id="same">B</h3></body></html>',
        encoding="utf-8",
    )

    issues = audit_html(tmp_path)

    assert {issue.code for issue in issues} == {
        "broken-link",
        "broken-image",
        "duplicate-id",
        "missing-alt",
        "raw-mermaid",
    }


def test_html_audit_accepts_valid_local_resources(tmp_path: Path) -> None:
    (tmp_path / "chapter").mkdir()
    (tmp_path / "chapter/index.html").write_text(
        '<html><body><h1 id="lesson">Lesson</h1><img src="../diagram.svg" alt="流程图">'
        '<a href="../#home">Home</a></body></html>',
        encoding="utf-8",
    )
    (tmp_path / "diagram.svg").write_text("<svg></svg>", encoding="utf-8")
    (tmp_path / "index.html").write_text(
        '<html><body><h1 id="home">Home</h1></body></html>',
        encoding="utf-8",
    )

    assert audit_html(tmp_path) == []


def test_epub_svg_fallback_injection_adds_resource_and_rewrites_source(tmp_path: Path) -> None:
    root = tmp_path / "root"
    svg = root / "assets/diagrams/svg/demo.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text("<svg xmlns=\"http://www.w3.org/2000/svg\"></svg>", encoding="utf-8")
    epub_path = tmp_path / "book.epub"
    _write_minimal_epub(epub_path)

    inject_epub_svg_fallbacks(epub_path, root)

    with zipfile.ZipFile(epub_path) as archive:
        names = set(archive.namelist())
        chapter = archive.read("EPUB/text/ch001.xhtml").decode()
        manifest = archive.read("EPUB/content.opf").decode()
    assert "EPUB/media/demo.svg" in names
    assert 'srcset="../media/demo.svg"' in chapter
    assert 'href="media/demo.svg" media-type="image/svg+xml"' in manifest
    assert audit_epub(epub_path) == []


def test_pdf_audit_checks_page_count_title_and_final_chapter(tmp_path: Path) -> None:
    pdf = tmp_path / "book.pdf"
    registerFont(UnicodeCIDFont("STSong-Light"))
    canvas = Canvas(str(pdf), pagesize=(595.28, 841.89))
    canvas.setFont("STSong-Light", 14)
    canvas.drawString(72, 760, "AI Agent 从零到实战")
    canvas.showPage()
    canvas.setFont("STSong-Light", 14)
    canvas.drawString(72, 760, "第38章 技术选型")
    canvas.save()

    assert audit_pdf(
        pdf,
        min_pages=2,
        required_text=("AI Agent", "技术选型"),
    ) == []


def test_contact_sheet_audit_detects_missing_and_duplicate_entries(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    index = tmp_path / "contact" / "index.json"
    index.parent.mkdir()
    manifest.write_text(
        json.dumps(
            [
                {"semantic_id": "first"},
                {"semantic_id": "second"},
                {"semantic_id": "third"},
            ]
        ),
        encoding="utf-8",
    )
    index.write_text(
        json.dumps(
            {
                "diagram_count": 3,
                "page_count": 1,
                "entries": [
                    {"semantic_id": "first", "page": 1, "slot": 1},
                    {"semantic_id": "first", "page": 1, "slot": 2},
                    {"semantic_id": "third", "page": 1, "slot": 2},
                ],
            }
        ),
        encoding="utf-8",
    )

    issues = audit_contact_sheets(manifest, index)

    assert {issue.code for issue in issues} == {
        "duplicate-diagram",
        "duplicate-slot",
        "missing-contact-page",
        "missing-diagram",
    }


def _write_minimal_epub(path: Path) -> None:
    opf = """<?xml version="1.0" encoding="utf-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="chapter" href="text/ch001.xhtml" media-type="application/xhtml+xml"/>
<item id="png" href="media/file0.png" media-type="image/png"/>
</manifest><spine><itemref idref="chapter"/></spine></package>"""
    chapter = """<html xmlns="http://www.w3.org/1999/xhtml"><body>
<picture><source type="image/svg+xml" srcset="assets/diagrams/svg/demo.svg"/>
<img src="../media/file0.png" alt="演示图"/></picture></body></html>"""
    with zipfile.ZipFile(path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip", compress_type=zipfile.ZIP_STORED)
        archive.writestr("EPUB/content.opf", opf)
        archive.writestr("EPUB/nav.xhtml", "<html></html>")
        archive.writestr("EPUB/text/ch001.xhtml", chapter)
        archive.writestr("EPUB/media/file0.png", b"png")
