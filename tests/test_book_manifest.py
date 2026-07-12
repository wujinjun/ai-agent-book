from pathlib import Path

import pytest

from ai_agent_book.book_manifest import load_book_entries

ROOT = Path(__file__).parents[1]


def test_manifest_uses_mkdocs_navigation_order() -> None:
    entries = load_book_entries(ROOT / "mkdocs.yml")

    paths = [entry.path.as_posix() for entry in entries]

    assert paths[0] == "docs/index.md"
    assert "docs/part-01-foundations/ch01-what-is-llm.md" in paths
    assert "docs/part-07-advanced/ch38-selection-guide.md" in paths
    assert paths.index("docs/part-01-foundations/ch01-what-is-llm.md") < paths.index(
        "docs/part-07-advanced/ch38-selection-guide.md"
    )
    assert len(paths) == len(set(paths))


def test_manifest_rejects_duplicate_paths(tmp_path: Path) -> None:
    config = tmp_path / "mkdocs.yml"
    config.write_text(
        "docs_dir: docs\nnav:\n  - 首页: index.md\n  - 再次首页: index.md\n",
        encoding="utf-8",
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/index.md").write_text("# 首页\n", encoding="utf-8")

    with pytest.raises(ValueError, match="duplicate navigation path"):
        load_book_entries(config)
