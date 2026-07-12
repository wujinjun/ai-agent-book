import os
import subprocess
from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_all_ten_project_entry_points_run_on_python_312(tmp_path: Path) -> None:
    environment = {
        **os.environ,
        "PYTHONPATH": str(ROOT / "src"),
        "HISTORY_PATH": str(tmp_path / "history.jsonl"),
        "DATABASE_PATH": str(tmp_path / "platform.db"),
    }
    entries = sorted((ROOT / "projects").glob("[0-9][0-9]-*/main.py"))
    assert len(entries) == 10
    for entry in entries:
        result = subprocess.run(
            [str(ROOT / ".venv/bin/python"), str(entry)],
            cwd=ROOT,
            env=environment,
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.stdout.strip(), f"entry produced no output: {entry}"
