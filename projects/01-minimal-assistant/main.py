"""项目 1 命令行入口。默认离线运行；配置 APP_MODE=online 可接兼容服务。"""

import asyncio
import json

from ai_agent_book.apps.minimal_assistant import (
    AssistantConfig,
    AssistantService,
    JsonlConversationStore,
    MockChatModel,
    OpenAICompatibleChatModel,
)


async def main() -> None:
    config = AssistantConfig.from_env()
    model = (
        OpenAICompatibleChatModel(config) if config.mode == "online" else MockChatModel()
    )
    service = AssistantService(model, JsonlConversationStore(config.history_path))
    async for event in service.chat("请解释 Agent Runtime", session_id="demo"):
        print(json.dumps(event.model_dump(), ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
