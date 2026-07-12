"""项目 7：多来源、带时间与引用、事实/推断分离的股票研究 Agent。

本模块只生成教学研究报告，不提供确定性买卖建议。
"""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import UTC, datetime
from typing import Protocol

import httpx
from pydantic import BaseModel, Field, model_validator


class PriceBar(BaseModel):
    timestamp: datetime
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)

    @model_validator(mode="after")
    def validate_range(self) -> PriceBar:
        if self.high < max(self.open, self.close, self.low) or self.low > min(
            self.open, self.close, self.high
        ):
            raise ValueError("invalid OHLC range")
        return self


class SourceItem(BaseModel):
    title: str
    url: str
    published_at: datetime
    summary: str


class IndicatorSet(BaseModel):
    sma_5: float
    return_5d_percent: float
    rsi_14: float | None


class Fact(BaseModel):
    category: str
    statement: str
    source_url: str
    observed_at: datetime


class ResearchReport(BaseModel):
    symbol: str
    as_of: datetime
    indicators: IndicatorSet
    facts: list[Fact]
    inferences: list[str]
    sources: list[SourceItem]
    disclaimer: str = "本报告仅用于技术教学，不构成投资建议。"


class MarketProvider(Protocol):
    async def get_bars(self, symbol: str) -> Sequence[PriceBar]: ...


class NewsProvider(Protocol):
    async def get_news(self, symbol: str) -> Sequence[SourceItem]: ...


class DisclosureProvider(Protocol):
    async def get_disclosures(self, symbol: str) -> Sequence[SourceItem]: ...


class FixtureMarketProvider:
    def __init__(self, bars: Sequence[PriceBar]) -> None:
        self.bars = bars

    async def get_bars(self, symbol: str) -> Sequence[PriceBar]:
        return self.bars


class FixtureNewsProvider:
    def __init__(self, items: Sequence[SourceItem]) -> None:
        self.items = items

    async def get_news(self, symbol: str) -> Sequence[SourceItem]:
        return self.items


class FixtureDisclosureProvider:
    def __init__(self, items: Sequence[SourceItem]) -> None:
        self.items = items

    async def get_disclosures(self, symbol: str) -> Sequence[SourceItem]:
        return self.items


class HttpMarketProvider:
    """解析统一 `{bars: [...]}` 契约的可配置行情 HTTP 适配器。"""

    def __init__(self, url: str, *, client: httpx.AsyncClient | None = None) -> None:
        self.url = url
        self.client = client

    async def get_bars(self, symbol: str) -> Sequence[PriceBar]:
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=10)
        try:
            response = await client.get(self.url, params={"symbol": symbol})
            response.raise_for_status()
            return [PriceBar.model_validate(item) for item in response.json()["bars"]]
        finally:
            if owns_client:
                await client.aclose()


def _rsi(closes: list[float], period: int = 14) -> float | None:
    if len(closes) <= period:
        return None
    changes = [
        current - previous for previous, current in zip(closes, closes[1:], strict=False)
    ]
    window = changes[-period:]
    average_gain = sum(max(change, 0) for change in window) / period
    average_loss = sum(max(-change, 0) for change in window) / period
    if average_loss == 0:
        return 100.0
    relative_strength = average_gain / average_loss
    return round(100 - 100 / (1 + relative_strength), 2)


class StockResearchAgent:
    def __init__(
        self,
        market: MarketProvider,
        news: NewsProvider,
        disclosures: DisclosureProvider,
    ) -> None:
        self.market = market
        self.news = news
        self.disclosures = disclosures

    async def research(self, symbol: str) -> ResearchReport:
        bars_result, news_result, disclosures_result = await asyncio.gather(
            self.market.get_bars(symbol),
            self.news.get_news(symbol),
            self.disclosures.get_disclosures(symbol),
        )
        bars = sorted(bars_result, key=lambda bar: bar.timestamp)
        if len(bars) < 5:
            raise ValueError("at least five price bars are required")
        news = list(news_result)
        disclosures = list(disclosures_result)
        closes = [bar.close for bar in bars]
        latest = bars[-1]
        sma_5 = sum(closes[-5:]) / 5
        indicators = IndicatorSet(
            sma_5=round(sma_5, 4),
            return_5d_percent=round((closes[-1] / closes[-5] - 1) * 100, 2),
            rsi_14=_rsi(closes),
        )
        market_source = SourceItem(
            title=f"{symbol} 行情时间序列",
            url=f"fixture://market/{symbol}",
            published_at=latest.timestamp,
            summary=f"最新收盘价 {latest.close:.2f}",
        )
        sources = [market_source, *news, *disclosures]
        facts = [
            Fact(
                category="market",
                statement=f"最新收盘价为 {latest.close:.2f}，5 日均值为 {sma_5:.2f}。",
                source_url=market_source.url,
                observed_at=latest.timestamp,
            )
        ]
        facts.extend(
            Fact(
                category="news" if item in news else "disclosure",
                statement=item.summary,
                source_url=item.url,
                observed_at=item.published_at,
            )
            for item in [*news, *disclosures]
        )
        inferences = [
            "价格指标只描述所给历史窗口，不能单独推出未来价格方向。",
            "行业与公司信息需要结合来源时效、口径和后续公告交叉验证。",
        ]
        return ResearchReport(
            symbol=symbol,
            as_of=latest.timestamp.astimezone(UTC),
            indicators=indicators,
            facts=facts,
            inferences=inferences,
            sources=sources,
        )
