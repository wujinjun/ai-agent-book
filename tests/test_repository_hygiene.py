from pathlib import Path

from scripts.audit_repository_hygiene import audit_local_markdown_links, audit_paths
from scripts.check_secrets import scan_text


def test_hygiene_rejects_generated_cache_and_environment_files() -> None:
    issues = audit_paths(
        [
            Path("src/pkg/__pycache__/module.pyc"),
            Path("output/pdf/book.pdf"),
            Path("examples/demo/.env"),
            Path("docs/index.md"),
        ]
    )

    assert len(issues) == 3
    assert not audit_paths([Path("examples/demo/.env.example"), Path("docs/index.md")])


def test_secret_scanner_reports_high_confidence_signatures_without_echoing_value() -> None:
    secret = "s" + "k-" + "A" * 32
    findings = scan_text(Path("demo.py"), f'KEY = "{secret}"\n')

    assert len(findings) == 1
    assert findings[0].kind == "OpenAI-style key"
    assert secret not in repr(findings[0])


def test_local_markdown_link_audit_covers_root_readme_and_images(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/guide.md").write_text("# Guide", encoding="utf-8")
    (tmp_path / "README.md").write_text(
        "[good](docs/guide.md)\n![missing](docs/missing.png)\n",
        encoding="utf-8",
    )

    issues = audit_local_markdown_links(tmp_path, [Path("README.md"), Path("docs/guide.md")])

    assert issues == ["broken local link: README.md:2 -> docs/missing.png"]
