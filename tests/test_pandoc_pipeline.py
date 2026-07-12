from pathlib import Path

from scripts.build_pandoc import chrome_pdf_command, compose_book

ROOT = Path(__file__).parents[1]


def test_composed_book_has_ordered_chapters_projects_and_no_raw_mermaid(
    tmp_path: Path,
) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")
    text = output.read_text(encoding="utf-8")

    assert text.index("什么是大语言模型") < text.index("技术选型")
    assert text.index("项目1：最小 AI Assistant") < text.index("项目10：企业级 Agent 平台")
    assert "```mermaid" not in text
    assert text.count("# 项目") >= 10
    assert "assets/diagrams/svg/" in text


def test_composed_book_contains_front_and_back_matter(tmp_path: Path) -> None:
    output = compose_book(ROOT, tmp_path / "book.md")
    text = output.read_text(encoding="utf-8")

    assert "# 前言" in text
    assert "# 术语表" in text
    assert "# 参考资料" in text


def test_chrome_pdf_command_disables_browser_headers(tmp_path: Path) -> None:
    command = chrome_pdf_command(
        Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
        tmp_path / "print.html",
        tmp_path / "book.pdf",
    )

    assert "--no-pdf-header-footer" in command
    assert "--print-to-pdf-no-header" not in command
