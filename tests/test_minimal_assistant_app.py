from pathlib import Path

import httpx
import pytest

from ai_agent_book.apps.minimal_assistant import (
    AssistantConfig,
    AssistantService,
    JsonlConversationStore,
    MockChatModel,
    OpenAICompatibleChatModel,
)


@pytest.mark.asyncio
async def test_mock_assistant_streams_and_persists_history(tmp_path: Path) -> None:
    store = JsonlConversationStore(tmp_path / "history.jsonl")
    service = AssistantService(MockChatModel(), store)

    events = [event async for event in service.chat("你好", session_id="s-1")]

    assert events[-1].type == "usage"
    assert events[-1].usage is not None
    assert events[-1].usage.total_tokens > 0
    history = store.load("s-1")
    assert [message.role for message in history] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_openai_compatible_adapter_parses_sse_and_usage() -> None:
    body = (
        'data: {"choices":[{"delta":{"content":"你"}}]}\n\n'
        'data: {"choices":[{"delta":{"content":"好"}}],'
        '"usage":{"prompt_tokens":3,"completion_tokens":2,"total_tokens":5}}\n\n'
        "data: [DONE]\n\n"
    )

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer test-key"
        return httpx.Response(200, text=body, headers={"content-type": "text/event-stream"})

    config = AssistantConfig(
        mode="online",
        base_url="https://model.test/v1",
        api_key="test-key",
        model="test-model",
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        model = OpenAICompatibleChatModel(config, client=client)
        events = [event async for event in model.stream([])]

    assert "".join(event.delta for event in events if event.type == "delta") == "你好"
    assert events[-1].usage is not None
    assert events[-1].usage.total_tokens == 5


def test_config_rejects_online_mode_without_api_key() -> None:
    with pytest.raises(ValueError, match="API key"):
        AssistantConfig(mode="online", api_key=None)
