"""Build paginated visual-review contact sheets from the diagram manifest."""

from __future__ import annotations

import json
import textwrap
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageFont, ImageOps

PAGE_WIDTH = 2000
PAGE_HEIGHT = 2800
PAGE_MARGIN = 56
HEADER_HEIGHT = 104
BACKGROUND = "#F3F0E8"
CARD = "#FFFFFF"
INK = "#172033"
MUTED = "#5C6472"
ACCENT = "#246B68"
PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    bundled = PROJECT_ROOT / "assets/fonts/noto-sans-sc" / (
        "NotoSansSC-Bold.otf" if bold else "NotoSansSC-Regular.otf"
    )
    if bundled.is_file():
        return ImageFont.truetype(str(bundled), size=size)

    candidates = (
        (Path("/System/Library/Fonts/Hiragino Sans GB.ttc"), 0),
        (Path("/System/Library/Fonts/STHeiti Light.ttc"), 1),
        (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), 0),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"), 0),
    )
    bold_candidates = (
        (Path("/System/Library/Fonts/Hiragino Sans GB.ttc"), 2),
        (Path("/System/Library/Fonts/STHeiti Medium.ttc"), 1),
        (Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"), 0),
        (Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"), 0),
    )
    for path, index in bold_candidates if bold else candidates:
        if path.is_file():
            return ImageFont.truetype(str(path), size=size, index=index)
    return ImageFont.load_default()


def _wrapped(value: str, width: int) -> str:
    return "\n".join(textwrap.wrap(value, width=width, break_long_words=True)[:2])


def build_contact_sheets(
    manifest_path: Path,
    output_dir: Path,
    *,
    columns: int = 4,
    rows: int = 5,
) -> tuple[list[Path], Path]:
    """Render every manifest entry exactly once and write a machine-checkable index."""

    if columns < 1 or rows < 1:
        raise ValueError("columns and rows must be positive")
    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("diagram manifest must be a list")
    entries = [entry for entry in raw if isinstance(entry, dict)]
    if len(entries) != len(raw):
        raise ValueError("diagram manifest entries must be objects")

    output_dir.mkdir(parents=True, exist_ok=True)
    asset_root = manifest_path.parent
    per_page = columns * rows
    page_count = max(1, (len(entries) + per_page - 1) // per_page)
    usable_width = PAGE_WIDTH - 2 * PAGE_MARGIN
    usable_height = PAGE_HEIGHT - 2 * PAGE_MARGIN - HEADER_HEIGHT
    cell_width = usable_width // columns
    cell_height = usable_height // rows
    title_font = _font(31, bold=True)
    card_title_font = _font(22, bold=True)
    meta_font = _font(17)
    pages: list[Path] = []
    index_entries: list[dict[str, Any]] = []

    for page_index in range(page_count):
        canvas = Image.new("RGB", (PAGE_WIDTH, PAGE_HEIGHT), BACKGROUND)
        draw = ImageDraw.Draw(canvas)
        draw.text(
            (PAGE_MARGIN, PAGE_MARGIN),
            f"AI Agent 教材图稿联系表 · {page_index + 1}/{page_count}",
            fill=INK,
            font=title_font,
        )
        page_entries = entries[page_index * per_page : (page_index + 1) * per_page]
        for slot, entry in enumerate(page_entries):
            row, column = divmod(slot, columns)
            left = PAGE_MARGIN + column * cell_width + 10
            top = PAGE_MARGIN + HEADER_HEIGHT + row * cell_height + 10
            right = PAGE_MARGIN + (column + 1) * cell_width - 10
            bottom = PAGE_MARGIN + HEADER_HEIGHT + (row + 1) * cell_height - 10
            draw.rounded_rectangle(
                (left, top, right, bottom),
                radius=18,
                fill=CARD,
                outline="#D8D3C8",
                width=2,
            )
            png_path = asset_root / str(entry["png_path"])
            if not png_path.is_file():
                raise FileNotFoundError(f"diagram PNG missing: {png_path}")
            with Image.open(png_path) as source:
                thumbnail = ImageOps.contain(
                    source.convert("RGB"),
                    (right - left - 34, bottom - top - 142),
                    Image.Resampling.LANCZOS,
                )
            image_left = left + (right - left - thumbnail.width) // 2
            image_top = top + 18
            canvas.paste(thumbnail, (image_left, image_top))
            text_top = bottom - 112
            draw.line((left + 18, text_top - 12, right - 18, text_top - 12), fill="#E3DED4")
            draw.text(
                (left + 18, text_top),
                _wrapped(str(entry.get("title", "")), 28),
                fill=INK,
                font=card_title_font,
                spacing=3,
            )
            draw.text(
                (left + 18, bottom - 56),
                _wrapped(str(entry.get("source_path", "")), 48),
                fill=MUTED,
                font=meta_font,
                spacing=2,
            )
            draw.text(
                (right - 56, top + 16),
                f"{page_index * per_page + slot + 1:03d}",
                fill=ACCENT,
                font=meta_font,
            )
            index_entries.append(
                {
                    "page": page_index + 1,
                    "slot": slot + 1,
                    "semantic_id": str(entry.get("semantic_id", "")),
                    "title": str(entry.get("title", "")),
                    "source_path": str(entry.get("source_path", "")),
                    "png_path": str(entry.get("png_path", "")),
                }
            )
        page_path = output_dir / f"diagram-contact-sheet-{page_index + 1:02d}.png"
        canvas.save(page_path, optimize=True)
        pages.append(page_path)

    index_path = output_dir / "index.json"
    index_path.write_text(
        json.dumps(
            {
                "diagram_count": len(entries),
                "page_count": page_count,
                "columns": columns,
                "rows": rows,
                "entries": index_entries,
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return pages, index_path
