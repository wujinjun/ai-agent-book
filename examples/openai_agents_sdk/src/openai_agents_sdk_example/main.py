"""Run tools and structured output with OpenAI Agents SDK, fully offline."""

import argparse
import asyncio
import json

from agents import Agent, RunConfig, Runner, function_tool, set_tracing_disabled

from openai_agents_sdk_example.domain import SupportReport
from openai_agents_sdk_example.providers import ScriptedModel, function_call, message


@function_tool
def lookup_ticket(ticket_id: str) -> str:
    """Return deterministic fixture data for one ticket."""
    return json.dumps({"ticket_id": ticket_id, "status": "resolved"})


async def run_offline() -> SupportReport:
    set_tracing_disabled(True)
    model = ScriptedModel(
        (
            function_call("lookup_ticket", '{"ticket_id":"T-42"}'),
            message('{"summary":"ticket resolved","risk":"low"}', "message_2"),
        )
    )
    agent = Agent(
        name="Support agent",
        instructions="Use the tool, then return a typed report.",
        model=model,
        tools=[lookup_ticket],
        output_type=SupportReport,
    )
    result = await Runner.run(
        agent,
        "Inspect T-42",
        max_turns=3,
        run_config=RunConfig(
            tracing_disabled=True,
            trace_include_sensitive_data=False,
            workflow_name="offline-sdk-example",
        ),
    )
    return result.final_output_as(SupportReport)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", default=True)
    args = parser.parse_args()
    del args
    print(asyncio.run(run_offline()).model_dump_json(indent=2))


if __name__ == "__main__":
    main()
