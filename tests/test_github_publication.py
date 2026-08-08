from pathlib import Path

import yaml

ROOT = Path(__file__).parents[1]


def test_publish_workflow_deploys_pages_and_versioned_downloads() -> None:
    workflow_path = ROOT / ".github/workflows/publish.yml"
    assert workflow_path.is_file()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    source = workflow_path.read_text(encoding="utf-8")

    assert "main" in workflow[True]["push"]["branches"]
    assert "v*" in workflow[True]["push"]["tags"]
    assert "actions/deploy-pages@v4" in source
    assert "output/html/downloads" in source
    assert "ai-agent-book-2026.pdf" in source
    assert "ai-agent-book-2026.epub" in source
    assert "scripts/package_release.py" in source
    assert "SHA256SUMS" not in source  # 文件名由打包脚本统一生成，避免工作流漂移
    assert "publication/release/*" in source
    assert '--notes-file "$notes_file"' in source
    assert 'gh release create "$GITHUB_REF_NAME"' in source
    assert "GH_REPO: ${{ github.repository }}" in source
    assert "final-gate:" in source
    assert "needs: [build, final-gate]" in source
    assert '--release-commit "$GITHUB_SHA"' not in source
    assert "audit_final_acceptance.py" in source
    assert "--require-repository-complete" in source


def test_homepage_links_published_offline_editions() -> None:
    homepage = (ROOT / "docs/index.md").read_text(encoding="utf-8")

    assert 'href="downloads/ai-agent-book-2026.pdf"' in homepage
    assert 'href="downloads/ai-agent-book-2026.epub"' in homepage
