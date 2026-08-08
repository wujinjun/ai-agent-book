import zipfile
from pathlib import Path

from scripts.audit_distribution_assets import (
    audit_dependencies,
    audit_epub,
    audit_pptx,
    audit_source_assets,
)

ROOT = Path(__file__).parents[1]


def test_distribution_fonts_have_fixed_checksums_licenses_and_print_css_links() -> None:
    report, hard_issues, _ = audit_source_assets(ROOT / "notes/asset-provenance.yml")

    assert hard_issues == []
    fonts = report["distribution_fonts"]
    assert len(fonts) == 5
    assert {font["license"] for font in fonts} == {"SIL-OFL-1.1"}
    assert all(font["sha256"] == font["computed_sha256"] for font in fonts)
    assert all((ROOT / font["license_file"]).is_file() for font in fonts)

    dependencies, hard_issues, manual = audit_dependencies(ROOT / "pyproject.toml")
    assert hard_issues == []
    records = {record["name"].lower(): record for record in dependencies}
    assert records["langgraph"]["license_expression"] == "MIT"
    assert records["psycopg"]["license_expression"] == "LGPL-3.0-only"
    assert records["pytest-asyncio"]["license_expression"] == "Apache-2.0"
    for package in ("langgraph", "psycopg", "pytest-asyncio"):
        assert not any(f"Dependency {package} has no concise" in item for item in manual)


def test_epub_runtime_resource_audit_distinguishes_links_from_dependencies(
    tmp_path: Path,
) -> None:
    epub = tmp_path / "sample.epub"
    with zipfile.ZipFile(epub, "w") as archive:
        archive.writestr(
            "EPUB/chapter.xhtml",
            """<html xmlns="http://www.w3.org/1999/xhtml"><body>
            <a href="https://example.com/reference">reference</a>
            <img src="https://example.com/tracker.png" />
            </body></html>""",
        )

    report, hard_issues, _ = audit_epub(epub)

    assert report["external_hyperlinks"] == 1
    assert report["external_runtime_resources"] == [
        "EPUB/chapter.xhtml: img.src=https://example.com/tracker.png"
    ]
    assert hard_issues == [
        "EPUB has external runtime resources: EPUB/chapter.xhtml: "
        "img.src=https://example.com/tracker.png"
    ]


def test_print_css_does_not_fall_back_to_untracked_system_fonts() -> None:
    css = (ROOT / "templates/pandoc/print.css").read_text(encoding="utf-8")

    assert 'font-family: "Book Noto Sans SC", sans-serif' in css
    assert 'font-family: "Book Source Code Pro", "Book Noto Sans SC", monospace' in css
    for forbidden in ("Menlo", "Monaco", "PingFang", "Hiragino"):
        assert forbidden not in css


def test_training_pptx_visible_text_uses_bundled_ofl_font() -> None:
    report, hard_issues, _ = audit_pptx(
        ROOT / "training/slides/ai-agent-engineering-training.pptx"
    )

    assert hard_issues == []
    assert report["slides"] == 16
    assert report["explicit_visible_run_typefaces"] == ["Noto Sans SC"]
    assert report["unapproved_explicit_typefaces"] == []
    assert report["external_runtime_resources"] == []
