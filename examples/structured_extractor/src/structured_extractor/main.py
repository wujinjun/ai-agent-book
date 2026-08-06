"""Run a fully offline typed incident extraction fixture."""

import argparse
import json

from structured_extractor.domain import Extractor
from structured_extractor.providers import DeterministicIncidentProvider


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("incident",), default="incident")
    args = parser.parse_args()
    del args
    result = Extractor(DeterministicIncidentProvider()).extract(
        "支付服务发生严重超时，标题：支付超时"
    )
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
