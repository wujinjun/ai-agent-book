#!/usr/bin/env python3
"""Build a fail-closed P9 external-validation kit from a frozen release manifest."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import zipfile
from datetime import date
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
TEMPLATES = ROOT / "external-validation/templates"
PROTOCOL_FILES = (
    ROOT / "external-validation/README.md",
    ROOT / "external-validation/independent-review-packet.md",
    ROOT / "external-validation/device-print-protocol.md",
    ROOT / "external-validation/rights-review-protocol.md",
    ROOT / "training/p9-trial-protocol.md",
)
REQUIRED_ARTIFACT_ROLES = {
    "book_pdf",
    "book_epub",
    "training_pptx",
    "release_notes",
}
INDEPENDENT_ROLES = {
    "agent_engineer": "review-agent-engineer-001",
    "python_engineer": "review-python-engineer-001",
    "chinese_editor": "review-chinese-editor-001",
}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _load_manifest(path: Path) -> dict[str, Any]:
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"cannot read release manifest: {exc}") from exc
    if not isinstance(document, dict) or document.get("schema_version") != 1:
        raise RuntimeError("release manifest must be a schema_version 1 object")
    commit = document.get("source_commit")
    if (
        not isinstance(commit, str)
        or re.fullmatch(r"[0-9a-f]{40}", commit) is None
        or set(commit) == {"0"}
    ):
        raise RuntimeError("release manifest has an invalid source_commit")
    artifacts = document.get("artifacts")
    if not isinstance(artifacts, list):
        raise RuntimeError("release manifest artifacts must be a list")
    roles = {
        item.get("role")
        for item in artifacts
        if isinstance(item, dict) and isinstance(item.get("role"), str)
    }
    if roles != REQUIRED_ARTIFACT_ROLES or len(artifacts) != len(REQUIRED_ARTIFACT_ROLES):
        raise RuntimeError(
            "release manifest must contain exactly these artifact roles: "
            f"{sorted(REQUIRED_ARTIFACT_ROLES)}"
        )
    return document


def _verify_artifacts(manifest_path: Path, document: dict[str, Any]) -> list[Path]:
    verified: list[Path] = []
    seen_files: set[str] = set()
    for index, item in enumerate(document["artifacts"]):
        if not isinstance(item, dict):
            raise RuntimeError(f"release manifest artifact {index} must be an object")
        filename = item.get("file")
        expected_size = item.get("bytes")
        expected_hash = item.get("sha256")
        if (
            not isinstance(filename, str)
            or Path(filename).name != filename
            or filename in {"", ".", ".."}
            or filename in seen_files
        ):
            raise RuntimeError(f"release manifest artifact {index} has an unsafe file name")
        seen_files.add(filename)
        path = manifest_path.parent / filename
        if not path.is_file():
            raise RuntimeError(f"release artifact is missing: {path}")
        if (
            not isinstance(expected_size, int)
            or isinstance(expected_size, bool)
            or path.stat().st_size != expected_size
        ):
            raise RuntimeError(f"release artifact byte size mismatch: {filename}")
        if not isinstance(expected_hash, str) or sha256(path) != expected_hash:
            raise RuntimeError(f"release artifact SHA-256 mismatch: {filename}")
        verified.append(path)
    return verified


def _verify_release_bundle(manifest_path: Path, document: dict[str, Any]) -> tuple[Path, Path]:
    version = document.get("version")
    if not isinstance(version, str) or not version.strip():
        raise RuntimeError("release manifest has an invalid version")
    safe_version = version.replace("/", "-")
    archive = manifest_path.parent / f"ai-agent-book-output-{safe_version}.zip"
    checksums = manifest_path.parent / f"SHA256SUMS-{safe_version}.txt"
    if not archive.is_file() or not checksums.is_file():
        raise RuntimeError("release HTML bundle or checksum file is missing")
    entries: dict[str, str] = {}
    for line in checksums.read_text(encoding="utf-8").splitlines():
        digest, separator, filename = line.partition("  ")
        if separator and re.fullmatch(r"[0-9a-f]{64}", digest):
            entries[filename] = digest
    if entries.get(archive.name) != sha256(archive):
        raise RuntimeError("release HTML bundle SHA-256 mismatch")
    if entries.get(manifest_path.name) != sha256(manifest_path):
        raise RuntimeError("release manifest SHA-256 mismatch in checksum file")
    with zipfile.ZipFile(archive) as bundle:
        names = bundle.namelist()
        if not any(name.endswith("/html/index.html") for name in names):
            raise RuntimeError("release HTML bundle has no html/index.html")
        for item in document["artifacts"]:
            filename = str(item["file"])
            matches = [name for name in names if name.endswith(f"/{filename}")]
            if len(matches) != 1:
                raise RuntimeError(f"release bundle must contain one {filename}")
            payload = bundle.read(matches[0])
            if (
                len(payload) != item["bytes"]
                or hashlib.sha256(payload).hexdigest() != item["sha256"]
            ):
                raise RuntimeError(f"release bundle artifact mismatch: {filename}")
    return archive, checksums


def _git_output(root: Path, *arguments: str) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        raise RuntimeError(f"git {' '.join(arguments)} failed: {result.stderr.strip()}")
    return result.stdout.strip()


def _verify_repository_candidate(root: Path, source_commit: str) -> None:
    if _git_output(root, "status", "--porcelain", "--untracked-files=all"):
        raise RuntimeError("external-validation kit requires a clean Git worktree")
    head = _git_output(root, "rev-parse", "HEAD")
    if source_commit != head:
        raise RuntimeError(f"release manifest targets {source_commit}, but current HEAD is {head}")


def _write_yaml(path: Path, document: dict[str, Any]) -> None:
    path.write_text(
        yaml.safe_dump(document, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )


def _bound_template(
    source: Path,
    *,
    source_commit: str,
    manifest_hash: str,
) -> dict[str, Any]:
    document = yaml.safe_load(source.read_text(encoding="utf-8"))
    if not isinstance(document, dict):
        raise RuntimeError(f"evidence template must be a mapping: {source}")
    document["checked_at"] = date.today().isoformat()
    document["source_commit"] = source_commit
    document["candidate_manifest_sha256"] = manifest_hash
    return document


def _write_evidence_templates(
    destination: Path,
    *,
    source_commit: str,
    manifest_hash: str,
) -> None:
    destination.mkdir(parents=True)
    review_source = TEMPLATES / "independent-review.yml"
    for role, record_id in INDEPENDENT_ROLES.items():
        document = _bound_template(
            review_source,
            source_commit=source_commit,
            manifest_hash=manifest_hash,
        )
        document["role"] = role
        document["record_id"] = record_id
        document["reviewer_id"] = f"anonymous-{role.replace('_', '-')}-reviewer"
        _write_yaml(destination / f"{record_id}.yml", document)

    for template_name, output_name in (
        ("learner-trial.yml", "learner-trial-001.yml"),
        ("enterprise-pilot.yml", "enterprise-pilot-001.yml"),
        ("device-print-qa.yml", "device-print-qa-001.yml"),
        ("rights-review.yml", "rights-review-001.yml"),
    ):
        document = _bound_template(
            TEMPLATES / template_name,
            source_commit=source_commit,
            manifest_hash=manifest_hash,
        )
        _write_yaml(destination / output_name, document)


def _write_kit_readme(destination: Path, source_commit: str, manifest_hash: str) -> None:
    destination.write_text(
        f"""# P9 外部验收候选执行包

候选 commit：`{source_commit}`  
候选清单 SHA-256：`{manifest_hash}`

`evidence/` 中七份 YAML 已绑定候选，但所有人工结论和测量值保持默认失败状态。
审阅者必须依据 `protocols/` 中的协议完成真实活动后填写，不得直接把布尔值改成通过。
身份、签字、电话、邮箱、合同和法律意见正文保存在受控系统，不写入本包或公开仓库。
`artifacts/` 中的候选 ZIP 解压后包含可直接打开的 `html/index.html`、PDF、EPUB、
培训 PPTX、发行说明和候选清单。

完成后，把匿名 YAML 交给维护者，执行：

```bash
.venv/bin/python scripts/validate_external_evidence.py \
  external-validation/evidence \
  --expected-source-commit {source_commit}
```

`structurally_valid=True` 只表示结构有效；只有 `complete=True` 才表示七份证据达到机器阈值。
""",
        encoding="utf-8",
    )


def _write_kit_manifest(destination: Path, source_commit: str, release_hash: str) -> Path:
    manifest_path = destination / "KIT_MANIFEST.json"
    files = []
    for path in sorted(item for item in destination.rglob("*") if item.is_file()):
        if path == manifest_path:
            continue
        files.append(
            {
                "file": path.relative_to(destination).as_posix(),
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )
    document = {
        "schema_version": 1,
        "source_commit": source_commit,
        "release_manifest_sha256": release_hash,
        "files": files,
    }
    manifest_path.write_text(
        json.dumps(document, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest_path


def _write_reproducible_zip(destination: Path) -> Path:
    archive = destination.with_suffix(".zip")
    root_name = destination.name
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in sorted(item for item in destination.rglob("*") if item.is_file()):
            info = zipfile.ZipInfo(f"{root_name}/{path.relative_to(destination).as_posix()}")
            info.date_time = (1980, 1, 1, 0, 0, 0)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            output.writestr(info, path.read_bytes())
    return archive


def prepare_kit(
    root: Path,
    release_manifest: Path,
    destination: Path,
    *,
    enforce_repository: bool = True,
) -> tuple[Path, Path]:
    document = _load_manifest(release_manifest)
    source_commit = str(document["source_commit"])
    _verify_artifacts(release_manifest, document)
    html_bundle, checksums = _verify_release_bundle(release_manifest, document)
    if enforce_repository:
        _verify_repository_candidate(root, source_commit)

    if destination.exists():
        shutil.rmtree(destination)
    destination.mkdir(parents=True)
    artifacts_dir = destination / "artifacts"
    candidate_dir = destination / "candidate"
    protocols_dir = destination / "protocols"
    artifacts_dir.mkdir()
    candidate_dir.mkdir()
    protocols_dir.mkdir()

    copied_manifest = candidate_dir / "release-manifest.json"
    shutil.copy2(release_manifest, copied_manifest)
    manifest_hash = sha256(copied_manifest)
    shutil.copy2(html_bundle, artifacts_dir / html_bundle.name)
    shutil.copy2(checksums, candidate_dir / checksums.name)
    for protocol in PROTOCOL_FILES:
        relative = protocol.relative_to(ROOT).as_posix().replace("/", "__")
        shutil.copy2(protocol, protocols_dir / relative)

    _write_evidence_templates(
        destination / "evidence",
        source_commit=source_commit,
        manifest_hash=manifest_hash,
    )
    _write_kit_readme(destination / "README.md", source_commit, manifest_hash)
    _write_kit_manifest(destination, source_commit, manifest_hash)
    archive = _write_reproducible_zip(destination)
    return destination, archive


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("release_manifest", type=Path)
    parser.add_argument(
        "--destination",
        type=Path,
        default=ROOT / "output/external-validation-kit",
    )
    args = parser.parse_args()
    destination, archive = prepare_kit(ROOT, args.release_manifest, args.destination)
    print(destination)
    print(archive)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
