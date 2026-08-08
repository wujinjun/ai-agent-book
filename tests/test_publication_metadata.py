from pathlib import Path

from ai_agent_book.publication_metadata import generate_supporting_pages

ROOT = Path(__file__).parents[1]


def test_generated_supporting_pages_cover_terms_references_and_index(tmp_path: Path) -> None:
    outputs = generate_supporting_pages(ROOT, tmp_path)

    glossary = outputs["glossary"].read_text(encoding="utf-8")
    references = outputs["references"].read_text(encoding="utf-8")
    index = outputs["index"].read_text(encoding="utf-8")

    assert glossary.count("\n| ") >= 30
    assert "LangGraph" in glossary
    assert "Prompt Injection" in glossary
    assert "vaswani2017" in references
    assert references.count('<span id="ref-') >= 100
    assert "https://" in references
    assert references.count("\n1.") == 1
    assert "part-01-foundations/ch01-what-is-llm.md" in index
    assert "part-05-engineering/ch30-security.md" in index
    assert "此文件由" in glossary + references + index
    assert "| — | 0 |" not in index
    assert "TODO" not in glossary + references + index


def test_checked_in_supporting_pages_match_generator(tmp_path: Path) -> None:
    outputs = generate_supporting_pages(ROOT, tmp_path)

    assert outputs["glossary"].read_text(encoding="utf-8") == (
        ROOT / "docs/glossary.md"
    ).read_text(encoding="utf-8")
    assert outputs["references"].read_text(encoding="utf-8") == (
        ROOT / "docs/references.md"
    ).read_text(encoding="utf-8")
    assert outputs["index"].read_text(encoding="utf-8") == (
        ROOT / "docs/book-index.md"
    ).read_text(encoding="utf-8")
