from pathlib import Path

from ai_agent_book.publication_audit import audit_html


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
