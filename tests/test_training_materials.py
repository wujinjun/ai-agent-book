import json
import re
import zipfile
from pathlib import Path

import yaml

from scripts.setup_training_env import build_workspace

ROOT = Path(__file__).parents[1]


def test_training_material_matrix_has_required_deliverables() -> None:
    matrix = yaml.safe_load((ROOT / "notes/training-matrix.yml").read_text(encoding="utf-8"))
    materials = {item["id"]: item for item in matrix["materials"]}
    expected = {
        "instructor-guide",
        "student-lab-manual",
        "assessment-rubric",
        "question-bank",
        "enterprise-cases",
        "workshops",
        "offline-training-pack",
        "common-mistakes",
        "slides",
    }
    assert set(materials) == expected
    for item in materials.values():
        assert item["status"] == "complete", item["id"]
        path = ROOT / item["path"]
        assert path.is_file(), path
        assert path.stat().st_size > 0, path


def test_training_guides_are_substantial_and_visual() -> None:
    required = (
        "instructor-guide.md",
        "student-lab-manual.md",
        "assessment-rubric.md",
        "enterprise-cases.md",
        "workshops.md",
        "offline-training-pack.md",
    )
    for name in required:
        source = (ROOT / "docs/training" / name).read_text(encoding="utf-8")
        assert len(source) >= 1_000, name
        assert "```mermaid" in source or "```text" in source, name


def test_question_bank_covers_all_38_chapters_and_exam() -> None:
    source = (ROOT / "docs/training/question-bank.md").read_text(encoding="utf-8")
    chapter_rows = re.findall(r"^\| (\d{1,2}) \|", source, re.MULTILINE)
    assert [int(number) for number in chapter_rows] == list(range(1, 39))
    assert "## 综合考试（100 分）" in source
    assert "### 综合考试评分要点" in source


def test_offline_training_workspace_is_deterministic(tmp_path: Path) -> None:
    target = tmp_path / "training"
    manifest = build_workspace(target)
    assert manifest["offline_only"] is True
    assert len(manifest["files"]) == 4
    assert all(item["records"] >= 3 for item in manifest["files"])
    written = json.loads((target / "training-manifest.json").read_text(encoding="utf-8"))
    assert written == manifest
    for item in manifest["files"]:
        assert len(item["sha256"]) == 64
        assert (target / item["path"]).is_file()


def test_training_routes_define_time_tasks_outputs_and_checks() -> None:
    guide = (ROOT / "docs/learning-guide.md").read_text(encoding="utf-8")
    for route in ("路线 A：8 周快速入门", "路线 B：12 周系统学习", "路线 C：24 周深入学习"):
        assert route in guide
    for heading in ("时间", "编码任务", "输出成果", "检查标准"):
        assert heading in guide


def test_training_delivery_contract_covers_before_during_after_class() -> None:
    instructor = (ROOT / "docs/training/instructor-guide.md").read_text(encoding="utf-8")
    for evidence in ("## 课前准备", "## 单次课程的标准节奏", "## 课程结束条件"):
        assert evidence in instructor

    student = (ROOT / "docs/training/student-lab-manual.md").read_text(encoding="utf-8")
    assert re.findall(r"\| L(\d{2}) \|", student) == [f"{number:02d}" for number in range(1, 13)]
    for evidence in ("成功测试", "失败", "ADR", "无付费账号运行"):
        assert evidence in student


def test_training_cases_workshops_and_navigation_are_complete() -> None:
    cases = (ROOT / "docs/training/enterprise-cases.md").read_text(encoding="utf-8")
    for case in ("客户服务", "企业知识库", "研发", "办公协作", "合规"):
        assert case in cases

    workshops = (ROOT / "docs/training/workshops.md").read_text(encoding="utf-8")
    for workshop in ("架构评审", "威胁建模", "成本与容量估算"):
        assert workshop in workshops

    mkdocs = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    for page in (
        "training/index.md",
        "training/instructor-guide.md",
        "training/student-lab-manual.md",
        "training/assessment-rubric.md",
        "training/question-bank.md",
        "training/slides.md",
    ):
        assert page in mkdocs


def test_training_deck_has_notes_sources_and_visual_preview() -> None:
    deck = ROOT / "training/slides/ai-agent-engineering-training.pptx"
    preview = ROOT / "docs/assets/training-deck-preview.png"
    assert deck.stat().st_size >= 50_000
    assert preview.stat().st_size >= 100_000

    with zipfile.ZipFile(deck) as archive:
        names = set(archive.namelist())
        slides = {
            name
            for name in names
            if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
        }
        notes = sorted(
            name
            for name in names
            if re.fullmatch(r"ppt/notesSlides/notesSlide\d+\.xml", name)
        )
        assert len(slides) == 16
        assert len(notes) == 16
        for note in notes:
            xml = archive.read(note).decode("utf-8")
            assert "[Sources]" in xml, note

    delivery = (ROOT / "training/slides/README.md").read_text(encoding="utf-8")
    assert "Noto Sans SC" in delivery
    assert "NotoSansSC-Regular.otf" in delivery
    assert "PowerPoint" in delivery and "Keynote" in delivery
