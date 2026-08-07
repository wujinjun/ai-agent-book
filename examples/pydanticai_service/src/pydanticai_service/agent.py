"""Typed PydanticAI agent definition and its deterministic business boundaries."""

from dataclasses import dataclass
from typing import Annotated

from pydantic import Field
from pydantic_ai import Agent, ModelRetry, RunContext

from pydanticai_service.domain import SupportReport, TicketFacts
from pydanticai_service.providers import InMemoryTicketRepository


@dataclass(frozen=True)
class SupportDeps:
    tenant_id: str
    actor_id: str
    expected_ticket_id: str
    repository: InMemoryTicketRepository


support_agent = Agent(
    deps_type=SupportDeps,
    output_type=SupportReport,
    instructions="Use lookup_ticket for facts. Return only a typed support report.",
    retries=1,
    tool_timeout=0.5,
)


@support_agent.tool(retries=1)
async def lookup_ticket(
    ctx: RunContext[SupportDeps],
    ticket_id: Annotated[str, Field(pattern=r"^T-[0-9]+$")],
) -> TicketFacts:
    """Read one ticket through the current tenant and actor boundary."""
    return await ctx.deps.repository.get(
        tenant_id=ctx.deps.tenant_id,
        actor_id=ctx.deps.actor_id,
        ticket_id=ticket_id,
    )


@support_agent.output_validator
def validate_ticket_identity(ctx: RunContext[SupportDeps], output: SupportReport) -> SupportReport:
    if output.ticket_id != ctx.deps.expected_ticket_id:
        raise ModelRetry("ticket_id must match the requested ticket")
    return output
