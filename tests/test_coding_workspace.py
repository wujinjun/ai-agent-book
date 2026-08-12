import subprocess
from pathlib import Path

import pytest

from ai_agent_book.apps.coding_workspace import (
    RepositoryWorkspace,
    WorkspacePolicy,
    WorkspacePolicyError,
)


def _repository(tmp_path: Path) -> Path:
    repository = tmp_path / "source"
    repository.mkdir()
    subprocess.run(["git", "init", "-q"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.email", "test@example.test"], cwd=repository, check=True)
    subprocess.run(["git", "config", "user.name", "Test"], cwd=repository, check=True)
    (repository / "answer.py").write_text("VALUE = 1\n", encoding="utf-8")
    subprocess.run(["git", "add", "answer.py"], cwd=repository, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=repository, check=True)
    return repository


def _patch(old: str, new: str) -> str:
    return (
        "diff --git a/answer.py b/answer.py\n"
        "index 624c9de..52ea9ad 100644\n"
        "--- a/answer.py\n"
        "+++ b/answer.py\n"
        "@@ -1 +1 @@\n"
        f"-{old}\n"
        f"+{new}\n"
    )


def test_patch_runs_allowlisted_check_in_disposable_clone(tmp_path: Path) -> None:
    source = _repository(tmp_path)
    policy = WorkspacePolicy(allowed_commands=(("python", "-m", "compileall", "-q", "."),))
    workspace = RepositoryWorkspace(source, tmp_path / "sandbox", policy=policy)

    result = workspace.execute_patch(
        _patch("VALUE = 1", "VALUE = 2"),
        test_command=("python", "-m", "compileall", "-q", "."),
    )

    assert result.kept and result.test is not None and result.test.returncode == 0
    assert (tmp_path / "sandbox" / "answer.py").read_text() == "VALUE = 2\n"
    assert (source / "answer.py").read_text() == "VALUE = 1\n"


def test_failed_test_destroys_workspace_and_preserves_source(tmp_path: Path) -> None:
    source = _repository(tmp_path)
    command = ("python", "-c", "raise SystemExit(3)")
    workspace = RepositoryWorkspace(
        source,
        tmp_path / "sandbox",
        policy=WorkspacePolicy(allowed_commands=(command,)),
    )

    result = workspace.execute_patch(_patch("VALUE = 1", "VALUE = 2"), test_command=command)

    assert result.kept is False
    assert result.test is not None and result.test.returncode == 3
    assert not (tmp_path / "sandbox").exists()
    assert (source / "answer.py").read_text() == "VALUE = 1\n"


def test_workspace_rejects_unsafe_path_and_non_allowlisted_command(tmp_path: Path) -> None:
    source = _repository(tmp_path)
    workspace = RepositoryWorkspace(source, tmp_path / "sandbox")
    workspace.create()
    unsafe = _patch("VALUE = 1", "VALUE = 2").replace("b/answer.py", "b/../answer.py")

    with pytest.raises(WorkspacePolicyError, match="unsafe path"):
        workspace.apply(unsafe)
    with pytest.raises(WorkspacePolicyError, match="allowlisted"):
        workspace.run_tests(("sh", "-c", "true"))

    workspace.rollback()
