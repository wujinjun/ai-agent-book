#!/usr/bin/env python3
"""Create deterministic publication archives, notes, and SHA-256 manifests."""

from __future__ import annotations

import argparse
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def release_notes(changelog: str, version: str) -> str:
    normalized = version.removeprefix("v")
    heading = f"## v{normalized}"
    start = changelog.find(heading)
    if start < 0:
        return (
            f"# AI Agent 从零到实战 {version}\n\n"
            "本文件由发布打包脚本生成。完整变更见仓库 `CHANGELOG.md`。\n"
        )
    end = changelog.find("\n## ", start + len(heading))
    section = changelog[start : end if end >= 0 else None].strip()
    return f"# AI Agent 从零到实战 {version}\n\n{section}\n"


def write_deterministic_zip(source: Path, output: Path, prefix: str) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(item for item in source.rglob("*") if item.is_file()):
            relative = Path(prefix) / path.relative_to(source)
            info = zipfile.ZipInfo(relative.as_posix(), date_time=(2026, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, path.read_bytes())


def package_release(root: Path, version: str, destination: Path) -> list[Path]:
    pdf = root / "output/pdf/ai-agent-book-2026.pdf"
    epub = root / "output/epub/ai-agent-book-2026.epub"
    html = root / "output/html"
    changelog = root / "CHANGELOG.md"
    for required in (pdf, epub, html / "index.html", changelog):
        if not required.exists():
            raise RuntimeError(f"release input missing: {required}")

    safe_version = version.replace("/", "-")
    destination.mkdir(parents=True, exist_ok=True)
    pdf_output = destination / f"ai-agent-book-2026-{safe_version}.pdf"
    epub_output = destination / f"ai-agent-book-2026-{safe_version}.epub"
    notes_output = destination / f"RELEASE_NOTES-{safe_version}.md"
    archive_output = destination / f"ai-agent-book-output-{safe_version}.zip"
    checksum_output = destination / f"SHA256SUMS-{safe_version}.txt"
    shutil.copy2(pdf, pdf_output)
    shutil.copy2(epub, epub_output)
    notes_output.write_text(
        release_notes(changelog.read_text(encoding="utf-8"), version),
        encoding="utf-8",
    )

    with tempfile.TemporaryDirectory(prefix="ai-agent-book-release-") as directory:
        staging = Path(directory)
        shutil.copytree(html, staging / "html")
        shutil.copy2(pdf_output, staging / pdf_output.name)
        shutil.copy2(epub_output, staging / epub_output.name)
        shutil.copy2(notes_output, staging / notes_output.name)
        write_deterministic_zip(staging, archive_output, f"ai-agent-book-{safe_version}")

    checksummed = (archive_output, pdf_output, epub_output, notes_output)
    checksum_output.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in checksummed),
        encoding="utf-8",
    )
    return [archive_output, pdf_output, epub_output, notes_output, checksum_output]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="snapshot")
    parser.add_argument("--destination", type=Path, default=ROOT / "output/release")
    args = parser.parse_args()
    for path in package_release(ROOT, args.version, args.destination):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
