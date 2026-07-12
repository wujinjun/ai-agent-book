"""项目 4 入口：导入 Markdown 并输出带来源引用的离线回答。"""

import argparse
import json
from pathlib import Path

from ai_agent_book.apps.knowledge_agent import KnowledgeBase


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "document",
        nargs="?",
        type=Path,
        default=Path("docs/part-02-agent-core/ch09-agent-runtime.md"),
    )
    parser.add_argument("--query", default="Agent Runtime 如何管理工具循环？")
    args = parser.parse_args()
    kb = KnowledgeBase()
    kb.ingest(args.document, tenant_id="demo")
    answer = kb.answer(args.query, tenant_id="demo")
    print(json.dumps(answer.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
