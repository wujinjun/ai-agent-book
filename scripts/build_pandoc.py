#!/usr/bin/env python3
"""Build EPUB3 and print-ready PDF from the canonical Markdown book."""

from __future__ import annotations

import argparse
import html
import posixpath
import re
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

from pypdf import PdfReader

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.book_manifest import load_publication_entries  # noqa: E402
from ai_agent_book.diagram_pipeline import extract_diagrams, replace_mermaid  # noqa: E402

BOOK_NAME = "ai-agent-book-2026"
REPOSITORY_BLOB_URL = "https://github.com/wujinjun/ai-agent-book/blob/main"
EPUB_CROSS_DOCUMENT_MARKER = "--epub-xref--"
MARKDOWN_LINK_PATTERN = re.compile(
    r"(?P<prefix>!?\[[^\]]*\]\()"
    r"(?P<target><[^>]+>|[^)\s]+)"
    r"(?P<suffix>(?:\s+[\"'][^\"']*[\"'])?\))"
)
CHROME_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/google-chrome-stable"),
    Path("/usr/bin/chromium"),
)


def _document_id(path: Path) -> str:
    """Return a stable, EPUB-safe anchor for one source document."""

    parts = list(path.with_suffix("").parts)
    if parts and parts[0] == "docs":
        parts = parts[1:]
    if parts and parts[-1].lower() == "readme":
        parts = parts[:-1]
    slug = "-".join(parts).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug).strip("-")
    return f"doc-{slug or 'book'}"


def _resolve_local_target(source_path: Path, target: str) -> tuple[Path, str]:
    """Resolve a Markdown target against its original source document."""

    path_text, separator, fragment = target.partition("#")
    if path_text.startswith("/"):
        candidate = path_text.lstrip("/")
    else:
        candidate = (source_path.parent / path_text).as_posix()
    normalized = Path(posixpath.normpath(candidate))
    return normalized, fragment if separator else ""


def rewrite_publication_links(
    markdown: str,
    *,
    source_path: Path,
    document_ids: dict[Path, str],
    root: Path,
) -> str:
    """Rewrite repository-relative links for a single-file Pandoc source.

    Pandoc receives all chapters as one composed Markdown file, so links that
    were relative to their original chapter otherwise point at non-existent
    ``.md`` files in EPUB readers. Publication documents use stable anchors;
    other repository files link to GitHub; local images use root-relative paths
    so Pandoc can embed them.
    """

    def replace(match: re.Match[str]) -> str:
        raw_target = match.group("target")
        bracketed = raw_target.startswith("<") and raw_target.endswith(">")
        target = raw_target[1:-1] if bracketed else raw_target
        if target.startswith(("#", "http://", "https://", "mailto:", "data:")):
            return match.group(0)

        local_path, fragment = _resolve_local_target(source_path, target)
        is_image = match.group("prefix").startswith("!")
        if is_image:
            if not (root / local_path).is_file():
                raise RuntimeError(f"出版图片不存在：{source_path.as_posix()} -> {target}")
            rewritten = local_path.as_posix()
        elif local_path in document_ids:
            if fragment and source_path == Path("docs/book-index.md"):
                # The full-book index intentionally links to many repeated
                # heading IDs (for example ``id__2``). Preserve the owning
                # source document until EPUB post-processing so Pandoc's
                # chapter split cannot make those links ambiguous.
                rewritten = (
                    f"#{document_ids[local_path]}{EPUB_CROSS_DOCUMENT_MARKER}{fragment}"
                )
            else:
                rewritten = f"#{fragment}" if fragment else f"#{document_ids[local_path]}"
        elif (root / local_path).exists():
            rewritten = f"{REPOSITORY_BLOB_URL}/{local_path.as_posix()}"
            if fragment:
                rewritten += f"#{fragment}"
        else:
            raise RuntimeError(f"出版链接目标不存在：{source_path.as_posix()} -> {target}")

        if bracketed:
            rewritten = f"<{rewritten}>"
        return f"{match.group('prefix')}{rewritten}{match.group('suffix')}"

    return MARKDOWN_LINK_PATTERN.sub(replace, markdown)


def add_document_anchor(markdown: str, document_id: str) -> str:
    """Place a stable raw-HTML anchor inside the first level-one section.

    Pandoc's GFM reader deliberately does not support heading attributes. An
    explicit span keeps the visible heading and generated table of contents
    clean, while surviving EPUB chapter splitting inside the same section.
    """

    rendered, replacements = re.subn(
        r"^# (?P<title>.+?)\s*$",
        rf'# \g<title>\n\n<span id="{document_id}"></span>',
        markdown,
        count=1,
        flags=re.MULTILINE,
    )
    if replacements != 1:
        raise RuntimeError(f"出版文档缺少一级标题：{document_id}")
    return rendered


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
                lines[index][4:] if lines[index].startswith("    ") else lines[index].lstrip("\t")
            )
            rendered.append(f"> {body}" if body else ">")
            index += 1
    return "\n".join(rendered) + ("\n" if markdown.endswith("\n") else "")


def compose_book(root: Path, output: Path) -> Path:
    """Compose front matter, 38 chapters, ten projects, and back matter."""

    sections: list[str] = []
    entries = [
        entry
        for entry in load_publication_entries(root / "mkdocs.yml")
        if entry.path not in {Path("docs/index.md"), Path("docs/project-status.md")}
        and entry.path.parts[:2] != ("docs", "training")
    ]
    document_ids = {entry.path: _document_id(entry.path) for entry in entries}
    if len(set(document_ids.values())) != len(document_ids):
        raise RuntimeError("出版文档锚点发生冲突")
    for entry in entries:
        markdown = (root / entry.path).read_text(encoding="utf-8")
        markdown = convert_mkdocs_admonitions(markdown)
        markdown = rewrite_publication_links(
            markdown,
            source_path=entry.path,
            document_ids=document_ids,
            root=root,
        )
        markdown = add_document_anchor(markdown, document_ids[entry.path])
        if entry.path.match("docs/part-*/index.md"):
            markdown = re.sub(
                r'^(# .+?\n)',
                r'\1\n<div class="part-opener-marker"></div>\n',
                markdown,
                count=1,
            )
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
    epub_source = ROOT / "output/intermediate/book-epub.md"
    epub_source.write_text(
        prepare_epub_markdown(source.read_text(encoding="utf-8"), root=ROOT),
        encoding="utf-8",
    )
    _run(
        [
            pandoc,
            str(epub_source),
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
    """Repair split-document links and replace diagram PNG fallbacks with SVG.

    Pandoc accepts one composed Markdown source, then splits EPUB output into
    multiple XHTML documents. Fragment-only links therefore need to be
    redirected to the XHTML file that owns the target ID. EPUB 3 supports SVG,
    so the same pass embeds the deterministic SVG and removes Pandoc's duplicate
    raster fallback. Information graphics remain optimized PNG assets.
    """

    source_pattern = re.compile(r'srcset="assets/diagrams/svg/(?P<name>[^"/]+\.svg)"')
    picture_pattern = re.compile(
        r'<picture>\s*<source\b[^>]*srcset="assets/diagrams/svg/'
        r'(?P<name>[^"/]+\.svg)"[^>]*/?>\s*<img(?P<attrs>[^>]*)/?>\s*</picture>',
        re.DOTALL,
    )
    with zipfile.ZipFile(epub_path) as archive:
        infos = archive.infolist()
        content = {info.filename: archive.read(info.filename) for info in infos}

    ids_by_document: dict[str, set[str]] = {}
    headings_by_document: dict[str, dict[str, str]] = {}
    locations_by_id: dict[str, str] = {}
    duplicate_ids: set[str] = set()
    for name, payload in content.items():
        if not name.endswith(".xhtml"):
            continue
        document_text = payload.decode("utf-8")
        document_ids = set(re.findall(r'\bid=["\'](?P<id>[^"\']+)["\']', document_text))
        ids_by_document[name] = document_ids
        heading_ids: dict[str, str] = {}
        for heading in re.finditer(
            r'<section\s+id="(?P<id>[^"]+)"\s+class="level[1-6]">\s*'
            r'<h[1-6]>(?P<title>.*?)</h[1-6]>',
            document_text,
            flags=re.DOTALL,
        ):
            title = html.unescape(re.sub(r"<[^>]+>", "", heading.group("title"))).strip()
            heading_ids.setdefault(title, heading.group("id"))
        headings_by_document[name] = heading_ids
        for document_id in document_ids:
            if document_id in locations_by_id:
                duplicate_ids.add(document_id)
            else:
                locations_by_id[document_id] = name
    for document_id in duplicate_ids:
        locations_by_id.pop(document_id, None)

    svg_names: set[str] = set()
    raster_fallbacks: set[str] = set()
    for name, payload in list(content.items()):
        if not name.endswith(".xhtml"):
            continue
        text = payload.decode("utf-8")

        def replace_cross_document_link(
            match: re.Match[str], current_name: str = name
        ) -> str:
            document_id = match.group("document")
            fragment = match.group("fragment")
            target_name = locations_by_id.get(document_id)
            if target_name is None:
                return match.group(0)
            label = match.group("label")
            label_text = html.unescape(re.sub(r"<[^>]+>", "", label)).strip()
            heading_title = label_text.rsplit(" · ", 1)[-1]
            target_fragment = (
                fragment
                if fragment in ids_by_document.get(target_name, set())
                else headings_by_document.get(target_name, {}).get(heading_title, document_id)
            )
            relative = posixpath.relpath(target_name, posixpath.dirname(current_name))
            return (
                f'<a{match.group("before")}href="{relative}#{target_fragment}"'
                f'{match.group("after")}>{label}</a>'
            )

        text = re.sub(
            rf'<a(?P<before>[^>]*?)href="#(?P<document>doc-[^"#]+?)'
            rf'{re.escape(EPUB_CROSS_DOCUMENT_MARKER)}(?P<fragment>[^"#]+)"'
            r'(?P<after>[^>]*)>(?P<label>.*?)</a>',
            replace_cross_document_link,
            text,
            flags=re.DOTALL,
        )

        def replace_fragment_link(match: re.Match[str], current_name: str = name) -> str:
            fragment = match.group("fragment")
            if fragment in ids_by_document.get(current_name, set()):
                return match.group(0)
            target_name = locations_by_id.get(fragment)
            if target_name is None:
                return match.group(0)
            relative = posixpath.relpath(target_name, posixpath.dirname(current_name))
            return f'href="{relative}#{fragment}"'

        text = re.sub(
            r'href="#(?P<fragment>[^"#]+)"',
            replace_fragment_link,
            text,
        )

        def replace_picture(match: re.Match[str]) -> str:
            svg_name = match.group("name")
            svg_names.add(svg_name)
            attrs = match.group("attrs")
            raster = re.search(r'\bsrc="\.\./media/(?P<name>[^"/]+)"', attrs)
            if raster is not None:
                raster_fallbacks.add(raster.group("name"))
            attrs = re.sub(r'\s+src="[^"]+"', "", attrs)
            return f'<img{attrs} src="../media/{svg_name}"/>'

        text = picture_pattern.sub(replace_picture, text)

        # Pandoc emits bare tables in EPUB XHTML. Wrapping them gives narrow
        # readers an independent horizontal scroll area instead of compressing
        # four or more columns into one-character-wide cells.
        text = re.sub(
            r"(?<!<div class=\"table-wrapper\">)(<table\b[^>]*>.*?</table>)",
            r'<div class="table-wrapper">\1</div>',
            text,
            flags=re.DOTALL,
        )

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
    for fallback in sorted(raster_fallbacks):
        content.pop(f"EPUB/media/{fallback}", None)
        opf = re.sub(
            rf'^\s*<item\b[^>]*href="media/{re.escape(fallback)}"[^>]*/>\s*$\n?',
            "",
            opf,
            flags=re.MULTILINE,
        )
    items: list[str] = []
    for svg_name in sorted(svg_names):
        source = root / "assets/diagrams/svg" / svg_name
        if not source.is_file():
            raise RuntimeError(f"EPUB SVG 源文件不存在：{source}")
        content[f"EPUB/media/{svg_name}"] = source.read_bytes()
        item_id = "svg_" + re.sub(r"[^a-zA-Z0-9]+", "_", svg_name)
        items.append(
            f'    <item id="{item_id}" href="media/{svg_name}" media-type="image/svg+xml" />'
        )
    if items:
        opf = opf.replace("</manifest>", "\n".join(items) + "\n  </manifest>", 1)
        content[opf_name] = opf.encode("utf-8")

    temporary = epub_path.with_suffix(".tmp.epub")
    with zipfile.ZipFile(temporary, "w") as output:
        for info in infos:
            if info.filename in content:
                output.writestr(info, content.pop(info.filename))
        for name, payload in sorted(content.items()):
            output.writestr(name, payload, compress_type=zipfile.ZIP_DEFLATED)
    temporary.replace(epub_path)
    return epub_path


def build_print_html(pandoc: str, source: Path) -> Path:
    output = ROOT / "output/intermediate/print.html"
    print_source = ROOT / "output/intermediate/book-print.md"
    print_source.write_text(
        prepare_print_markdown(source.read_text(encoding="utf-8"), root=ROOT),
        encoding="utf-8",
    )
    _run(
        [
            pandoc,
            str(print_source),
            "--from=gfm+raw_html",
            "--to=html5",
            "--standalone",
            "--toc",
            "--toc-depth=1",
            "--section-divs",
            f"--resource-path={ROOT}",
            f"--metadata-file={ROOT / 'templates/pandoc/metadata.yaml'}",
            f"--css={ROOT / 'templates/pandoc/print.css'}",
            "--output",
            str(output),
        ]
    )
    html = output.read_text(encoding="utf-8")
    html = html.replace(
        "<head>",
        f'<head>\n  <base href="{ROOT.resolve().as_uri()}/">',
        1,
    )
    html = html.replace(
        '<h1 class="title">AI Agent 从零到实战：原理、工程与项目（2026版）</h1>',
        '<h1 class="title"><span class="title-main">AI Agent 从零到实战</span>'
        '<span class="title-detail">原理、工程与项目（2026版）</span></h1>',
        1,
    )
    output.write_text(html, encoding="utf-8")
    shutil.copytree(
        ROOT / "assets/diagrams/svg",
        output.parent / "assets/diagrams/svg",
        dirs_exist_ok=True,
    )
    return output


MERMAID_PICTURE_RE = re.compile(
    r'<picture>\s*<source type="image/svg\+xml" srcset="(?P<svg>[^"]+)">\s*'
    r'<img src="[^"]+"(?P<attrs>[^>]*)>\s*</picture>',
    re.DOTALL,
)
INFOGRAPHIC_PNG_RE = re.compile(
    r"(?:docs/)?assets/infographics/png/(?P<name>[a-z0-9-]+?)(?:-2x)?\.png"
)


def prepare_epub_markdown(markdown: str, *, root: Path) -> str:
    """Use EPUB-specific, bounded PNGs while keeping engineering diagrams vector."""

    def replace_infographic(match: re.Match[str]) -> str:
        source = root / f"assets/infographics/png/{match.group('name')}-2x.png"
        target = root / (
            f"output/intermediate/epub-infographics-1100/{match.group('name')}.png"
        )
        if not source.is_file():
            raise RuntimeError(f"EPUB 信息图 PNG 不存在：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.is_file() or target.stat().st_mtime_ns < source.stat().st_mtime_ns:
            _run(
                [
                    "sips",
                    "--resampleHeightWidthMax",
                    "1100",
                    str(source),
                    "--out",
                    str(target),
                ]
            )
        return target.relative_to(root).as_posix()

    return INFOGRAPHIC_PNG_RE.sub(replace_infographic, markdown)


def prepare_print_markdown(markdown: str, *, root: Path) -> str:
    """Prefer vector assets in the PDF-only source to keep Chrome memory bounded."""

    def replace_mermaid_picture(match: re.Match[str]) -> str:
        svg = match.group("svg")
        if not (root / svg).is_file():
            raise RuntimeError(f"打印版 Mermaid SVG 不存在：{svg}")
        return f'<img src="{svg}"{match.group("attrs")}>'

    def replace_infographic(match: re.Match[str]) -> str:
        source = root / f"assets/infographics/png/{match.group('name')}-2x.png"
        target = root / f"output/intermediate/infographics/{match.group('name')}-print.png"
        size_marker = target.with_suffix(".max960")
        if not source.is_file():
            raise RuntimeError(f"打印版信息图 PNG 不存在：{source}")
        target.parent.mkdir(parents=True, exist_ok=True)
        if (
            not target.is_file()
            or not size_marker.is_file()
            or target.stat().st_mtime_ns < source.stat().st_mtime_ns
        ):
            _run(
                [
                    "sips",
                    "--resampleHeightWidthMax",
                    "960",
                    str(source),
                    "--out",
                    str(target),
                ]
            )
            size_marker.write_text("max-dimension=960\n", encoding="utf-8")
        return target.relative_to(root).as_posix()

    # The print source remains one HTML document, so only the original heading
    # fragment is required. EPUB retains the compound marker until its XHTML
    # chapter locations are known.
    markdown = re.sub(
        rf"#doc-[a-z0-9-]+{re.escape(EPUB_CROSS_DOCUMENT_MARKER)}(?P<fragment>[a-zA-Z0-9_.:-]+)",
        r"#\g<fragment>",
        markdown,
    )
    vectorized = MERMAID_PICTURE_RE.sub(replace_mermaid_picture, markdown)
    return INFOGRAPHIC_PNG_RE.sub(replace_infographic, vectorized)


def build_pdf(print_html: Path) -> Path:
    chrome = next((path for path in CHROME_CANDIDATES if path.is_file()), None)
    if chrome is None:
        raise RuntimeError("未找到 Google Chrome/Chromium，无法输出 PDF。")
    output = ROOT / f"output/pdf/{BOOK_NAME}.pdf"
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(".tmp.pdf")
    temporary.unlink(missing_ok=True)
    with tempfile.TemporaryDirectory(prefix="ai-agent-book-chrome-") as profile:
        try:
            run_chrome_pdf(
                chrome_pdf_command(
                    chrome, print_html, temporary, user_data_dir=Path(profile)
                ),
                temporary,
            )
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    if not temporary.is_file() or temporary.stat().st_size == 0:
        raise RuntimeError("Chrome 未生成有效 PDF。")
    temporary.replace(output)
    return output


def pdf_is_complete(path: Path) -> bool:
    """Return true only when Chrome has flushed a parseable, non-empty PDF."""

    if not path.is_file() or path.stat().st_size == 0:
        return False
    try:
        reader = PdfReader(path)
        return len(reader.pages) > 0 and not reader.is_encrypted
    except Exception:
        return False


def run_chrome_pdf(
    command: list[str],
    output: Path,
    *,
    timeout: float = 600,
    poll_interval: float = 2,
    stable_checks: int = 5,
) -> None:
    """Run Chrome and recover from its occasional post-write headless hang.

    Some Chrome builds finish and flush ``--print-to-pdf`` but keep an idle
    browser process alive.  A file is accepted only after its byte size remains
    stable across several polls *and* pypdf can traverse every page object.
    The idle shell may then be terminated without treating the valid document
    as a failed build.
    """

    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    deadline = time.monotonic() + timeout
    previous_size = -1
    stable = 0
    while time.monotonic() < deadline:
        returncode = process.poll()
        size = output.stat().st_size if output.is_file() else 0
        if size > 0 and size == previous_size and pdf_is_complete(output):
            stable += 1
        else:
            stable = 0
        previous_size = size

        if stable >= stable_checks:
            if returncode is None:
                process.terminate()
                try:
                    process.wait(timeout=10)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)
            return
        if returncode is not None:
            stderr = process.stderr.read() if process.stderr is not None else ""
            if returncode != 0:
                raise RuntimeError(f"Chrome PDF 渲染失败（{returncode}）：{stderr}")
            if pdf_is_complete(output):
                return
            raise RuntimeError("Chrome 正常退出，但没有生成完整 PDF。")
        time.sleep(poll_interval)

    process.kill()
    process.wait(timeout=10)
    raise subprocess.TimeoutExpired(command, timeout)


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


def chrome_pdf_command(
    chrome: Path,
    print_html: Path,
    output: Path,
    *,
    user_data_dir: Path | None = None,
) -> list[str]:
    """Build the deterministic Chrome Headless PDF command."""

    command = [
        str(chrome),
        "--headless=new",
        "--no-sandbox",
        "--disable-gpu",
        "--disable-extensions",
        "--disable-background-networking",
        "--allow-file-access-from-files",
        "--no-pdf-header-footer",
        f"--print-to-pdf={output}",
        print_html.resolve().as_uri(),
    ]
    if user_data_dir is not None:
        command.insert(1, f"--user-data-dir={user_data_dir}")
    return command


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
