from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parent


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(python: Path, module: str, cwd: Path) -> dict[str, Any]:
    completed = subprocess.run(
        [str(python), "-m", module],
        cwd=cwd,
        text=True,
        capture_output=True,
        timeout=30,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"{module} failed: {completed.stderr[-500:]}")
    return dict(json.loads(completed.stdout))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--langchain-python", type=Path, required=True)
    parser.add_argument("--llamaindex-python", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=ROOT / "evidence.json")
    args = parser.parse_args()
    candidates = [
        _run(args.langchain_python, "rag_spike_langchain.main", ROOT / "langchain"),
        _run(args.llamaindex_python, "rag_spike_llamaindex.main", ROOT / "llamaindex"),
    ]
    evidence = {
        "schema_version": 1,
        "fixture_sha256": _sha256(ROOT / "spec.json"),
        "candidate_source_sha256": {
            "langchain": _sha256(ROOT / "langchain/src/rag_spike_langchain/main.py"),
            "llamaindex": _sha256(ROOT / "llamaindex/src/rag_spike_llamaindex/main.py"),
        },
        "candidates": candidates,
        "passed": all(candidate["passed"] for candidate in candidates),
        "scope": "offline deterministic retrieval and tenant ACL; no LLM generation",
    }
    args.output.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(evidence, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()

