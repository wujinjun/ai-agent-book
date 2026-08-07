import httpx
import pytest
from pydantic_ai import models
from pydantic_ai.models.test import TestModel

from pydanticai_service.agent import SupportDeps, support_agent
from pydanticai_service.api import create_app
from pydanticai_service.domain import SupportRequest, TicketFacts
from pydanticai_service.providers import InMemoryTicketRepository, build_fixture_model
from pydanticai_service.service import SupportService

models.ALLOW_MODEL_REQUESTS = False


def repository() -> InMemoryTicketRepository:
    return InMemoryTicketRepository(
        records={
            "T-42": TicketFacts(
                ticket_id="T-42",
                tenant_id="acme",
                status="resolved",
                title="Build pipeline recovered",
            )
        }
    )


@pytest.mark.asyncio
async def test_dependency_injection_tool_and_typed_output() -> None:
    repo = repository()
    service = SupportService(repo)
    report = await service.answer(
        SupportRequest(
            tenant_id="acme",
            actor_id="engineer-1",
            ticket_id="T-42",
            question="What is the current status?",
        ),
        model=build_fixture_model(),
    )

    assert report.ticket_id == "T-42"
    assert report.status == "resolved"
    assert repo.calls == [("acme", "engineer-1", "T-42")]


@pytest.mark.asyncio
async def test_official_test_model_and_override_are_available() -> None:
    deps = SupportDeps("acme", "engineer-1", "T-42", repository())
    test_model = TestModel(
        call_tools=[],
        custom_output_args={
            "ticket_id": "T-42",
            "status": "resolved",
            "summary": "Schema generated fixture output.",
            "risk": 0,
        },
    )
    with support_agent.override(model=test_model):
        result = await support_agent.run("Return T-42", deps=deps)
    assert result.output.ticket_id == "T-42"


@pytest.mark.asyncio
async def test_fastapi_endpoint_runs_without_paid_model() -> None:
    app = create_app(SupportService(repository()))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post(
            "/v1/support",
            json={
                "tenant_id": "acme",
                "actor_id": "engineer-1",
                "ticket_id": "T-42",
                "question": "What is the current status?",
            },
        )

    assert response.status_code == 200
    assert response.json()["ticket_id"] == "T-42"
