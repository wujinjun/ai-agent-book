"""Offline CLI for the chapter 2 token and context-budget experiment."""

import argparse
import json
from dataclasses import asdict

from token_counter.domain import ContextRequest, build_context_plan
from token_counter.providers import Utf8ByteTokenizer, WhitespaceTokenizer


def multilingual_report() -> dict[str, object]:
    byte_counter = Utf8ByteTokenizer()
    samples = {"english": "Agent", "chinese": "智能体", "emoji": "🤖"}
    counts = {name: byte_counter.count(text) for name, text in samples.items()}

    request = ContextRequest(
        instructions="follow policy",
        tool_schema="read tool",
        user_query="answer now",
        history=("old low value message", "recent message"),
        evidence=("best evidence", "secondary evidence"),
        reserved_output_tokens=4,
        max_history_tokens=2,
        max_evidence_tokens=2,
    )
    plan = build_context_plan(
        request,
        model_window=16,
        tokenizer=WhitespaceTokenizer(),
    )
    return {"fixture_counts": counts, "context_plan": asdict(plan)}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("multilingual",), default="multilingual")
    parser.parse_args()
    print(json.dumps(multilingual_report(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
