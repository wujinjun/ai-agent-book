"""项目 1：带在线适配器、流式事件、Usage 和持久历史的最小助手。"""

from __future__ import annotations

import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field, model_validator


class AssistantConfig(BaseModel):
    mode: Literal["offline", "online"] = "offline"
    base_url: str = "https://api.openai.com/v1"
    api_key: str | None = None
    model: str = "gpt-4.1-mini"
    timeout_seconds: float = Field(default=30, gt=0, le=300)
    history_path: Path = Path(".data/assistant-history.jsonl")

    @model_validator(mode="after")
    def require_online_key(self) -> AssistantConfig:
        if self.mode == "online" and not self.api_key:
            raise ValueError("online mode requires an API key")
        return self

    @classmethod
    def from_env(cls) -> AssistantConfig:
        return cls(
            mode=os.getenv("APP_MODE", "offline"),  # type: ignore[arg-type]
            base_url=os.getenv("MODEL_BASE_URL", "https://api.openai.com/v1"),
            api_key=os.getenv("MODEL_API_KEY"),
            model=os.getenv("MODEL_NAME", "gpt-4.1-mini"),
            timeout_seconds=float(os.getenv("MODEL_TIMEOUT_SECONDS", "30")),
            history_path=Path(os.getenv("HISTORY_PATH", ".data/assistant-history.jsonl")),
        )


class ChatMessage(BaseModel):
    session_id: str
    role: Literal["user", "assistant"]
    content: str


class TokenUsage(BaseModel):
    prompt_tokens: int = Field(ge=0)
    completion_tokens: int = Field(ge=0)
    total_tokens: int = Field(ge=0)


class ChatEvent(BaseModel):
    type: Literal["delta", "usage", "error"]
    delta: str = ""
    usage: TokenUsage | None = None
    error: str | None = None


class ChatModel(Protocol):
    def stream(self, messages: list[ChatMessage]) -> AsyncIterator[ChatEvent]: ...


class JsonlConversationStore:
    """小型教学存储；生产环境可用同一接口替换为 PostgreSQL。"""

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self, session_id: str) -> list[ChatMessage]:
        if not self.path.exists():
            return []
        messages: list[ChatMessage] = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            message = ChatMessage.model_validate_json(line)
            if message.session_id == session_id:
                messages.append(message)
        return messages

    def append(self, message: ChatMessage) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(message.model_dump_json() + "\n")


class MockChatModel:
    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[ChatEvent]:
        prompt = messages[-1].content if messages else ""
        answer = f"离线助手已收到：{prompt}"
        for start in range(0, len(answer), 6):
            yield ChatEvent(type="delta", delta=answer[start : start + 6])
        prompt_tokens = max(1, sum(len(message.content) for message in messages) // 2)
        completion_tokens = max(1, len(answer) // 2)
        yield ChatEvent(
            type="usage",
            usage=TokenUsage(
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=prompt_tokens + completion_tokens,
            ),
        )


class OpenAICompatibleChatModel:
    """使用 `/chat/completions` 和 SSE 的兼容适配器。

    该适配器不假定某个供应商的扩展字段，只处理常见 delta 与 usage。
    """

    def __init__(self, config: AssistantConfig, client: httpx.AsyncClient | None = None) -> None:
        self.config = config
        self._client = client

    async def stream(self, messages: list[ChatMessage]) -> AsyncIterator[ChatEvent]:
        headers = {"Authorization": f"Bearer {self.config.api_key}"}
        payload = {
            "model": self.config.model,
            "stream": True,
            "stream_options": {"include_usage": True},
            "messages": [
                {"role": message.role, "content": message.content} for message in messages
            ],
        }
        owns_client = self._client is None
        client = self._client or httpx.AsyncClient(timeout=self.config.timeout_seconds)
        try:
            async with client.stream(
                "POST",
                f"{self.config.base_url.rstrip('/')}/chat/completions",
                headers=headers,
                json=payload,
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line.removeprefix("data:").strip()
                    if not raw or raw == "[DONE]":
                        continue
                    item = json.loads(raw)
                    choices = item.get("choices") or []
                    if choices:
                        delta = choices[0].get("delta", {}).get("content") or ""
                        if delta:
                            yield ChatEvent(type="delta", delta=str(delta))
                    if usage := item.get("usage"):
                        yield ChatEvent(type="usage", usage=TokenUsage.model_validate(usage))
        except (httpx.HTTPError, json.JSONDecodeError) as exc:
            yield ChatEvent(type="error", error=f"model request failed: {type(exc).__name__}")
        finally:
            if owns_client:
                await client.aclose()


class AssistantService:
    def __init__(self, model: ChatModel, store: JsonlConversationStore) -> None:
        self.model = model
        self.store = store

    async def chat(self, prompt: str, *, session_id: str) -> AsyncIterator[ChatEvent]:
        if not prompt.strip():
            raise ValueError("prompt 不能为空")
        user_message = ChatMessage(session_id=session_id, role="user", content=prompt)
        self.store.append(user_message)
        messages = self.store.load(session_id)
        answer_parts: list[str] = []
        failed = False
        async for event in self.model.stream(messages):
            if event.type == "delta":
                answer_parts.append(event.delta)
            elif event.type == "error":
                failed = True
            yield event
        if answer_parts and not failed:
            self.store.append(
                ChatMessage(
                    session_id=session_id,
                    role="assistant",
                    content="".join(answer_parts),
                )
            )
