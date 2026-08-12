from pathlib import Path

import pytest

from scripts.verify_examples import environment_python, load_examples, replace_python


def test_orchestrator_loads_all_completed_examples() -> None:
    examples = load_examples()
    assert len(examples) == 13
    assert all(item.complete for item in examples)


def test_catalog_python_command_is_replaced_without_shell() -> None:
    python = Path("/tmp/example/bin/python")
    assert replace_python("python -m package.main --fixture demo", python) == [
        str(python),
        "-m",
        "package.main",
        "--fixture",
        "demo",
    ]
    with pytest.raises(ValueError, match="must start"):
        replace_python("bash run.sh", python)


def test_environment_python_is_platform_specific(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("scripts.verify_examples.sys.platform", "win32")
    assert environment_python(Path("venv")) == Path("venv/Scripts/python.exe")
