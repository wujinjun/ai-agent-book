from pathlib import Path

import pytest

from ai_agent_book.apps.minimal_assistant import (
    AssistantService,
    JsonlConversationStore,
    MockChatModel,
)


@pytest.mark.asyncio
async def test_stream_ends_with_usage(tmp_path: Path) -> None:
    service = AssistantService(MockChatModel(), JsonlConversationStore(tmp_path / "history.jsonl"))
    events = [event async for event in service.chat("hello", session_id="test")]
    assert events[-1].type == "usage"
