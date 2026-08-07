#!/usr/bin/env python3
"""Install and verify every completed P2 example in its own Python 3.12 environment."""

from __future__ import annotations

import argparse
import json
import os
import shlex
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from time import perf_counter
from typing import Any

import yaml

ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "notes" / "example-matrix.yml"


@dataclass(frozen=True)
class ExampleSpec:
    name: str
    offline_command: str
    test_command: str
    complete: bool


@dataclass
class CheckResult:
    example: str
    check: str
    command: list[str]
    duration_seconds: float
    returncode: int
    output_tail: str


def load_examples(path: Path = CATALOG) -> list[ExampleSpec]:
    document: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return [
        ExampleSpec(
            name=str(item["name"]),
            offline_command=str(item["offline_command"]),
            test_command=str(item["test_command"]),
            complete=bool(item["complete"]),
        )
        for item in document["examples"]
    ]


def replace_python(command: str, python: Path) -> list[str]:
    parts = shlex.split(command)
    if not parts or parts[0] not in {"python", "python3", "python3.12"}:
        raise ValueError(f"catalog command must start with Python: {command}")
    return [str(python), *parts[1:]]


def environment_python(venv: Path) -> Path:
    return venv / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")


def run_check(
    *,
    example: str,
    check: str,
    command: list[str],
    cwd: Path,
    env: dict[str, str] | None = None,
    timeout: int = 300,
) -> CheckResult:
    started = perf_counter()
    completed = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    output = (completed.stdout + completed.stderr).strip()
    return CheckResult(
        example=example,
        check=check,
        command=command,
        duration_seconds=round(perf_counter() - started, 3),
        returncode=completed.returncode,
        output_tail=output[-4000:],
    )


def verify_one(
    spec: ExampleSpec,
    *,
    base_python: Path,
    venv_root: Path,
    skip_install: bool,
) -> list[CheckResult]:
    example_root = ROOT / "examples" / spec.name
    venv = venv_root / spec.name
    python = environment_python(venv)
    results: list[CheckResult] = []

    if not python.is_file():
        venv.parent.mkdir(parents=True, exist_ok=True)
        result = run_check(
            example=spec.name,
            check="create_venv",
            command=[str(base_python), "-m", "venv", str(venv)],
            cwd=ROOT,
        )
        results.append(result)
        if result.returncode:
            return results

    if not skip_install:
        result = run_check(
            example=spec.name,
            check="install",
            command=[str(python), "-m", "pip", "install", "-e", f"{example_root}[test]"],
            cwd=ROOT,
            timeout=600,
        )
        results.append(result)
        if result.returncode:
            return results

    run_env = os.environ.copy()
    run_env["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    checks = [
        ("offline", replace_python(spec.offline_command, python)),
        ("tests", replace_python(spec.test_command, python)),
        ("ruff", [str(python), "-m", "ruff", "check", "src", "tests"]),
        ("mypy", [str(python), "-m", "mypy", "src", "tests"]),
    ]
    for check, command in checks:
        result = run_check(
            example=spec.name,
            check=check,
            command=command,
            cwd=example_root,
            env=run_env,
        )
        results.append(result)
        if result.returncode:
            break
    return results


def verify_framework_comparison_drivers(venv_root: Path) -> list[CheckResult]:
    comparison_root = ROOT / "examples" / "framework_comparison"
    comparison_src = comparison_root / "src"
    openai_python = environment_python(venv_root / "openai_agents_sdk")
    pydanticai_python = environment_python(venv_root / "pydanticai_service")
    comparison_python = environment_python(venv_root / "framework_comparison")
    env = os.environ.copy()
    env["MYPYPATH"] = str(comparison_src)
    env["OPENAI_AGENTS_DISABLE_TRACING"] = "1"
    checks = [
        (
            "openai_driver_mypy",
            openai_python,
            comparison_root / "src/framework_comparison/candidates/openai_agents_sdk.py",
        ),
        (
            "pydanticai_driver_mypy",
            pydanticai_python,
            comparison_root / "src/framework_comparison/candidates/pydanticai.py",
        ),
    ]
    results: list[CheckResult] = []
    for name, python, source in checks:
        results.append(
            run_check(
                example="framework_comparison",
                check=name,
                command=[str(python), "-m", "mypy", "--strict", str(source)],
                cwd=ROOT,
                env=env,
            )
        )
    regenerate_env = env.copy()
    regenerate_env["FRAMEWORK_COMPARISON_OPENAI_PYTHON"] = str(openai_python)
    regenerate_env["FRAMEWORK_COMPARISON_PYDANTICAI_PYTHON"] = str(pydanticai_python)
    results.append(
        run_check(
            example="framework_comparison",
            check="regenerate_isolated_evidence",
            command=[
                str(comparison_python),
                "-m",
                "framework_comparison.main",
                "--fixture",
                "research",
                "--regenerate",
                "--runs",
                "5",
            ],
            cwd=comparison_root,
            env=regenerate_env,
        )
    )
    return results


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--python", type=Path, default=Path(shutil.which("python3.12") or ""))
    parser.add_argument("--venv-root", type=Path, default=ROOT / ".venvs" / "examples")
    parser.add_argument("--name", action="append", dest="names")
    parser.add_argument("--skip-install", action="store_true")
    parser.add_argument(
        "--report",
        type=Path,
        default=ROOT / "tmp" / "p2-example-verification.json",
    )
    args = parser.parse_args()

    if not args.python.is_file():
        raise SystemExit("Python 3.12 executable not found; pass --python")
    version = subprocess.run(
        [
            str(args.python),
            "-c",
            "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')",
        ],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.strip()
    if version != "3.12":
        raise SystemExit(f"P2 examples require Python 3.12, got {version}")

    selected = [item for item in load_examples() if item.complete]
    if args.names:
        requested = set(args.names)
        selected = [item for item in selected if item.name in requested]
        missing = requested - {item.name for item in selected}
        if missing:
            raise SystemExit(f"unknown or incomplete examples: {sorted(missing)}")

    results: list[CheckResult] = []
    for spec in selected:
        print(f"[verify] {spec.name}", flush=True)
        example_results = verify_one(
            spec,
            base_python=args.python,
            venv_root=args.venv_root,
            skip_install=args.skip_install,
        )
        results.extend(example_results)
        if any(item.returncode for item in example_results):
            break

    selected_names = {item.name for item in selected}
    if not any(item.returncode for item in results) and {
        "openai_agents_sdk",
        "pydanticai_service",
        "framework_comparison",
    } <= selected_names:
        results.extend(verify_framework_comparison_drivers(args.venv_root))

    payload = {
        "schema_version": 1,
        "python": version,
        "selected": [item.name for item in selected],
        "passed": not any(item.returncode for item in results),
        "checks": [asdict(item) for item in results],
    }
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps({"passed": payload["passed"], "checks": len(results)}), flush=True)
    raise SystemExit(0 if payload["passed"] else 1)


if __name__ == "__main__":
    main()
