#!/usr/bin/env python3
"""Build the strict MkDocs HTML publication."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.book_manifest import load_book_entries  # noqa: E402
from ai_agent_book.diagram_pipeline import extract_diagrams, replace_mermaid  # noqa: E402


def prepare_html_sources(root: Path, destination: Path) -> Path:
    """Create a disposable docs tree whose Mermaid fences use portable assets."""

    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(root / "docs", destination)
    internal_notes = destination / "superpowers"
    if internal_notes.exists():
        shutil.rmtree(internal_notes)

    diagrams_source = root / "assets/diagrams"
    diagrams_target = destination / "assets/diagrams"
    if not (diagrams_source / "manifest.json").is_file():
        raise FileNotFoundError("图形清单不存在；请先运行 scripts/build_diagrams.py。")
    shutil.copytree(diagrams_source, diagrams_target, dirs_exist_ok=True)

    for entry in load_book_entries(root / "mkdocs.yml"):
        original = root / entry.path
        prepared = destination / entry.path.relative_to("docs")
        markdown = original.read_text(encoding="utf-8")
        diagrams = extract_diagrams(entry.path, markdown)
        relative_assets = Path(
            os.path.relpath(destination / "assets/diagrams", prepared.parent)
        )
        if prepared.parent != destination:
            relative_assets = Path("..") / relative_assets
        prepared.write_text(
            replace_mermaid(markdown, diagrams, relative_assets),
            encoding="utf-8",
        )
    return destination


def write_build_config(root: Path, docs_dir: Path, output: Path) -> Path:
    """Write a temporary MkDocs config pointing at the prepared source tree."""

    config = (root / "mkdocs.yml").read_text(encoding="utf-8")
    config = config.replace("docs_dir: docs", f"docs_dir: {docs_dir.as_posix()}", 1)
    config = config.replace(
        "custom_dir: overrides",
        f"custom_dir: {(root / 'overrides').as_posix()}",
        1,
    )
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(config, encoding="utf-8")
    return output


def main() -> int:
    intermediate = ROOT / "output/intermediate"
    prepared_docs = prepare_html_sources(ROOT, intermediate / "html-docs")
    config = write_build_config(ROOT, prepared_docs, intermediate / "mkdocs-html.yml")
    command = [
        sys.executable,
        "-m",
        "mkdocs",
        "build",
        "--config-file",
        str(config),
        "--strict",
        "--site-dir",
        str(ROOT / "output/html"),
    ]
    try:
        completed = subprocess.run(command, cwd=ROOT, check=False, timeout=180)
    except subprocess.TimeoutExpired:
        print("MkDocs 构建超过 180 秒，已终止。", file=sys.stderr)
        return 124
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
