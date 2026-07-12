import httpx
import pytest

from ai_agent_book.project_api import app


@pytest.mark.asyncio
async def test_health_and_project_execution_api() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        health = await client.get("/health")
        result = await client.post("/projects/7/run", json={"prompt": "研究 DEMO"})

    assert health.json() == {"status": "ok"}
    assert result.status_code == 200
    assert result.json()["project_id"] == 7
    assert "不构成投资建议" in result.json()["output"]


@pytest.mark.asyncio
async def test_api_rejects_unknown_project() -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/projects/99/run", json={"prompt": "test"})
    assert response.status_code == 404
