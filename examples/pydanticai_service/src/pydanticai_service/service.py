"""Application service that maps framework failures to stable domain failures."""

import asyncio

from pydantic_ai import UnexpectedModelBehavior, UsageLimitExceeded
from pydantic_ai.models import Model
from pydantic_ai.usage import UsageLimits

from pydanticai_service.agent import SupportDeps, support_agent
from pydanticai_service.domain import InvalidAgentResult, SupportReport, SupportRequest
from pydanticai_service.providers import InMemoryTicketRepository


class SupportService:
    def __init__(
        self,
        repository: InMemoryTicketRepository,
        *,
        timeout_seconds: float = 2.0,
    ) -> None:
        self.repository = repository
        self.timeout_seconds = timeout_seconds

    async def answer(self, request: SupportRequest, *, model: Model) -> SupportReport:
        deps = SupportDeps(
            tenant_id=request.tenant_id,
            actor_id=request.actor_id,
            expected_ticket_id=request.ticket_id,
            repository=self.repository,
        )
        try:
            async with asyncio.timeout(self.timeout_seconds):
                with support_agent.override(model=model):
                    result = await support_agent.run(
                        f"Ticket {request.ticket_id}: {request.question}",
                        deps=deps,
                        usage_limits=UsageLimits(request_limit=4, tool_calls_limit=2),
                    )
        except (UnexpectedModelBehavior, UsageLimitExceeded) as exc:
            raise InvalidAgentResult("agent could not satisfy the bounded contract") from exc
        return result.output
