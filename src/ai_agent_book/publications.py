"""从同一 Markdown 章节集合生成中文 PDF 与 EPUB。"""

from __future__ import annotations

import html
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BookChapter:
    title: str
    markdown: str


def _plain_blocks(markdown_text: str) -> list[tuple[str, str]]:
    blocks: list[tuple[str, str]] = []
    in_code = False
    code_language = ""
    buffer: list[str] = []
    for raw in markdown_text.splitlines():
        line = raw.rstrip()
        if line.startswith("```"):
            if in_code:
                kind = "diagram" if code_language == "mermaid" else "code"
                blocks.append((kind, "\n".join(buffer)))
                buffer = []
                code_language = ""
            else:
                code_language = line.removeprefix("```").strip()
            in_code = not in_code
            continue
        if in_code:
            buffer.append(line)
        elif line.startswith("#"):
            level = len(line) - len(line.lstrip("#"))
            blocks.append((f"h{min(level, 3)}", line[level:].strip()))
        elif line.lstrip().startswith("|") and line.rstrip().endswith("|"):
            cells = [cell.strip() for cell in line.strip().strip("|").split("|")]
            if not all(re.fullmatch(r":?-{2,}:?", cell) for cell in cells):
                blocks.append(("body", "  ·  ".join(cells)))
        elif line.strip():
            cleaned = re.sub(r"!?\[([^]]*)\]\([^)]+\)", r"\1", line)
            # 保留下划线：它经常属于 Python 标识符和文件路径，而不是强调语法。
            cleaned = re.sub(r"[*`>]", "", cleaned).strip()
            blocks.append(("body", cleaned))
    return blocks


def build_pdf(chapters: list[BookChapter], output: Path, *, book_title: str) -> None:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.pdfbase.cidfonts import UnicodeCIDFont
    from reportlab.pdfbase.pdfmetrics import registerFont
    from reportlab.platypus import PageBreak, Paragraph, Preformatted, SimpleDocTemplate, Spacer

    if not chapters:
        raise ValueError("至少需要一个章节")
    output.parent.mkdir(parents=True, exist_ok=True)
    registerFont(UnicodeCIDFont("STSong-Light"))
    base = getSampleStyleSheet()
    body = ParagraphStyle(
        "ChineseBody",
        parent=base["BodyText"],
        fontName="STSong-Light",
        fontSize=10.5,
        leading=17,
        spaceAfter=6,
    )
    h1 = ParagraphStyle(
        "ChineseH1", parent=body, fontSize=20, leading=28, spaceBefore=10, spaceAfter=12
    )
    h2 = ParagraphStyle(
        "ChineseH2", parent=body, fontSize=15, leading=22, spaceBefore=9, spaceAfter=7
    )
    title_style = ParagraphStyle(
        "BookTitle",
        parent=h1,
        fontSize=22,
        leading=31,
        alignment=TA_CENTER,
        textColor=colors.HexColor("#243B6B"),
    )
    code = ParagraphStyle(
        "Code",
        parent=body,
        fontSize=8.2,
        leading=11,
        leftIndent=8,
        backColor=colors.HexColor("#F3F5F7"),
    )

    def footer(canvas: Any, document: Any) -> None:
        canvas.saveState()
        canvas.setFillColor(colors.white)
        canvas.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        canvas.restoreState()
        canvas.saveState()
        canvas.setFont("STSong-Light", 8)
        canvas.setFillColor(colors.grey)
        canvas.drawCentredString(
            A4[0] / 2, 12 * mm, f"AI Agent 从零到实战（2026版）  ·  {document.page}"
        )
        canvas.restoreState()

    story: list[Any] = [
        Spacer(1, 55 * mm),
        Paragraph(html.escape(book_title), title_style),
        Spacer(1, 8 * mm),
        Paragraph(
            "2026 版 · 软件工程师教材", ParagraphStyle("Subtitle", parent=body, alignment=TA_CENTER)
        ),
        PageBreak(),
    ]
    story.append(Paragraph("目录", h1))
    for index, chapter in enumerate(chapters, 1):
        story.append(Paragraph(f"{index}. {html.escape(chapter.title)}", body))
    story.append(PageBreak())
    for index, chapter in enumerate(chapters):
        for kind, text in _plain_blocks(chapter.markdown):
            escaped = html.escape(text).replace("\n", "<br/>")
            if kind == "h1":
                story.append(Paragraph(escaped, h1))
            elif kind in {"h2", "h3"}:
                story.append(Paragraph(escaped, h2))
            elif kind == "code":
                story.append(Preformatted(text, code, maxLineLength=92))
            elif kind == "diagram":
                story.append(Paragraph("架构图（Mermaid 图示源码）", h2))
                story.append(Preformatted(text, code, maxLineLength=92))
            else:
                story.append(Paragraph(escaped, body))
        if index < len(chapters) - 1:
            story.append(PageBreak())
    document = SimpleDocTemplate(
        str(output),
        pagesize=A4,
        leftMargin=22 * mm,
        rightMargin=22 * mm,
        topMargin=20 * mm,
        bottomMargin=20 * mm,
        title=book_title,
        author="AI Agent Book contributors",
    )
    document.build(story, onFirstPage=footer, onLaterPages=footer)


def build_epub(chapters: list[BookChapter], output: Path, *, book_title: str) -> None:
    from ebooklib import epub
    from markdown import markdown

    if not chapters:
        raise ValueError("至少需要一个章节")
    output.parent.mkdir(parents=True, exist_ok=True)
    book = epub.EpubBook()
    book.set_identifier("ai-agent-book-2026")
    book.set_title(book_title)
    book.set_language("zh-CN")
    book.add_author("AI Agent Book contributors")
    items = []
    for index, chapter in enumerate(chapters, 1):
        item = epub.EpubHtml(
            title=chapter.title, file_name=f"chapter-{index:02d}.xhtml", lang="zh-CN"
        )
        epub_source = chapter.markdown.replace(
            "```mermaid", "**架构图（Mermaid 图示源码）**\n\n```text"
        )
        item.content = markdown(epub_source, extensions=["fenced_code", "tables"])
        book.add_item(item)
        items.append(item)
    book.toc = tuple(items)
    book.spine = ["nav", *items]
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    style = (
        "body{font-family:serif;line-height:1.75;margin:5%;}"
        "code,pre{font-family:monospace;background:#f3f5f7;}"
        "table{border-collapse:collapse;}"
        "td,th{border:1px solid #aaa;padding:.35em;}"
    )
    css = epub.EpubItem(
        uid="style", file_name="style/book.css", media_type="text/css", content=style
    )
    book.add_item(css)
    for item in items:
        item.add_item(css)
    epub.write_epub(str(output), book, {})
