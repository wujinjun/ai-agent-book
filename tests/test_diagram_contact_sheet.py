import json
from pathlib import Path

from PIL import Image

from ai_agent_book.contact_sheet import _font, build_contact_sheets


def test_contact_sheet_font_supports_chinese_titles() -> None:
    font = _font(24, bold=True)

    assert bytes(font.getmask("中")) != bytes(font.getmask(chr(0x10FFFF)))


def test_contact_sheet_paginates_and_indexes_every_diagram_once(tmp_path: Path) -> None:
    asset_root = tmp_path / "diagrams"
    png_root = asset_root / "png"
    png_root.mkdir(parents=True)
    manifest: list[dict[str, object]] = []
    for index in range(21):
        filename = f"diagram-{index:02d}.png"
        Image.new("RGB", (320 + index, 180), "white").save(png_root / filename)
        manifest.append(
            {
                "source_path": f"docs/ch{index:02d}.md",
                "index": 1,
                "semantic_id": f"diagram-{index:02d}",
                "title": f"Diagram {index:02d}",
                "png_path": f"png/{filename}",
            }
        )
    manifest_path = asset_root / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    pages, index_path = build_contact_sheets(
        manifest_path,
        tmp_path / "contact-sheets",
        columns=4,
        rows=5,
    )

    assert [page.name for page in pages] == [
        "diagram-contact-sheet-01.png",
        "diagram-contact-sheet-02.png",
    ]
    assert all(page.is_file() and page.stat().st_size > 0 for page in pages)
    payload = json.loads(index_path.read_text(encoding="utf-8"))
    assert payload["page_count"] == 2
    assert payload["diagram_count"] == 21
    assert {entry["semantic_id"] for entry in payload["entries"]} == {
        f"diagram-{index:02d}" for index in range(21)
    }
    assert len(payload["entries"]) == len(
        {(entry["page"], entry["slot"]) for entry in payload["entries"]}
    )
