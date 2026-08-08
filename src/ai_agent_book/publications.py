"""生成测试用轻量 PDF；正式 PDF/EPUB 始终使用 Pandoc 出版管线。"""

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
