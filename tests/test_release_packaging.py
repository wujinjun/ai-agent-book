import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

import pytest
import yaml

from scripts.package_release import package_release, release_notes
from scripts.prepare_external_validation_kit import prepare_kit
from scripts.validate_external_evidence import validate_directory


def test_release_package_contains_site_editions_notes_and_valid_checksums(
    tmp_path: Path,
) -> None:
    (tmp_path / "output/html").mkdir(parents=True)
    (tmp_path / "output/pdf").mkdir(parents=True)
    (tmp_path / "output/epub").mkdir(parents=True)
    (tmp_path / "output/html/downloads").mkdir(parents=True)
    (tmp_path / "training/slides").mkdir(parents=True)
    (tmp_path / "external-validation/candidate").mkdir(parents=True)
    (tmp_path / "output/html/index.html").write_text("<h1>book</h1>", encoding="utf-8")
    (tmp_path / "output/pdf/ai-agent-book-2026.pdf").write_bytes(b"pdf")
    (tmp_path / "output/epub/ai-agent-book-2026.epub").write_bytes(b"epub")
    (tmp_path / "output/html/downloads/ai-agent-book-2026.pdf").write_bytes(b"stale-pdf")
    (tmp_path / "output/html/downloads/ai-agent-book-2026.epub").write_bytes(b"stale-epub")
    (tmp_path / "training/slides/ai-agent-engineering-training.pptx").write_bytes(b"pptx")
    (tmp_path / "CHANGELOG.md").write_text(
        "# 变更记录\n\n## v1.2.3 - 2026-08-08\n\n- 完成验收。\n",
        encoding="utf-8",
    )

    source_commit = "1" * 40
    candidate_source_commit = "2" * 40
    candidate_manifest = tmp_path / "external-validation/candidate/release-manifest.json"
    candidate_manifest.write_text(
        json.dumps({"source_commit": candidate_source_commit}) + "\n",
        encoding="utf-8",
    )
    outputs = package_release(
        tmp_path,
        "v1.2.3",
        tmp_path / "release",
        source_commit=source_commit,
    )

    archive, pdf, epub, pptx, notes, release_manifest, checksums = outputs
    assert all(path.is_file() for path in outputs)
    assert "完成验收" in notes.read_text(encoding="utf-8")
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
        bundled_pdf = bundle.read("ai-agent-book-v1.2.3/html/downloads/ai-agent-book-2026.pdf")
        bundled_epub = bundle.read("ai-agent-book-v1.2.3/html/downloads/ai-agent-book-2026.epub")
    assert "ai-agent-book-v1.2.3/html/index.html" in names
    assert f"ai-agent-book-v1.2.3/{pdf.name}" in names
    assert f"ai-agent-book-v1.2.3/{epub.name}" in names
    assert f"ai-agent-book-v1.2.3/{pptx.name}" in names
    assert f"ai-agent-book-v1.2.3/{release_manifest.name}" in names
    assert bundled_pdf == b"pdf"
    assert bundled_epub == b"epub"

    release = json.loads(release_manifest.read_text(encoding="utf-8"))
    assert release["source_commit"] == source_commit
    assert release["reviewed_candidate"] == {
        "source_commit": candidate_source_commit,
        "manifest_sha256": hashlib.sha256(candidate_manifest.read_bytes()).hexdigest(),
    }
    assert {item["role"] for item in release["artifacts"]} == {
        "book_pdf",
        "book_epub",
        "training_pptx",
        "release_notes",
    }
    for item in release["artifacts"]:
        path = tmp_path / "release" / item["file"]
        assert item["bytes"] == path.stat().st_size
        assert item["sha256"] == hashlib.sha256(path.read_bytes()).hexdigest()

    manifest = checksums.read_text(encoding="utf-8")
    for path in (archive, pdf, epub, pptx, notes, release_manifest):
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        assert f"{expected}  {path.name}" in manifest


def test_release_candidate_notes_fall_back_to_unreleased_section() -> None:
    changelog = "# 变更记录\n\n## Unreleased\n\n- 完成候选版视觉验收。\n\n## v1.0.0\n"

    notes = release_notes(changelog, "2026-08-13-rc2")

    assert "## Unreleased" in notes
    assert "完成候选版视觉验收" in notes
    assert "## v1.0.0" not in notes


def test_local_release_candidate_rejects_a_dirty_git_worktree(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "output/html").mkdir(parents=True)
    (tmp_path / "output/pdf").mkdir(parents=True)
    (tmp_path / "output/epub").mkdir(parents=True)
    (tmp_path / "training/slides").mkdir(parents=True)
    (tmp_path / "output/html/index.html").write_text("<h1>book</h1>", encoding="utf-8")
    (tmp_path / "output/pdf/ai-agent-book-2026.pdf").write_bytes(b"pdf")
    (tmp_path / "output/epub/ai-agent-book-2026.epub").write_bytes(b"epub")
    (tmp_path / "training/slides/ai-agent-engineering-training.pptx").write_bytes(b"pptx")
    changelog = tmp_path / "CHANGELOG.md"
    changelog.write_text("# changes\n", encoding="utf-8")
    (tmp_path / ".gitignore").write_text("output/\n", encoding="utf-8")

    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.invalid"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(
        ["git", "add", ".gitignore", "CHANGELOG.md", "training"],
        cwd=tmp_path,
        check=True,
    )
    subprocess.run(["git", "commit", "-qm", "candidate"], cwd=tmp_path, check=True)
    repository_head = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
    ).strip()
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    monkeypatch.setenv("GITHUB_SHA", "f" * 40)

    clean_release = tmp_path / "output/release-clean"
    package_release(tmp_path, "clean", clean_release)
    release_manifest = next(clean_release.glob("RELEASE_MANIFEST-*.json"))
    release_document = json.loads(release_manifest.read_text(encoding="utf-8"))
    assert release_document["source_commit"] == repository_head
    kit, archive = prepare_kit(
        tmp_path,
        release_manifest,
        tmp_path / "output/external-validation-kit",
    )
    first_archive_hash = hashlib.sha256(archive.read_bytes()).hexdigest()
    assert len(list((kit / "evidence").glob("*.yml"))) == 7
    assert len(list((kit / "artifacts").glob("ai-agent-book-output-*.zip"))) == 1
    assert len(list((kit / "artifacts").iterdir())) == 1
    assert len(list((kit / "candidate").glob("SHA256SUMS-*.txt"))) == 1
    for evidence_path in (kit / "evidence").glob("*.yml"):
        evidence = yaml.safe_load(evidence_path.read_text(encoding="utf-8"))
        assert (
            evidence["source_commit"]
            == subprocess.check_output(
                ["git", "rev-parse", "HEAD"], cwd=tmp_path, text=True
            ).strip()
        )
        assert set(evidence["candidate_manifest_sha256"]) != {"0"}
    validation = validate_directory(
        kit / "evidence",
        candidate_manifest=kit / "candidate/release-manifest.json",
    )
    assert validation["valid"] is False
    assert validation["complete"] is False
    _, rebuilt_archive = prepare_kit(
        tmp_path,
        release_manifest,
        tmp_path / "output/external-validation-kit",
    )
    assert hashlib.sha256(rebuilt_archive.read_bytes()).hexdigest() == first_archive_hash

    released_pdf = next(clean_release.glob("*.pdf"))
    original_pdf = released_pdf.read_bytes()
    released_pdf.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="artifact .* mismatch"):
        prepare_kit(
            tmp_path,
            release_manifest,
            tmp_path / "output/external-validation-kit",
        )
    released_pdf.write_bytes(original_pdf)

    changelog.write_text("# changed after candidate\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="clean Git worktree"):
        package_release(tmp_path, "dirty", tmp_path / "output/release-dirty")
