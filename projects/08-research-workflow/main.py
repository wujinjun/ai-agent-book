"""项目 8 入口：运行真实 LangGraph，暂停后用 Command 恢复。"""

import json

from langgraph.types import Command

from ai_agent_book.apps.langgraph_research import FixtureSearchProvider, build_research_graph


def main() -> None:
    graph = build_research_graph(
        FixtureSearchProvider(
            [
                {
                    "title": "Checkpoint",
                    "url": "https://example.test/checkpoint",
                    "content": "Checkpoint 保存持久状态。",
                },
                {
                    "title": "Interrupt",
                    "url": "https://example.test/interrupt",
                    "content": "Interrupt 支持人工确认后恢复。",
                },
            ]
        )
    )
    config = {"configurable": {"thread_id": "demo-research"}}
    paused = graph.invoke({"topic": "如何恢复长任务？"}, config)
    print(json.dumps(paused, ensure_ascii=False, indent=2, default=str))
    completed = graph.invoke(Command(resume={"approved": True}), config)
    print(json.dumps(completed, ensure_ascii=False, indent=2, default=str))


if __name__ == "__main__":
    main()
