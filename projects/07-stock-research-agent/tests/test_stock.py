from datetime import UTC, datetime

import pytest

from ai_agent_book.apps.stock_research import (
    FixtureDisclosureProvider,
    FixtureMarketProvider,
    FixtureNewsProvider,
    PriceBar,
    StockResearchAgent,
)


@pytest.mark.asyncio
async def test_report_is_not_investment_advice() -> None:
    bars = [
        PriceBar(timestamp=datetime.now(UTC), open=i, high=i + 1, low=i - 1, close=i, volume=1)
        for i in range(2, 7)
    ]
    agent = StockResearchAgent(
        FixtureMarketProvider(bars), FixtureNewsProvider([]), FixtureDisclosureProvider([])
    )
    assert "不构成投资建议" in (await agent.research("DEMO")).disclaimer
