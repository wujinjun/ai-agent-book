import pytest
from agents import (
    Agent,
    GuardrailFunctionOutput,
    InputGuardrailTripwireTriggered,
    RunConfig,
    RunContextWrapper,
    Runner,
    input_guardrail,
    set_tracing_disabled,
)
from agents.items import TResponseInputItem

from openai_agents_sdk_example.providers import ScriptedModel, message

set_tracing_disabled(True)


@input_guardrail(name="deny-delete", run_in_parallel=False)
async def deny_delete(
    context: RunContextWrapper[None],
    agent: Agent[None],
    input_value: str | list[TResponseInputItem],
) -> GuardrailFunctionOutput:
    del context, agent
    blocked = "delete" in str(input_value).lower()
    return GuardrailFunctionOutput(output_info={"blocked": blocked}, tripwire_triggered=blocked)


@pytest.mark.asyncio
async def test_blocking_guardrail_prevents_model_execution() -> None:
    model = ScriptedModel((message("must not run"),))
    agent = Agent(name="guarded", model=model, input_guardrails=[deny_delete])

    with pytest.raises(InputGuardrailTripwireTriggered):
        await Runner.run(
            agent,
            "delete all records",
            run_config=RunConfig(tracing_disabled=True, trace_include_sensitive_data=False),
        )

    assert model.calls == 0


def test_trace_configuration_excludes_sensitive_data() -> None:
    config = RunConfig(
        tracing_disabled=True,
        trace_include_sensitive_data=False,
        workflow_name="offline-test",
    )
    assert config.tracing_disabled is True
    assert config.trace_include_sensitive_data is False
