from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_every_chapter_has_a_diagram_and_balanced_code_fences() -> None:
    chapters = sorted((ROOT / "docs").glob("part-*/ch*.md"))
    assert len(chapters) == 38
    for chapter in chapters:
        content = chapter.read_text(encoding="utf-8")
        assert "```mermaid" in content, f"missing diagram: {chapter}"
        assert content.count("```") % 2 == 0, f"unbalanced code fence: {chapter}"
        opening_languages: list[str] = []
        inside_fence = False
        for line in content.splitlines():
            if line.startswith("```"):
                if not inside_fence:
                    opening_languages.append(line.removeprefix("```").strip())
                inside_fence = not inside_fence
        assert all(opening_languages), f"unlabelled code fence: {chapter}"
        assert any(language != "mermaid" for language in opening_languages), (
            f"chapter has a diagram but no rendered code/config example: {chapter}"
        )


def test_project_readmes_render_diagrams_and_commands() -> None:
    readmes = sorted((ROOT / "projects").glob("[0-9][0-9]-*/README.md"))
    assert len(readmes) == 10
    for readme in readmes:
        content = readme.read_text(encoding="utf-8")
        assert "```mermaid" in content
        assert "```bash" in content
        assert "```text" in content
        assert "## 目录、配置与扩展" in content
        assert "\\`" not in content, f"escaped fences will not render: {readme}"
