"""Dependency-light SVG and PNG heatmap export for fixed attention weights."""

import struct
import zlib
from pathlib import Path

import numpy as np

from attention_demo.domain import FloatArray


def _color(weight: float) -> tuple[int, int, int]:
    bounded = max(0.0, min(1.0, weight))
    return (
        int(244 - 158 * bounded),
        int(247 - 120 * bounded),
        int(255 - 38 * bounded),
    )


def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(
        ">I", zlib.crc32(kind + payload)
    )


def _write_png(weights: FloatArray, path: Path, *, cell_size: int = 48) -> None:
    rows, columns = weights.shape
    width, height = columns * cell_size, rows * cell_size
    scanlines = bytearray()
    for y in range(height):
        scanlines.append(0)
        source_row = y // cell_size
        for x in range(width):
            source_column = x // cell_size
            red, green, blue = _color(float(weights[source_row, source_column]))
            scanlines.extend((red, green, blue, 255))
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _png_chunk(b"IHDR", header)
    png += _png_chunk(b"IDAT", zlib.compress(bytes(scanlines), level=9))
    png += _png_chunk(b"IEND", b"")
    path.write_bytes(png)


def _write_svg(weights: FloatArray, labels: tuple[str, ...], path: Path) -> None:
    cell, margin_left, margin_top = 72, 100, 70
    rows, columns = weights.shape
    width = margin_left + columns * cell + 24
    height = margin_top + rows * cell + 70
    elements = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#f8fafc"/>',
        '<text x="20" y="28" font-family="sans-serif" font-size="18" '
        'font-weight="700" fill="#172554">因果掩码后的注意力权重</text>',
    ]
    for index, label in enumerate(labels):
        x = margin_left + index * cell + cell / 2
        y = margin_top + index * cell + cell / 2
        elements.append(
            f'<text x="{x}" y="55" text-anchor="middle" font-family="sans-serif" '
            f'font-size="13" fill="#334155">K: {label}</text>'
        )
        elements.append(
            f'<text x="90" y="{y + 5}" text-anchor="end" font-family="sans-serif" '
            f'font-size="13" fill="#334155">Q: {label}</text>'
        )
    for row in range(rows):
        for column in range(columns):
            weight = float(weights[row, column])
            red, green, blue = _color(weight)
            x, y = margin_left + column * cell, margin_top + row * cell
            elements.extend(
                (
                    f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" '
                    f'fill="rgb({red},{green},{blue})" stroke="#ffffff"/>',
                    f'<text x="{x + cell / 2}" y="{y + cell / 2 + 5}" '
                    'text-anchor="middle" font-family="monospace" font-size="14" '
                    f'fill="#0f172a">{weight:.3f}</text>',
                )
            )
    elements.append(
        f'<text x="20" y="{height - 20}" font-family="sans-serif" font-size="12" '
        'fill="#9f1239">注意力权重不等于因果解释，仅用于机制教学。</text>'
    )
    elements.append("</svg>")
    path.write_text("\n".join(elements), encoding="utf-8")


def write_heatmap_assets(
    weights: FloatArray, labels: tuple[str, ...], output_directory: Path
) -> tuple[Path, Path]:
    if weights.ndim != 2 or weights.shape[0] != weights.shape[1]:
        raise ValueError("热力图要求方形二维注意力矩阵")
    if len(labels) != weights.shape[0] or not np.isfinite(weights).all():
        raise ValueError("标签数量必须匹配，权重必须为有限数")
    output_directory.mkdir(parents=True, exist_ok=True)
    svg_path = output_directory / "attention-weights.svg"
    png_path = output_directory / "attention-weights.png"
    _write_svg(weights, labels, svg_path)
    _write_png(weights, png_path)
    return svg_path, png_path
