#!/usr/bin/env python3
"""Create deterministic publication archives, notes, and SHA-256 manifests."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def resolve_source_commit(root: Path, override: str | None = None) -> str:
    candidate = override or os.environ.get("GITHUB_SHA", "")
    if not candidate:
        candidate = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=root, text=True
        ).strip()
    if re.fullmatch(r"[0-9a-f]{40}", candidate) is None:
        raise RuntimeError(f"invalid source commit: {candidate!r}")
    return candidate


def ensure_clean_worktree(root: Path) -> None:
    result = subprocess.run(
        ["git", "status", "--porcelain", "--untracked-files=all"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"cannot inspect Git worktree: {result.stderr.strip()}")
    dirty = [line for line in result.stdout.splitlines() if line.strip()]
    if dirty:
        preview = ", ".join(dirty[:8])
        raise RuntimeError(
            "release candidate requires a clean Git worktree; commit or remove changes: "
            f"{preview}"
        )


def artifact_record(path: Path, role: str) -> dict[str, Any]:
    return {
        "role": role,
        "file": path.name,
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
    }


def reviewed_candidate_record(root: Path) -> dict[str, str] | None:
    path = root / "external-validation/candidate/release-manifest.json"
    if not path.is_file():
        return None
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"candidate release manifest cannot be read: {exc}") from exc
    if not isinstance(document, dict):
        raise RuntimeError("candidate release manifest must be a JSON object")
    source_commit = document.get("source_commit")
    if not isinstance(source_commit, str) or re.fullmatch(r"[0-9a-f]{40}", source_commit) is None:
        raise RuntimeError("candidate release manifest has an invalid source_commit")
    return {
        "source_commit": source_commit,
        "manifest_sha256": sha256(path),
    }


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


def package_release(
    root: Path,
    version: str,
    destination: Path,
    *,
    source_commit: str | None = None,
    require_clean: bool = True,
) -> list[Path]:
    pdf = root / "output/pdf/ai-agent-book-2026.pdf"
    epub = root / "output/epub/ai-agent-book-2026.epub"
    html = root / "output/html"
    training_pptx = root / "training/slides/ai-agent-engineering-training.pptx"
    changelog = root / "CHANGELOG.md"
    for required in (pdf, epub, html / "index.html", training_pptx, changelog):
        if not required.exists():
            raise RuntimeError(f"release input missing: {required}")

    if require_clean and source_commit is None and not os.environ.get("GITHUB_ACTIONS"):
        ensure_clean_worktree(root)

    safe_version = version.replace("/", "-")
    commit = resolve_source_commit(root, source_commit)
    destination.mkdir(parents=True, exist_ok=True)
    pdf_output = destination / f"ai-agent-book-2026-{safe_version}.pdf"
    epub_output = destination / f"ai-agent-book-2026-{safe_version}.epub"
    pptx_output = destination / f"ai-agent-engineering-training-{safe_version}.pptx"
    notes_output = destination / f"RELEASE_NOTES-{safe_version}.md"
    manifest_output = destination / f"RELEASE_MANIFEST-{safe_version}.json"
    archive_output = destination / f"ai-agent-book-output-{safe_version}.zip"
    checksum_output = destination / f"SHA256SUMS-{safe_version}.txt"
    shutil.copy2(pdf, pdf_output)
    shutil.copy2(epub, epub_output)
    shutil.copy2(training_pptx, pptx_output)
    notes_output.write_text(
        release_notes(changelog.read_text(encoding="utf-8"), version),
        encoding="utf-8",
    )
    manifest_output.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "version": version,
                "source_commit": commit,
                "reviewed_candidate": reviewed_candidate_record(root),
                "artifacts": [
                    artifact_record(pdf_output, "book_pdf"),
                    artifact_record(epub_output, "book_epub"),
                    artifact_record(pptx_output, "training_pptx"),
                    artifact_record(notes_output, "release_notes"),
                ],
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )

    with tempfile.TemporaryDirectory(prefix="ai-agent-book-release-") as directory:
        staging = Path(directory)
        staged_html = staging / "html"
        shutil.copytree(html, staged_html)
        downloads = staged_html / "downloads"
        downloads.mkdir(parents=True, exist_ok=True)
        shutil.copy2(pdf_output, downloads / "ai-agent-book-2026.pdf")
        shutil.copy2(epub_output, downloads / "ai-agent-book-2026.epub")
        shutil.copy2(pdf_output, staging / pdf_output.name)
        shutil.copy2(epub_output, staging / epub_output.name)
        shutil.copy2(pptx_output, staging / pptx_output.name)
        shutil.copy2(notes_output, staging / notes_output.name)
        shutil.copy2(manifest_output, staging / manifest_output.name)
        write_deterministic_zip(staging, archive_output, f"ai-agent-book-{safe_version}")

    checksummed = (
        archive_output,
        pdf_output,
        epub_output,
        pptx_output,
        notes_output,
        manifest_output,
    )
    checksum_output.write_text(
        "".join(f"{sha256(path)}  {path.name}\n" for path in checksummed),
        encoding="utf-8",
    )
    return [
        archive_output,
        pdf_output,
        epub_output,
        pptx_output,
        notes_output,
        manifest_output,
        checksum_output,
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--version", default="snapshot")
    parser.add_argument("--destination", type=Path, default=ROOT / "output/release")
    parser.add_argument("--allow-dirty", action="store_true")
    args = parser.parse_args()
    for path in package_release(
        ROOT,
        args.version,
        args.destination,
        require_clean=not args.allow_dirty,
    ):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
