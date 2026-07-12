#!/usr/bin/env python3
"""Render every book Mermaid fence to stable SVG and PNG assets."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.book_manifest import load_publication_entries  # noqa: E402
from ai_agent_book.diagram_pipeline import extract_diagrams, write_manifest  # noqa: E402


def build_diagrams(root: Path, *, executable: str = "mmdc") -> int:
    renderer = shutil.which(executable)
    if renderer is None:
        print(
            "Mermaid CLI 未安装。请运行 npm install --save-dev @mermaid-js/mermaid-cli，"
            "或通过 --mmdc 指定可执行文件。",
            file=sys.stderr,
        )
        return 2

    asset_root = root / "assets/diagrams"
    records = []
    for entry in load_publication_entries(root / "mkdocs.yml"):
        markdown = (root / entry.path).read_text(encoding="utf-8")
        records.extend(extract_diagrams(entry.path, markdown))

    config = root / "templates/mermaid-config.json"
    puppeteer_config = root / "templates/puppeteer-config.json"
    puppeteer_options = json.loads(puppeteer_config.read_text(encoding="utf-8"))
    configured_browser = Path(str(puppeteer_options.get("executablePath", "")))
    for record in records:
        source = asset_root / record.source_asset
        svg = asset_root / record.svg_path
        png = asset_root / record.png_path
        source.parent.mkdir(parents=True, exist_ok=True)
        svg.parent.mkdir(parents=True, exist_ok=True)
        png.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(record.source, encoding="utf-8")
        for output, scale in ((svg, "1"), (png, "2")):
            if output.is_file() and output.stat().st_size > 0:
                continue
            command = [
                renderer,
                "-i",
                str(source),
                "-o",
                str(output),
                "-c",
                str(config),
                "-b",
                "white",
                "-s",
                scale,
            ]
            if configured_browser.is_file():
                command[command.index("-b"):command.index("-b")] = [
                    "-p",
                    str(puppeteer_config),
                ]
            try:
                subprocess.run(command, check=True, capture_output=True, text=True, timeout=30)
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as error:
                detail = getattr(error, "stderr", "") or str(error)
                print(
                    f"图形渲染失败：{record.source_path}，图 {record.index}\n{detail}",
                    file=sys.stderr,
                )
                return 1
    write_manifest(records, asset_root / "manifest.json")
    print(f"Rendered {len(records)} diagrams into {asset_root}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--mmdc", default="mmdc")
    args = parser.parse_args()
    return build_diagrams(ROOT, executable=args.mmdc)


if __name__ == "__main__":
    raise SystemExit(main())
