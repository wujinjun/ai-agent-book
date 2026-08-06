import re
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_first_lesson_has_required_sections_and_substantial_length() -> None:
    lesson = (ROOT / "docs/part-01-foundations/ch01-what-is-llm.md").read_text(encoding="utf-8")
    required = [
        "本节学习目标",
        "AI、机器学习与深度学习",
        "下一个 Token 预测",
        "随机鹦鹉",
        "ChatGPT 与 LLM",
        "AI Agent 与 LLM",
        "```mermaid",
        "常见误区",
        "练习题",
        "参考资料",
    ]
    assert all(title in lesson for title in required)
    assert len(lesson) >= 5_000


def test_repository_contains_no_real_env_file() -> None:
    assert not (ROOT / ".env").exists()
    example = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OPENAI_API_KEY=\n" in example


def test_local_markdown_links_point_to_existing_files() -> None:
    missing: list[str] = []
    for document in (ROOT / "docs").rglob("*.md"):
        content = document.read_text(encoding="utf-8")
        for target in re.findall(r"\[[^]]+\]\(([^)]+\.md)(?:#[^)]+)?\)", content):
            resolved = (document.parent / target).resolve()
            if not resolved.is_file():
                missing.append(f"{document.relative_to(ROOT)} -> {target}")
    assert missing == []


def test_chapter_code_paths_exist() -> None:
    missing: list[str] = []
    pattern = re.compile(r"`((?:examples|projects|src)/[^` ]+)`")
    for chapter in sorted((ROOT / "docs").glob("part-*/ch*.md")):
        for target in pattern.findall(chapter.read_text(encoding="utf-8")):
            normalized = target.removesuffix("/")
            if not (ROOT / normalized).exists():
                missing.append(f"{chapter.relative_to(ROOT)} -> {target}")
    assert missing == []


def test_completion_matrix_covers_book_and_projects() -> None:
    matrix_path = ROOT / "notes/completion-matrix.md"
    assert matrix_path.is_file()
    matrix = matrix_path.read_text(encoding="utf-8")

    chapter_rows = re.findall(r"^\| 第(?:[1-9]|[12]\d|3[0-8])章 \|", matrix, re.MULTILINE)
    project_rows = re.findall(r"^\| 项目(?:[1-9]|10) \|", matrix, re.MULTILINE)

    assert len(chapter_rows) == 38
    assert len(project_rows) == 10
    for state in (
        "publishable_draft",
        "inline_only",
        "installed_and_tested",
        "vertical_slice",
        "production_reference",
    ):
        assert f"`{state}`" in matrix


def test_all_chapters_meet_the_publishable_content_contract() -> None:
    chapters = sorted((ROOT / "docs").glob("part-*/ch*.md"))
    assert len(chapters) == 38
    required_concepts = (
        "学习目标",
        "前置知识",
        "核心",
        "mermaid",
        "示例",
        "误区",
        "调试",
        "安全",
        "总结",
        "练习",
        "面试",
        "延伸阅读",
        "代码目录",
    )
    failures: list[str] = []
    for chapter in chapters:
        source = chapter.read_text(encoding="utf-8")
        missing = [concept for concept in required_concepts if concept not in source]
        if len(source) < 2_500 or missing:
            failures.append(
                f"{chapter.relative_to(ROOT)}: chars={len(source)}, missing={','.join(missing)}"
            )
    assert failures == []
