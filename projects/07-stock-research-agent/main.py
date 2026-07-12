"""项目 7 入口：使用带时间的 Fixture 数据生成结构化研究报告。"""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from ai_agent_book.apps.stock_research import (
    FixtureDisclosureProvider,
    FixtureMarketProvider,
    FixtureNewsProvider,
    PriceBar,
    SourceItem,
    StockResearchAgent,
)


async def main() -> None:
    now = datetime.now(UTC)
    bars = [
        PriceBar(
            timestamp=now - timedelta(days=19 - index),
            open=100 + index,
            high=102 + index,
            low=99 + index,
            close=101 + index,
            volume=1_000 + index,
        )
        for index in range(20)
    ]
    news = SourceItem(
        title="行业教学新闻",
        url="https://example.test/news",
        published_at=now,
        summary="行业信息仅为教学 Fixture。",
    )
    agent = StockResearchAgent(
        FixtureMarketProvider(bars),
        FixtureNewsProvider([news]),
        FixtureDisclosureProvider([]),
    )
    report = await agent.research("DEMO")
    print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
