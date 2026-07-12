"""项目 2 命令行入口：离线演示多工具并行与校验。"""

import asyncio
import json

from ai_agent_book.apps.weather_agent import (
    DeterministicPlanner,
    ToolAgent,
    ToolCall,
    ToolRegistry,
)


async def main() -> None:
    planner = DeterministicPlanner(
        [
            ToolCall(call_id="weather-1", name="get_weather", arguments={"city": "上海"}),
            ToolCall(
                call_id="convert-1",
                name="calculate",
                arguments={"expression": "26 * 9 / 5 + 32"},
            ),
        ]
    )
    result = await ToolAgent(planner, ToolRegistry.default()).run("查询上海天气并换算温度")
    print(json.dumps(result.model_dump(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
