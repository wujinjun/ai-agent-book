#!/usr/bin/env python3
"""Build EPUB3 and print-ready PDF from the canonical Markdown book."""

from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
import zipfile
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
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/google-chrome-stable"),
    Path("/usr/bin/chromium"),
)


def convert_mkdocs_admonitions(markdown: str) -> str:
    """Convert MkDocs-only admonitions into portable Markdown blockquotes."""

    lines = markdown.splitlines()
    rendered: list[str] = []
    index = 0
    labels = {"warning": "警告", "note": "说明", "tip": "提示"}
    while index < len(lines):
        match = re.match(
            r'^!!!\s+(?P<kind>[\w-]+)(?:\s+"(?P<title>[^"]+)")?\s*$',
            lines[index],
        )
        if match is None:
            rendered.append(lines[index])
            index += 1
            continue
        title = match.group("title") or labels.get(match.group("kind"), match.group("kind"))
        rendered.append(f"> **{title}**")
        index += 1
        while index < len(lines) and (
            not lines[index].strip() or lines[index].startswith(("    ", "\t"))
        ):
            body = (
                lines[index][4:]
                if lines[index].startswith("    ")
                else lines[index].lstrip("\t")
            )
            rendered.append(f"> {body}" if body else ">")
            index += 1
    return "\n".join(rendered) + ("\n" if markdown.endswith("\n") else "")


def compose_book(root: Path, output: Path) -> Path:
    """Compose front matter, 38 chapters, ten projects, and back matter."""

    sections: list[str] = []
    for entry in load_publication_entries(root / "mkdocs.yml"):
        if entry.path in {Path("docs/index.md"), Path("docs/project-status.md")}:
            continue
        markdown = (root / entry.path).read_text(encoding="utf-8")
        markdown = convert_mkdocs_admonitions(markdown)
        diagrams = extract_diagrams(entry.path, markdown)
        sections.append(replace_mermaid(markdown, diagrams, Path("assets/diagrams")))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text("\n\n".join(sections), encoding="utf-8")
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
    inject_epub_svg_fallbacks(output, ROOT)
    return output


def inject_epub_svg_fallbacks(epub_path: Path, root: Path) -> Path:
    """Embed SVG sources that Pandoc leaves as raw picture references."""

    source_pattern = re.compile(r'srcset="assets/diagrams/svg/(?P<name>[^"/]+\.svg)"')
    with zipfile.ZipFile(epub_path) as archive:
        infos = archive.infolist()
        content = {info.filename: archive.read(info.filename) for info in infos}

    svg_names: set[str] = set()
    for name, payload in list(content.items()):
        if not name.startswith("EPUB/text/") or not name.endswith(".xhtml"):
            continue
        text = payload.decode("utf-8")

        def replace_source(match: re.Match[str]) -> str:
            svg_name = match.group("name")
            svg_names.add(svg_name)
            return f'srcset="../media/{svg_name}"'

        text = source_pattern.sub(replace_source, text)
        text = re.sub(
            r"<(?P<tag>source|img)\b(?P<attrs>[^>]*?)(?<!/)>",
            r"<\g<tag>\g<attrs>/>",
            text,
        )
        content[name] = text.encode("utf-8")

    opf_name = "EPUB/content.opf"
    opf = content[opf_name].decode("utf-8")
    items: list[str] = []
    for svg_name in sorted(svg_names):
        source = root / "assets/diagrams/svg" / svg_name
        if not source.is_file():
            raise RuntimeError(f"EPUB SVG 源文件不存在：{source}")
        content[f"EPUB/media/{svg_name}"] = source.read_bytes()
        item_id = "svg_" + re.sub(r"[^a-zA-Z0-9]+", "_", svg_name)
        items.append(
            f'    <item id="{item_id}" href="media/{svg_name}" '
            'media-type="image/svg+xml" />'
        )
    if items:
        opf = opf.replace("</manifest>", "\n".join(items) + "\n  </manifest>", 1)
        content[opf_name] = opf.encode("utf-8")

    temporary = epub_path.with_suffix(".tmp.epub")
    with zipfile.ZipFile(temporary, "w") as output:
        for info in infos:
            output.writestr(info, content.pop(info.filename))
        for name, payload in sorted(content.items()):
            output.writestr(name, payload, compress_type=zipfile.ZIP_DEFLATED)
    temporary.replace(epub_path)
    return epub_path


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
            "--section-divs",
            f"--resource-path={ROOT}",
            f"--metadata-file={ROOT / 'templates/pandoc/metadata.yaml'}",
            f"--css={ROOT / 'templates/pandoc/print.css'}",
            "--output",
            str(output),
        ]
    )
    shutil.copytree(
        ROOT / "assets/diagrams/svg",
        output.parent / "assets/diagrams/svg",
        dirs_exist_ok=True,
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


def stage_offline_editions(
    html_dir: Path,
    pdf_path: Path,
    epub_path: Path,
) -> list[Path]:
    """Copy offline editions into the generated reading site."""

    downloads = html_dir / "downloads"
    downloads.mkdir(parents=True, exist_ok=True)
    outputs = [downloads / pdf_path.name, downloads / epub_path.name]
    shutil.copy2(pdf_path, outputs[0])
    shutil.copy2(epub_path, outputs[1])
    return outputs


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
        epub_output: Path | None = None
        pdf_output: Path | None = None
        if args.format in {"all", "epub"}:
            epub_output = build_epub(pandoc, source)
            outputs.append(epub_output)
        if args.format in {"all", "pdf", "html"}:
            print_html = build_print_html(pandoc, source)
            outputs.append(print_html)
            if args.format in {"all", "pdf"}:
                pdf_output = build_pdf(print_html)
                outputs.append(pdf_output)
        if args.format == "all":
            if epub_output is None or pdf_output is None:
                raise RuntimeError("完整发布缺少 PDF 或 EPUB。")
            outputs.extend(
                stage_offline_editions(
                    ROOT / "output/html",
                    pdf_output,
                    epub_output,
                )
            )
    except (RuntimeError, subprocess.TimeoutExpired) as error:
        print(str(error), file=sys.stderr)
        return 1
    for output in outputs:
        print(output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
