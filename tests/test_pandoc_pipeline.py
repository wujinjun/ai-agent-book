import zipfile
from pathlib import Path

import scripts.build_pandoc as pandoc_pipeline
from scripts.build_pandoc import chrome_pdf_command, compose_book

ROOT = Path(__file__).parents[1]


def test_composed_book_has_ordered_chapters_projects_and_no_raw_mermaid(
    tmp_path: Path,
) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")
    text = output.read_text(encoding="utf-8")

    assert text.index("# 第1章 第1节：什么是大语言模型？") < text.index("# 第38章：技术选型指南")
    assert text.index("项目1：最小 AI Assistant") < text.index("项目10：企业级 Agent 平台")
    assert "```mermaid" not in text
    assert text.count("# 项目") >= 10
    assert "assets/diagrams/svg/" in text


def test_composed_book_contains_front_and_back_matter(tmp_path: Path) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")
    text = output.read_text(encoding="utf-8")

    assert "# 前言" in text
    assert "# 版权与使用说明" in text
    assert "# 版本与发行信息" in text
    assert "# 术语表" in text
    assert "# 参考资料" in text


def test_composed_book_rewrites_cross_document_links_and_local_images(
    tmp_path: Path,
) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")
    text = output.read_text(encoding="utf-8")

    assert '<span id="doc-part-01-foundations-ch01-what-is-llm"></span>' in text
    assert "](ch01-what-is-llm.md)" not in text
    assert "](../references.md#ref-" not in text
    assert "](references.md#ref-" not in text
    assert "](#ref-vaswani2017)" in text
    assert "docs/assets/training-deck-preview.png" in text


def test_composed_book_converts_mkdocs_admonitions_for_pandoc(tmp_path: Path) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")
    text = output.read_text(encoding="utf-8")

    assert '!!! warning "投资风险"' not in text
    assert "> **投资风险**" in text
    assert "> 项目 7 仅用于软件工程与信息整理教学" in text


def test_composed_book_uses_heading_sections_without_extra_page_breaks(
    tmp_path: Path,
) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")

    assert '<div class="page-break"></div>' not in output.read_text(encoding="utf-8")


def test_chrome_pdf_command_disables_browser_headers(tmp_path: Path) -> None:
    command = chrome_pdf_command(
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        tmp_path / "print.html",
        tmp_path / "book.pdf",
    )

    assert "--no-pdf-header-footer" in command
    assert "--print-to-pdf-no-header" not in command


def test_print_tables_repeat_headers_and_split_only_between_rows() -> None:
    css = (ROOT / "templates/pandoc/print.css").read_text(encoding="utf-8")

    assert "table { width: 100%; border-collapse: collapse; font-size: 8.5pt; }" in css
    assert "thead { display: table-header-group; }" in css
    assert "tr { break-inside: avoid-page; }" in css
    assert "th, td { padding: 3pt;" in css


def test_build_print_html_stages_relative_svg_sources(tmp_path: Path, monkeypatch) -> None:
    svg = tmp_path / "assets/diagrams/svg/demo.svg"
    svg.parent.mkdir(parents=True)
    svg.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")
    source = tmp_path / "output/intermediate/book.md"
    source.parent.mkdir(parents=True)
    source.write_text("# Demo", encoding="utf-8")

    def fake_run(command: list[str], *, timeout: int = 600) -> None:
        del timeout
        output = Path(command[command.index("--output") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            '<picture><source type="image/svg+xml" '
            'srcset="assets/diagrams/svg/demo.svg">'
            '<img src="data:image/png;base64,cG5n" alt="演示图"></picture>',
            encoding="utf-8",
        )

    monkeypatch.setattr(pandoc_pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pandoc_pipeline, "_run", fake_run)

    print_html = pandoc_pipeline.build_print_html("pandoc", source)

    assert (
        (print_html.parent / "assets/diagrams/svg/demo.svg")
        .read_text(encoding="utf-8")
        .startswith("<svg")
    )


def test_build_print_html_preserves_manual_chapter_numbering(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "assets/diagrams/svg").mkdir(parents=True)
    source = tmp_path / "output/intermediate/book.md"
    source.parent.mkdir(parents=True)
    source.write_text("# 第6章 Prompt Engineering", encoding="utf-8")
    captured: list[str] = []

    def fake_run(command: list[str], *, timeout: int = 600) -> None:
        del timeout
        captured.extend(command)
        output = Path(command[command.index("--output") + 1])
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text("<h1>第6章 Prompt Engineering</h1>", encoding="utf-8")

    monkeypatch.setattr(pandoc_pipeline, "ROOT", tmp_path)
    monkeypatch.setattr(pandoc_pipeline, "_run", fake_run)

    pandoc_pipeline.build_print_html("pandoc", source)

    assert "--number-sections" not in captured
    assert "--from=gfm+raw_html" in captured


def test_stage_offline_editions_copies_pdf_and_epub_into_site(
    tmp_path: Path,
) -> None:
    assert hasattr(pandoc_pipeline, "stage_offline_editions")
    pdf = tmp_path / "output/pdf/ai-agent-book-2026.pdf"
    epub = tmp_path / "output/epub/ai-agent-book-2026.epub"
    pdf.parent.mkdir(parents=True)
    epub.parent.mkdir(parents=True)
    pdf.write_bytes(b"pdf")
    epub.write_bytes(b"epub")

    outputs = pandoc_pipeline.stage_offline_editions(
        tmp_path / "output/html",
        pdf,
        epub,
    )

    assert [path.name for path in outputs] == [
        "ai-agent-book-2026.pdf",
        "ai-agent-book-2026.epub",
    ]
    assert outputs[0].read_bytes() == b"pdf"
    assert outputs[1].read_bytes() == b"epub"


def test_epub_postprocess_rewrites_cross_xhtml_fragment_links(tmp_path: Path) -> None:
    epub = tmp_path / "book.epub"
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "EPUB/content.opf",
            "<package><manifest></manifest></package>",
        )
        archive.writestr(
            "EPUB/text/ch001.xhtml",
            '<html><body><h1 id="source">源</h1>'
            '<a href="#target">目标</a><a href="#source">本页</a>'
            "</body></html>",
        )
        archive.writestr(
            "EPUB/text/ch002.xhtml",
            '<html><body><h1 id="target">目标</h1></body></html>',
        )

    pandoc_pipeline.inject_epub_svg_fallbacks(epub, tmp_path)

    with zipfile.ZipFile(epub) as archive:
        source = archive.read("EPUB/text/ch001.xhtml").decode("utf-8")
    assert 'href="ch002.xhtml#target"' in source
    assert 'href="#source"' in source
