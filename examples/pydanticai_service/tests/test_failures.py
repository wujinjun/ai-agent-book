import httpx
import pytest
from pydantic_ai import models
from pydantic_ai.messages import RetryPromptPart

from pydanticai_service.api import create_app
from pydanticai_service.domain import (
    InvalidAgentResult,
    SupportRequest,
    TicketFacts,
)
from pydanticai_service.providers import InMemoryTicketRepository, Scenario, build_fixture_model
from pydanticai_service.service import SupportService

models.ALLOW_MODEL_REQUESTS = False


def request(actor_id: str = "engineer-1") -> SupportRequest:
    return SupportRequest(
        tenant_id="acme",
        actor_id=actor_id,
        ticket_id="T-42",
        question="What is the current status?",
    )


def repository(*, unavailable: bool = False) -> InMemoryTicketRepository:
    return InMemoryTicketRepository(
        records={
            "T-42": TicketFacts(
                ticket_id="T-42",
                tenant_id="acme",
                status="resolved",
                title="Build pipeline recovered",
            )
        },
        unavailable=unavailable,
    )


@pytest.mark.asyncio
async def test_tool_schema_error_is_retried_once_then_succeeds() -> None:
    result = await SupportService(repository()).answer(
        request(), model=build_fixture_model("invalid_tool_once")
    )
    assert result.ticket_id == "T-42"


@pytest.mark.asyncio
async def test_output_business_validation_is_retried_once_then_succeeds() -> None:
    result = await SupportService(repository()).answer(
        request(), model=build_fixture_model("invalid_output_once")
    )
    assert result.ticket_id == "T-42"


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["invalid_tool_forever", "invalid_output_forever"])
async def test_retry_budget_exhaustion_maps_to_stable_error(scenario: Scenario) -> None:
    with pytest.raises(InvalidAgentResult, match="bounded contract"):
        await SupportService(repository()).answer(request(), model=build_fixture_model(scenario))


@pytest.mark.asyncio
async def test_fastapi_maps_policy_and_dependency_errors() -> None:
    cases = [
        (SupportService(repository()), "blocked-user", 403, "policy_denied"),
        (SupportService(repository(unavailable=True)), "engineer-1", 503, "dependency_unavailable"),
    ]
    for service, actor_id, status, code in cases:
        transport = httpx.ASGITransport(app=create_app(service))
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.post(
                "/v1/support",
                json=request(actor_id).model_dump(),
            )
        assert response.status_code == status
        assert response.json()["detail"]["code"] == code


@pytest.mark.asyncio
async def test_fastapi_maps_service_timeout_without_leaking_exception() -> None:
    slow_repository = repository()
    slow_repository.delay_seconds = 0.05
    app = create_app(SupportService(slow_repository, timeout_seconds=0.001))
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        response = await client.post("/v1/support", json=request().model_dump())

    assert response.status_code == 504
    assert response.json()["detail"] == {"code": "timeout", "message": "request timed out"}


def test_retry_prompt_type_is_from_installed_framework() -> None:
    assert RetryPromptPart.__module__.startswith("pydantic_ai")
