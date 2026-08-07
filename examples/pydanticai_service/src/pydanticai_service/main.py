"""Run the PydanticAI + FastAPI vertical slice without network access."""

import argparse
import asyncio

from pydantic_ai import models

from pydanticai_service.domain import SupportRequest, TicketFacts
from pydanticai_service.providers import InMemoryTicketRepository, build_fixture_model
from pydanticai_service.service import SupportService


async def run_offline() -> None:
    models.ALLOW_MODEL_REQUESTS = False
    repository = InMemoryTicketRepository(
        records={
            "T-42": TicketFacts(
                ticket_id="T-42",
                tenant_id="acme",
                status="resolved",
                title="Build pipeline recovered",
            )
        }
    )
    service = SupportService(repository)
    report = await service.answer(
        SupportRequest(
            tenant_id="acme",
            actor_id="engineer-1",
            ticket_id="T-42",
            question="What is the current status?",
        ),
        model=build_fixture_model(),
    )
    print(report.model_dump_json(indent=2))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", default=True)
    parser.parse_args()
    asyncio.run(run_offline())


if __name__ == "__main__":
    main()
