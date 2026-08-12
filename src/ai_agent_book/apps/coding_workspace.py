"""项目 9：一次性 Git 工作区、补丁策略和受限测试执行边界。"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from pydantic import BaseModel, Field


class WorkspacePolicyError(ValueError):
    """工作区或补丁违反本地执行策略。"""


@dataclass(frozen=True, slots=True)
class WorkspacePolicy:
    max_patch_bytes: int = 500_000
    max_changed_files: int = 100
    test_timeout_seconds: int = 60
    allowed_commands: tuple[tuple[str, ...], ...] = (
        ("python", "-m", "pytest", "-q"),
        ("python", "-m", "compileall", "-q", "."),
    )


class TestExecution(BaseModel):
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    output_truncated: bool = False


class PatchExecution(BaseModel):
    changed_files: list[str] = Field(default_factory=list)
    test: TestExecution | None = None
    kept: bool


def _patch_paths(patch: str) -> list[str]:
    paths: list[str] = []
    for raw in patch.splitlines():
        if not raw.startswith("+++ "):
            continue
        value = raw[4:].split("\t", 1)[0]
        if value == "/dev/null":
            continue
        value = value.removeprefix("b/")
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not value or "\x00" in value:
            raise WorkspacePolicyError("patch contains unsafe path")
        if not re.fullmatch(r"[A-Za-z0-9_./@+ -]+", value):
            raise WorkspacePolicyError("patch path contains unsupported characters")
        paths.append(value)
    return sorted(set(paths))


class RepositoryWorkspace:
    """在一次性本地克隆中执行补丁；不会直接修改源仓库。"""

    def __init__(
        self,
        source: Path,
        workspace: Path,
        *,
        policy: WorkspacePolicy | None = None,
    ) -> None:
        self.source = source.resolve()
        self.workspace = workspace.resolve()
        self.policy = policy or WorkspacePolicy()
        self._active = False
        if not (self.source / ".git").exists():
            raise WorkspacePolicyError("source is not a Git repository")
        if self.workspace == self.source or self.source in self.workspace.parents:
            raise WorkspacePolicyError("workspace must not be inside the source repository")

    def create(self) -> Path:
        if self.workspace.exists():
            raise WorkspacePolicyError("workspace already exists")
        self.workspace.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            ["git", "clone", "--quiet", "--no-hardlinks", str(self.source), str(self.workspace)],
            check=True,
            capture_output=True,
            timeout=30,
        )
        self._active = True
        return self.workspace

    def apply(self, patch: str) -> list[str]:
        self._require_active()
        if len(patch.encode()) > self.policy.max_patch_bytes:
            raise WorkspacePolicyError("patch exceeds byte budget")
        paths = _patch_paths(patch)
        if not paths:
            raise WorkspacePolicyError("patch changes no files")
        if len(paths) > self.policy.max_changed_files:
            raise WorkspacePolicyError("patch exceeds file budget")
        payload = patch.encode()
        subprocess.run(
            ["git", "apply", "--check", "--whitespace=error-all", "-"],
            cwd=self.workspace,
            input=payload,
            check=True,
            capture_output=True,
            timeout=10,
        )
        subprocess.run(
            ["git", "apply", "--whitespace=error-all", "-"],
            cwd=self.workspace,
            input=payload,
            check=True,
            capture_output=True,
            timeout=10,
        )
        return paths

    def run_tests(self, command: tuple[str, ...]) -> TestExecution:
        self._require_active()
        if command not in self.policy.allowed_commands:
            raise WorkspacePolicyError("test command is not allowlisted")
        executable = os.path.basename(command[0])
        resolved = (
            sys.executable if executable in {"python", "python3"} else shutil.which(executable)
        )
        if resolved is None:
            raise WorkspacePolicyError(f"test executable is unavailable: {executable}")
        actual = [resolved, *command[1:]]
        safe_env = {
            "PATH": os.environ.get("PATH", ""),
            "HOME": str(self.workspace),
            "PYTHONPATH": str(self.workspace),
            "PYTHONDONTWRITEBYTECODE": "1",
            "NO_PROXY": "",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
        }
        try:
            completed = subprocess.run(
                actual,
                cwd=self.workspace,
                env=safe_env,
                capture_output=True,
                text=True,
                timeout=self.policy.test_timeout_seconds,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return TestExecution(
                command=list(command),
                returncode=124,
                stdout=_bounded_output(exc.stdout or "")[0],
                stderr=_bounded_output(exc.stderr or "")[0],
                timed_out=True,
            )
        stdout, stdout_truncated = _bounded_output(completed.stdout)
        stderr, stderr_truncated = _bounded_output(completed.stderr)
        return TestExecution(
            command=list(command),
            returncode=completed.returncode,
            stdout=stdout,
            stderr=stderr,
            output_truncated=stdout_truncated or stderr_truncated,
        )

    def execute_patch(
        self,
        patch: str,
        *,
        test_command: tuple[str, ...],
        keep_on_success: bool = True,
    ) -> PatchExecution:
        if not self._active:
            self.create()
        try:
            changed = self.apply(patch)
            test = self.run_tests(test_command)
        except Exception:
            self.rollback()
            raise
        if test.returncode != 0:
            self.rollback()
            return PatchExecution(changed_files=changed, test=test, kept=False)
        if not keep_on_success:
            self.rollback()
            return PatchExecution(changed_files=changed, test=test, kept=False)
        return PatchExecution(changed_files=changed, test=test, kept=True)

    def rollback(self) -> None:
        """销毁一次性克隆，使补丁和测试副作用一起消失。"""
        if self.workspace.exists():
            shutil.rmtree(self.workspace)
        self._active = False

    def _require_active(self) -> None:
        if not self._active or not self.workspace.exists():
            raise WorkspacePolicyError("workspace has not been created")


def _bounded_output(value: str | bytes, limit: int = 20_000) -> tuple[str, bool]:
    text = value.decode(errors="replace") if isinstance(value, bytes) else value
    if len(text) <= limit:
        return text, False
    return text[:limit] + "\n...[truncated]", True
