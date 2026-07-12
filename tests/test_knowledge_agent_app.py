from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile

import pytest
from reportlab.pdfbase.cidfonts import UnicodeCIDFont
from reportlab.pdfbase.pdfmetrics import registerFont
from reportlab.pdfgen.canvas import Canvas

from ai_agent_book.apps.knowledge_agent import (
    DocumentParser,
    KnowledgeBase,
    PgVectorKnowledgeRepository,
    evaluate_retrieval,
)


def _write_office(path: Path, member: str, text: str) -> None:
    xml = f'<root xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main"><a:t>{text}</a:t></root>'
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(member, xml)


def test_parser_imports_markdown_pdf_word_and_powerpoint(tmp_path: Path) -> None:
    markdown = tmp_path / "guide.md"
    markdown.write_text("Agent Runtime 管理工具循环。", encoding="utf-8")
    docx = tmp_path / "policy.docx"
    _write_office(docx, "word/document.xml", "Word 制度内容")
    pptx = tmp_path / "slides.pptx"
    _write_office(pptx, "ppt/slides/slide1.xml", "PPT 架构内容")
    pdf = tmp_path / "paper.pdf"
    registerFont(UnicodeCIDFont("STSong-Light"))
    canvas = Canvas(str(pdf))
    canvas.setFont("STSong-Light", 12)
    canvas.drawString(72, 720, "PDF 检索内容")
    canvas.save()

    parser = DocumentParser()
    parsed = [parser.parse(path) for path in (markdown, docx, pptx, pdf)]

    assert "Agent Runtime" in parsed[0][0].text
    assert "Word" in parsed[1][0].text
    assert "PPT" in parsed[2][0].text
    assert "PDF" in parsed[3][0].text


def test_knowledge_base_chunks_retrieves_reranks_and_cites(tmp_path: Path) -> None:
    source = tmp_path / "runtime.md"
    source.write_text(
        "Agent Runtime 保存运行状态并执行工具循环。\n\nRAG 通过检索补充外部证据。",
        encoding="utf-8",
    )
    kb = KnowledgeBase(chunk_size=24, overlap=6)
    chunk_ids = kb.ingest(source, tenant_id="tenant-a")

    answer = kb.answer("谁保存运行状态？", tenant_id="tenant-a", top_k=3)

    assert chunk_ids
    assert "Agent Runtime" in answer.text
    assert answer.citations[0].source.endswith("runtime.md")
    assert answer.citations[0].chunk_id in chunk_ids
    assert kb.answer("谁保存状态？", tenant_id="tenant-b").citations == []


def test_retrieval_evaluation_computes_recall_and_mrr(tmp_path: Path) -> None:
    source = tmp_path / "memory.md"
    source.write_text("长期记忆需要写入策略与遗忘策略。", encoding="utf-8")
    kb = KnowledgeBase()
    expected = kb.ingest(source, tenant_id="t")[0]
    metrics = evaluate_retrieval(kb, [("长期记忆有什么策略？", expected)], tenant_id="t")
    assert metrics.recall_at_k == 1.0
    assert metrics.mrr == 1.0


def test_pgvector_repository_rejects_embedding_dimension_mismatch() -> None:
    repository = PgVectorKnowledgeRepository("postgresql://unused")
    with pytest.raises(ValueError, match="128 dimensions"):
        repository._vector_literal([0.0] * 127)
