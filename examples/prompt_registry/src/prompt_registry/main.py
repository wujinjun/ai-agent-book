"""Publish two prompt versions, run a rollout and demonstrate rollback."""

import argparse
import json
import tempfile
from pathlib import Path

from prompt_registry.domain import PromptSpec
from prompt_registry.providers import DeterministicPromptModel
from prompt_registry.registry import FilePromptRegistry


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("support",), default="support")
    args = parser.parse_args()
    del args
    with tempfile.TemporaryDirectory() as directory:
        registry = FilePromptRegistry(Path(directory))
        for version, template in (
            ("1.0.0", "分类：{ticket}"),
            ("1.1.0", "请分类：{ticket}"),
        ):
            registry.publish(PromptSpec.create("support", version, template, ("ticket",)))
        registry.activate("support", "1.0.0", traffic_percent=100)
        registry.activate("support", "1.1.0", traffic_percent=25)
        selected = registry.select("support", "demo-user")
        result = DeterministicPromptModel().run(selected.render({"ticket": "退款失败"}))
        before = selected.version
        registry.rollback("support")
        after = registry.select("support", "demo-user").version
        print(
            json.dumps(
                {"selected": before, "result": result, "rollback": after},
                ensure_ascii=False,
            )
        )


if __name__ == "__main__":
    main()
