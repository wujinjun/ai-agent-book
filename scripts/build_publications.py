from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "src"))

from ai_agent_book.publications import BookChapter, build_epub, build_pdf  # noqa: E402


def chapter_number(path: Path) -> int:
    match = re.search(r"ch(\d+)", path.name)
    if match is None:
        raise ValueError(f"无法从文件名读取章节号: {path}")
    return int(match.group(1))


def collect_chapters() -> list[BookChapter]:
    textbook = sorted(ROOT.glob("docs/part-*/ch*.md"), key=chapter_number)
    if len(textbook) != 38:
        raise RuntimeError(f"发布要求 38 章，当前找到 {len(textbook)} 章")
    before_projects = [path for path in textbook if chapter_number(path) <= 31]
    after_projects = [path for path in textbook if chapter_number(path) >= 32]
    project_paths = sorted(ROOT.glob("projects/[0-9][0-9]-*/README.md"))
    if len(project_paths) != 10:
        raise RuntimeError(f"发布要求 10 个项目，当前找到 {len(project_paths)} 个")
    paths = [*before_projects, *project_paths, *after_projects]
    chapters: list[BookChapter] = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        title = next(
            (line.removeprefix("# ") for line in source.splitlines() if line.startswith("# ")),
            path.stem,
        )
        chapters.append(BookChapter(title=title, markdown=source))
    return chapters


def main() -> None:
    parser = argparse.ArgumentParser(description="生成教材 PDF 与 EPUB")
    parser.add_argument("--format", choices=("all", "pdf", "epub"), default="all")
    args = parser.parse_args()
    chapters = collect_chapters()
    title = "AI Agent 从零到实战：原理、工程与项目（2026版）"
    if args.format in {"all", "pdf"}:
        build_pdf(chapters, ROOT / "output/pdf/ai-agent-book-2026.pdf", book_title=title)
    if args.format in {"all", "epub"}:
        build_epub(chapters, ROOT / "output/epub/ai-agent-book-2026.epub", book_title=title)


if __name__ == "__main__":
    main()
