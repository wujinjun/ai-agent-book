from pathlib import Path
from zipfile import ZipFile

from pypdf import PdfReader

from ai_agent_book.publications import BookChapter, build_epub, build_pdf


def test_pdf_contains_title_and_page_number(tmp_path: Path) -> None:
    output = tmp_path / "book.pdf"
    build_pdf(
        [BookChapter(title="测试章节", markdown="# 测试章节\n\n这是正文。")],
        output,
        book_title="AI Agent 教材测试",
    )

    reader = PdfReader(output)
    assert len(reader.pages) >= 2
    text = "\n".join(page.extract_text() or "" for page in reader.pages)
    assert "AI Agent" in text
    assert "测试章节" in text


def test_pdf_labels_mermaid_as_a_renderable_diagram_source(tmp_path: Path) -> None:
    output = tmp_path / "diagram.pdf"
    build_pdf(
        [BookChapter(title="图示章", markdown="# 图示章\n```mermaid\nflowchart LR\nA --> B\n```")],
        output,
        book_title="图示测试",
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "架构图" in text
    assert "A --> B" in text


def test_pdf_preserves_underscores_in_inline_code_paths(tmp_path: Path) -> None:
    output = tmp_path / "paths.pdf"
    build_pdf(
        [BookChapter(title="路径", markdown="# 路径\n代码：`tests/test_agent_app.py`。")],
        output,
        book_title="路径测试",
    )
    text = "\n".join(page.extract_text() or "" for page in PdfReader(output).pages)
    assert "tests/test_agent_app.py" in text


def test_epub_has_required_container_and_navigation(tmp_path: Path) -> None:
    output = tmp_path / "book.epub"
    build_epub(
        [BookChapter(title="第一章", markdown="# 第一章\n\n正文。")],
        output,
        book_title="测试书",
    )

    with ZipFile(output) as archive:
        names = archive.namelist()
        assert names[0] == "mimetype"
        assert archive.read("mimetype") == b"application/epub+zip"
        assert "META-INF/container.xml" in names
        assert any(name.endswith("nav.xhtml") for name in names)
