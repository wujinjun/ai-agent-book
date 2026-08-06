"""Run seeded toy sampling and generate CSV/Markdown frequency reports."""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from sampling_lab.domain import SamplingConfig, generate
from sampling_lab.providers import FixedLogitModel
from sampling_lab.reporting import write_reports


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--output", type=Path, default=Path("assets"))
    args = parser.parse_args()

    config = SamplingConfig(
        temperature=0.8,
        top_k=3,
        top_p=0.95,
        max_tokens=8,
        stop_tokens=("<STOP>",),
    )
    result = generate(FixedLogitModel(), config=config, seed=args.seed)
    csv_path, markdown_path = write_reports(args.output)
    print(
        json.dumps(
            {**asdict(result), "csv": str(csv_path), "markdown": str(markdown_path)},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
