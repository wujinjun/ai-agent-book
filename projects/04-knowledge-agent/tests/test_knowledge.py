from pathlib import Path

from ai_agent_book.apps.knowledge_agent import KnowledgeBase


def test_empty_index_refuses_to_answer(tmp_path: Path) -> None:
    assert KnowledgeBase().answer("unknown", tenant_id="t").citations == []
