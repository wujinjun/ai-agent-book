from pathlib import Path

import yaml

from ai_agent_book.book_manifest import _MkDocsNavigationLoader
from scripts.build_html import prepare_html_sources, write_build_config

ROOT = Path(__file__).parents[1]


def test_mkdocs_loads_reader_assets_and_custom_directory() -> None:
    config = yaml.load(
        (ROOT / "mkdocs.yml").read_text(encoding="utf-8"),
        Loader=_MkDocsNavigationLoader,
    )

    assert config["theme"]["custom_dir"] == "overrides"
    assert "assets/stylesheets/extra.css" in config["extra_css"]
    assert "assets/javascripts/reader.js" in config["extra_javascript"]
    assert "toc.follow" in config["theme"]["features"]
    assert "navigation.top" in config["theme"]["features"]


def test_reader_assets_define_responsive_layout_and_accessible_dialog() -> None:
    css = (ROOT / "docs/assets/stylesheets/extra.css").read_text(encoding="utf-8")
    javascript = (ROOT / "docs/assets/javascripts/reader.js").read_text(encoding="utf-8")

    assert "--book-content-width" in css
    assert "@media" in css
    assert "prefers-reduced-motion" in css
    assert "padding-inline: 0.9rem" in css
    assert ".md-typeset figure.book-diagram" in css
    assert ".book-diagram picture" in css
    assert "width: 100%" in css
    assert 'aria-label="关闭图形预览"' in javascript
    assert "Escape" in javascript


def test_html_source_preparation_replaces_mermaid_with_portable_picture(tmp_path: Path) -> None:
    prepared = prepare_html_sources(ROOT, tmp_path)
    chapter = prepared / "part-01-foundations/ch01-what-is-llm.md"
    source = chapter.read_text(encoding="utf-8")

    assert "```mermaid" not in source
    assert '<source type="image/svg+xml"' in source
    assert "../../assets/diagrams/svg/" in source
    assert (prepared / "assets/diagrams/manifest.json").is_file()
    project = prepared / "part-06-projects/project-01.md"
    assert project.is_file()
    assert "```mermaid" not in project.read_text(encoding="utf-8")


def test_temporary_mkdocs_config_adds_all_ten_project_pages(tmp_path: Path) -> None:
    prepared = prepare_html_sources(ROOT, tmp_path / "docs")
    config_path = write_build_config(ROOT, prepared, tmp_path / "mkdocs.yml")
    config = config_path.read_text(encoding="utf-8")

    assert config.count("part-06-projects/project-") == 10
    assert "项目1：最小 AI Assistant" in config
    assert "项目10：企业级 Agent 平台" in config
