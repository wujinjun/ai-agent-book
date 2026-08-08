import hashlib
import zipfile
from pathlib import Path

from scripts.package_release import package_release


def test_release_package_contains_site_editions_notes_and_valid_checksums(
    tmp_path: Path,
) -> None:
    (tmp_path / "output/html").mkdir(parents=True)
    (tmp_path / "output/pdf").mkdir(parents=True)
    (tmp_path / "output/epub").mkdir(parents=True)
    (tmp_path / "output/html/index.html").write_text("<h1>book</h1>", encoding="utf-8")
    (tmp_path / "output/pdf/ai-agent-book-2026.pdf").write_bytes(b"pdf")
    (tmp_path / "output/epub/ai-agent-book-2026.epub").write_bytes(b"epub")
    (tmp_path / "CHANGELOG.md").write_text(
        "# 变更记录\n\n## v1.2.3 - 2026-08-08\n\n- 完成验收。\n",
        encoding="utf-8",
    )

    outputs = package_release(tmp_path, "v1.2.3", tmp_path / "release")

    archive, pdf, epub, notes, checksums = outputs
    assert all(path.is_file() for path in outputs)
    assert "完成验收" in notes.read_text(encoding="utf-8")
    with zipfile.ZipFile(archive) as bundle:
        names = set(bundle.namelist())
    assert "ai-agent-book-v1.2.3/html/index.html" in names
    assert f"ai-agent-book-v1.2.3/{pdf.name}" in names
    assert f"ai-agent-book-v1.2.3/{epub.name}" in names
    manifest = checksums.read_text(encoding="utf-8")
    for path in (archive, pdf, epub, notes):
        expected = hashlib.sha256(path.read_bytes()).hexdigest()
        assert f"{expected}  {path.name}" in manifest
