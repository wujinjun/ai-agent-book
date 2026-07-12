#!/usr/bin/env python3
"""Build EPUB3 and print-ready PDF from the canonical Markdown book."""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.book_manifest import load_publication_entries  # noqa: E402
from ai_agent_book.diagram_pipeline import extract_diagrams, replace_mermaid  # noqa: E402

BOOK_NAME = "ai-agent-book-2026"
CHROME_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
)


def compose_book(root: Path, output: Path) -> Path:
    """Compose front matter, 38 chapters, ten projects, and back matter."""

    sections: list[str] = []
    for entry in load_publication_entries(root / "mkdocs.yml"):
        if entry.path in {Path("docs/index.md"), Path("docs/project-status.md")}:
            continue
        markdown = (root / entry.path).read_text(encoding="utf-8")
        diagrams = extract_diagrams(entry.path, markdown)
        sections.append(replace_mermaid(markdown, diagrams, Path("assets/diagrams")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n<div class=\"page-break\"></div>\n\n".join(sections), encoding="utf-8")
    return output


def _require_pandoc() -> str:
    executable = shutil.which("pandoc")
    if executable is None:
        raise RuntimeError("Pandoc 未安装。macOS 请运行 brew install pandoc。")
    return executable


def _run(command: list[str], *, timeout: int = 600) -> None:
    completed = subprocess.run(
        command,
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(
            f"命令失败（{completed.returncode}）：{' '.join(command)}\n{completed.stderr}"
        )


def build_epub(pandoc: str, source: Path) -> Path:
    output = ROOT / f"output/epub/{BOOK_NAME}.epub"
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(
        [
            pandoc,
            str(source),
            "--from=gfm+raw_html",
            "--to=epub3",
            "--standalone",
            "--toc",
            "--toc-depth=2",
            "--section-divs",
            f"--resource-path={ROOT}",
            f"--metadata-file={ROOT / 'templates/pandoc/metadata.yaml'}",
            f"--css={ROOT / 'templates/pandoc/epub.css'}",
            "--output",
            str(output),
        ]
    )
    return output


def build_print_html(pandoc: str, source: Path) -> Path:
    output = ROOT / "output/intermediate/print.html"
    _run(
        [
            pandoc,
            str(source),
            "--from=gfm+raw_html",
            "--to=html5",
            "--standalone",
            "--embed-resources",
            "--toc",
            "--toc-depth=2",
            "--number-sections",
            "--section-divs",
            f"--resource-path={ROOT}",
            f"--metadata-file={ROOT / 'templates/pandoc/metadata.yaml'}",
            f"--css={ROOT / 'templates/pandoc/print.css'}",
            "--output",
            str(output),
        ]
    )
    return output


def build_pdf(print_html: Path) -> Path:
    chrome = next((path for path in CHROME_CANDIDATES if path.is_file()), None)
    if chrome is None:
        raise RuntimeError("未找到 Google Chrome/Chromium，无法输出 PDF。")
    output = ROOT / f"output/pdf/{BOOK_NAME}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    _run(chrome_pdf_command(chrome, print_html, output))
    if not output.is_file() or output.stat().st_size == 0:
        raise RuntimeError("Chrome 未生成有效 PDF。")
    return output


def chrome_pdf_command(chrome: Path, print_html: Path, output: Path) -> list[str]:
    """Build the deterministic Chrome Headless PDF command."""

    return [
        str(chrome),
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output}",
        print_html.resolve().as_uri(),
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("format", choices=("all", "epub", "pdf", "html"), default="all", nargs="?")
    args = parser.parse_args()
    try:
        pandoc = _require_pandoc()
        source = compose_book(ROOT, ROOT / "output/intermediate/book.md")
        outputs: list[Path] = []
        if args.format in {"all", "epub"}:
            outputs.append(build_epub(pandoc, source))
        if args.format in {"all", "pdf", "html"}:
            print_html = build_print_html(pandoc, source)
            outputs.append(print_html)
            if args.format in {"all", "pdf"}:
                outputs.append(build_pdf(print_html))
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
