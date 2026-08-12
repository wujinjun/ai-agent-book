import re
from pathlib import Path

import yaml

from scripts.audit_editorial import audit
from scripts.build_chapter_citations import build_blocks

ROOT = Path(__file__).parents[1]


def test_reference_catalog_is_formal_traceable_and_large_enough() -> None:
    references = yaml.safe_load((ROOT / "notes/references.yml").read_text(encoding="utf-8"))
    assert len(references) >= 100
    ids = [item["id"] for item in references]
    assert len(ids) == len(set(ids))
    assert all(item["url"].startswith("https://") for item in references)
    assert all(item["title"] and item["authors"] and item["publication"] for item in references)

    version_sensitive = [
        item
        for item in references
        if item["publication"] in {"Official Documentation", "Official OpenAI Documentation"}
    ]
    assert version_sensitive
    assert all(re.fullmatch(r"\d{4}-\d{2}-\d{2}", item["checked"]) for item in version_sensitive)


def test_all_chapters_have_current_generated_citation_blocks() -> None:
    outputs = build_blocks(ROOT)
    assert len(outputs) == 38
    for path, expected in outputs.items():
        assert path.read_text(encoding="utf-8") == expected
        assert expected.count("<!-- chapter-citations:start -->") == 1
        assert expected.count("../references.md#ref-") >= 3


def test_editorial_audit_passes_without_remote_images() -> None:
    report = audit(ROOT)
    assert report["chapters"] == 38
    assert report["references"] >= 100
    assert report["chapter_citations"] >= 114
    assert report["remote_images"] == 0
    assert report["issues"] == []


def test_editorial_audit_rejects_future_last_checked_date(tmp_path: Path) -> None:
    root = tmp_path
    chapter = root / "docs/part-01-foundations/ch01.md"
    chapter.parent.mkdir(parents=True)
    chapter.write_text("# 章节\n\n最后核对日期：2999-01-01。\n", encoding="utf-8")
    (root / "notes").mkdir()
    (root / "notes/references.yml").write_text("[]\n", encoding="utf-8")
    (root / "notes/chapter-citations.yml").write_text("chapters: {}\n", encoding="utf-8")

    report = audit(root)

    assert any(item["issue"] == "future_last_checked_date" for item in report["issues"])


def test_editorial_audit_rejects_unlabelled_project_code_fence(tmp_path: Path) -> None:
    root = tmp_path
    chapter = root / "docs/part-01-foundations/ch01.md"
    chapter.parent.mkdir(parents=True)
    chapter.write_text(
        "# 章节\n\n最后核对日期：2026-01-01。\n"
        "<!-- chapter-citations:start -->\n<!-- chapter-citations:end -->\n",
        encoding="utf-8",
    )
    project = root / "projects/01-demo/README.md"
    project.parent.mkdir(parents=True)
    project.write_text("# Demo\n\n```\npython main.py\n```\n", encoding="utf-8")
    (root / "notes").mkdir()
    (root / "notes/references.yml").write_text("[]\n", encoding="utf-8")
    (root / "notes/chapter-citations.yml").write_text("chapters: {}\n", encoding="utf-8")

    report = audit(root)

    assert {
        "path": "projects/01-demo/README.md",
        "issue": "unlabelled_code_fence:3",
    } in report["issues"]


def test_dual_license_and_commercial_boundary_are_explicit() -> None:
    license_notice = (ROOT / "LICENSE").read_text(encoding="utf-8")
    code_license = (ROOT / "LICENSE-CODE").read_text(encoding="utf-8")
    commercial = (ROOT / "COMMERCIAL_LICENSE.md").read_text(encoding="utf-8")
    cla = (ROOT / "CONTRIBUTOR_LICENSE_AGREEMENT.md").read_text(encoding="utf-8")
    rights = (ROOT / "notes/rights-and-permissions.md").read_text(encoding="utf-8")

    assert "CC BY-NC-SA 4.0" in license_notice
    assert "MIT License" in license_notice + code_license
    assert "单独书面许可" in license_notice + commercial
    assert "商业纸书" in cla
    assert "商标" in rights and "第三方" in rights and "字体" in rights
