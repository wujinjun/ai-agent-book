"""Score verified framework evidence or explicitly regenerate it."""

import argparse
import json
import os
from pathlib import Path

from framework_comparison.io import (
    EXAMPLE_ROOT,
    dump_evidence,
    load_evidence,
    load_spec,
    verify_evidence_sources,
)
from framework_comparison.regenerate import collect
from framework_comparison.scoring import compare_candidates, render_adr


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("research",), default="research")
    parser.add_argument("--regenerate", action="store_true")
    parser.add_argument("--runs", type=int, default=20)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()

    evidence_path = EXAMPLE_ROOT / "fixtures" / "verified-evidence.json"
    if args.regenerate:
        openai_python = Path(os.environ["FRAMEWORK_COMPARISON_OPENAI_PYTHON"])
        pydanticai_python = Path(os.environ["FRAMEWORK_COMPARISON_PYDANTICAI_PYTHON"])
        evidence = collect(
            openai_python=openai_python,
            pydanticai_python=pydanticai_python,
            runs=args.runs,
        )
        if args.write:
            dump_evidence(evidence_path, evidence)
    else:
        evidence = load_evidence(evidence_path)

    verify_evidence_sources(evidence)
    result = compare_candidates(load_spec(), evidence)
    print(json.dumps(result.model_dump(mode="json"), ensure_ascii=False, indent=2))
    if args.write:
        (EXAMPLE_ROOT / "ADR.md").write_text(render_adr(result, evidence), encoding="utf-8")


if __name__ == "__main__":
    main()
