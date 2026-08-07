"""An installed-SDK Model fake that never performs a network request."""

from collections.abc import AsyncIterator

from agents import (
    AgentOutputSchemaBase,
    Handoff,
    Model,
    ModelResponse,
    ModelSettings,
    ModelTracing,
    Tool,
    Usage,
)
from agents.items import TResponseInputItem, TResponseStreamEvent
from openai.types.responses import (
    ResponseFunctionToolCall,
    ResponseOutputItem,
    ResponseOutputMessage,
    ResponseOutputText,
)
from openai.types.responses.response_prompt_param import ResponsePromptParam


def message(text: str, identifier: str = "message_1") -> ResponseOutputMessage:
    return ResponseOutputMessage(
        id=identifier,
        type="message",
        role="assistant",
        status="completed",
        content=[
            ResponseOutputText(
                type="output_text",
                text=text,
                annotations=[],
                logprobs=[],
            )
        ],
    )


def function_call(
    name: str, arguments: str, *, call_id: str = "call_1"
) -> ResponseFunctionToolCall:
    return ResponseFunctionToolCall(
        id=f"item_{call_id}",
        call_id=call_id,
        name=name,
        arguments=arguments,
        type="function_call",
        status="completed",
    )


class ScriptedModel(Model):
    def __init__(self, outputs: tuple[ResponseOutputItem, ...]) -> None:
        self.outputs = outputs
        self.calls = 0

    async def get_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: ResponsePromptParam | None,
    ) -> ModelResponse:
        del (
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id,
            conversation_id,
            prompt,
        )
        output = self.outputs[min(self.calls, len(self.outputs) - 1)]
        self.calls += 1
        return ModelResponse(
            output=[output],
            usage=Usage(requests=1, input_tokens=1, output_tokens=1, total_tokens=2),
            response_id=f"response_{self.calls}",
        )

    def stream_response(
        self,
        system_instructions: str | None,
        input: str | list[TResponseInputItem],
        model_settings: ModelSettings,
        tools: list[Tool],
        output_schema: AgentOutputSchemaBase | None,
        handoffs: list[Handoff],
        tracing: ModelTracing,
        *,
        previous_response_id: str | None,
        conversation_id: str | None,
        prompt: ResponsePromptParam | None,
    ) -> AsyncIterator[TResponseStreamEvent]:
        del (
            system_instructions,
            input,
            model_settings,
            tools,
            output_schema,
            handoffs,
            tracing,
            previous_response_id,
            conversation_id,
            prompt,
        )

        async def empty() -> AsyncIterator[TResponseStreamEvent]:
            if False:
                yield  # pragma: no cover

        return empty()
