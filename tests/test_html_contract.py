from pathlib import Path

import yaml

from ai_agent_book.book_manifest import _MkDocsNavigationLoader

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
    assert 'aria-label="关闭图形预览"' in javascript
    assert "Escape" in javascript
