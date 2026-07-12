from datetime import UTC, datetime, timedelta

import httpx
import pytest

from ai_agent_book.apps.stock_research import (
    FixtureDisclosureProvider,
    FixtureMarketProvider,
    FixtureNewsProvider,
    HttpMarketProvider,
    PriceBar,
    SourceItem,
    StockResearchAgent,
)


def _bars() -> list[PriceBar]:
    now = datetime.now(UTC)
    return [
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


@pytest.mark.asyncio
async def test_stock_report_has_timed_facts_sources_indicators_and_inferences() -> None:
    news = SourceItem(
        title="行业需求更新",
        url="https://example.test/news/1",
        published_at=datetime.now(UTC),
        summary="行业需求同比增长。",
    )
    filing = SourceItem(
        title="季度公告",
        url="https://example.test/filing/1",
        published_at=datetime.now(UTC),
        summary="公司披露季度收入。",
    )
    agent = StockResearchAgent(
        FixtureMarketProvider(_bars()),
        FixtureNewsProvider([news]),
        FixtureDisclosureProvider([filing]),
    )
    report = await agent.research("DEMO")

    assert report.indicators.sma_5 == pytest.approx(118.0)
    assert report.indicators.rsi_14 is not None
    assert len(report.sources) == 3
    assert report.facts and report.inferences
    assert "不构成投资建议" in report.disclaimer
    assert "买入" not in "".join(report.inferences)


@pytest.mark.asyncio
async def test_http_market_provider_parses_timed_bars() -> None:
    payload = {
        "bars": [
            {
                "timestamp": "2026-07-10T00:00:00Z",
                "open": 10,
                "high": 12,
                "low": 9,
                "close": 11,
                "volume": 100,
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["symbol"] == "DEMO"
        return httpx.Response(200, json=payload)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        bars = await HttpMarketProvider("https://market.test/bars", client=client).get_bars("DEMO")
    assert bars[0].close == 11
    assert bars[0].timestamp.tzinfo is not None
