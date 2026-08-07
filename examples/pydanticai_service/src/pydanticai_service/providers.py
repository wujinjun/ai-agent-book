"""Deterministic repository and model adapters used by the offline example."""

import asyncio
import re
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Literal

from pydantic_ai import ModelMessage, ModelResponse, TextPart, ToolCallPart
from pydantic_ai.models.function import AgentInfo, FunctionModel

from pydanticai_service.domain import DependencyUnavailable, PolicyDenied, TicketFacts


@dataclass
class InMemoryTicketRepository:
    records: dict[str, TicketFacts]
    unavailable: bool = False
    delay_seconds: float = 0.0
    calls: list[tuple[str, str, str]] = field(default_factory=list)

    async def get(self, *, tenant_id: str, actor_id: str, ticket_id: str) -> TicketFacts:
        self.calls.append((tenant_id, actor_id, ticket_id))
        if self.delay_seconds:
            await asyncio.sleep(self.delay_seconds)
        if actor_id == "blocked-user":
            raise PolicyDenied("actor is not allowed to read tickets")
        if self.unavailable:
            raise DependencyUnavailable("ticket repository is unavailable")
        ticket = self.records.get(ticket_id)
        if ticket is None or ticket.tenant_id != tenant_id:
            raise PolicyDenied("ticket is outside the tenant boundary")
        return ticket


Scenario = Literal[
    "happy",
    "invalid_tool_once",
    "invalid_tool_forever",
    "invalid_output_once",
    "invalid_output_forever",
]


def _part_kind(message: ModelMessage) -> str:
    parts = getattr(message, "parts", ())
    if not parts:
        return ""
    return str(getattr(parts[-1], "part_kind", ""))


def _retry_tool_name(message: ModelMessage) -> str | None:
    parts = getattr(message, "parts", ())
    if not parts:
        return None
    return getattr(parts[-1], "tool_name", None)


def _ticket_from_messages(messages: list[ModelMessage]) -> str:
    text = " ".join(str(getattr(part, "content", "")) for m in messages for part in m.parts)
    match = re.search(r"T-[0-9]+", text)
    return match.group(0) if match else "T-42"


def build_fixture_model(scenario: Scenario = "happy") -> FunctionModel:
    """Build an official FunctionModel that drives an exact deterministic dialogue."""

    output_attempts = 0

    def respond(messages: list[ModelMessage], info: AgentInfo) -> ModelResponse:
        nonlocal output_attempts
        last_kind = _part_kind(messages[-1])
        retry_tool = _retry_tool_name(messages[-1])

        if len(messages) == 1:
            ticket_id = (
                "invalid"
                if scenario.startswith("invalid_tool")
                else _ticket_from_messages(messages)
            )
            return ModelResponse(parts=[ToolCallPart("lookup_ticket", {"ticket_id": ticket_id})])

        if last_kind == "retry-prompt" and retry_tool == "lookup_ticket":
            ticket_id = (
                "invalid"
                if scenario == "invalid_tool_forever"
                else _ticket_from_messages(messages)
            )
            return ModelResponse(parts=[ToolCallPart("lookup_ticket", {"ticket_id": ticket_id})])

        if not info.output_tools:
            return ModelResponse(parts=[TextPart("fixture requires a structured output tool")])

        output_attempts += 1
        invalid_output = scenario == "invalid_output_forever" or (
            scenario == "invalid_output_once" and output_attempts == 1
        )
        ticket_id = "T-999" if invalid_output else _ticket_from_messages(messages)
        return ModelResponse(
            parts=[
                ToolCallPart(
                    info.output_tools[0].name,
                    {
                        "ticket_id": ticket_id,
                        "status": "resolved",
                        "summary": "Fixture confirms the ticket is resolved.",
                        "risk": 1,
                    },
                )
            ]
        )

    callback: Callable[[list[ModelMessage], AgentInfo], ModelResponse] = respond
    return FunctionModel(callback, model_name=f"fixture-{scenario}")
