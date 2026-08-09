import json
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).parents[1]


def test_pilot_infographic_assets_are_tracked_and_publishable() -> None:
    manifest = json.loads(
        (ROOT / "assets/infographics/manifest.json").read_text(encoding="utf-8")
    )
    assert len(manifest) >= 1
    record = next(
        item
        for item in manifest
        if item["semantic_id"] == "llm-product-agent-system-infographic"
    )
    assert len(record["source_sha256"]) == 64
    assert len(record["svg_sha256"]) == 64
    assert len(record["png_sha256"]) == 64

    svg = ROOT / record["svg_asset"]
    png = ROOT / record["png_asset"]
    assert svg.is_file()
    assert png.is_file()
    assert "<title" in svg.read_text(encoding="utf-8")
    assert "<desc" in svg.read_text(encoding="utf-8")
    with Image.open(png) as image:
        assert image.size == (1536, 1024)


def test_chapter_one_integrates_infographic_with_explanation() -> None:
    chapter = (ROOT / "docs/part-01-foundations/ch01-what-is-llm.md").read_text(
        encoding="utf-8"
    )
    assert "llm-product-agent-system-infographic-2x.png" in chapter
    assert "图 1-A" in chapter
    assert "信息图帮助读者建立全局心智模型" in chapter


def test_rag_pilot_integrates_infographic_and_evaluation_boundary() -> None:
    chapter = (ROOT / "docs/part-03-rag-and-memory/ch13-rag.md").read_text(
        encoding="utf-8"
    )
    assert "rag-evidence-pipeline-infographic-2x.png" in chapter
    assert "图 13-A" in chapter
    assert "权限过滤属于检索契约" in chapter
    manifest = json.loads(
        (ROOT / "assets/infographics/manifest.json").read_text(encoding="utf-8")
    )
    record = next(
        item for item in manifest if item["semantic_id"] == "rag-evidence-pipeline-infographic"
    )
    assert (ROOT / record["svg_asset"]).is_file()
    assert (ROOT / record["png_asset"]).is_file()


def test_enterprise_architecture_pilot_integrates_layer_boundaries() -> None:
    chapter = (ROOT / "docs/part-07-advanced/ch36-architecture.md").read_text(
        encoding="utf-8"
    )
    assert "enterprise-agent-platform-infographic-2x.png" in chapter
    assert "图 36-A" in chapter
    assert "不要求每层独立部署成微服务" in chapter
    manifest = json.loads(
        (ROOT / "assets/infographics/manifest.json").read_text(encoding="utf-8")
    )
    record = next(
        item
        for item in manifest
        if item["semantic_id"] == "enterprise-agent-platform-infographic"
    )
    assert (ROOT / record["svg_asset"]).is_file()
    assert (ROOT / record["png_asset"]).is_file()
