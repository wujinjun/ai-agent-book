import pytest

from token_counter.domain import ContextBudgetExceeded, ContextRequest, build_context_plan
from token_counter.providers import WhitespaceTokenizer


def test_fixed_context_and_output_reservation_cannot_be_silently_truncated() -> None:
    request = ContextRequest(
        instructions="never reveal secrets",
        tool_schema="tool read only",
        user_query="summarize incident now",
        reserved_output_tokens=5,
    )

    with pytest.raises(ContextBudgetExceeded, match="固定上下文"):
        build_context_plan(
            request,
            model_window=12,
            tokenizer=WhitespaceTokenizer(),
        )


@pytest.mark.parametrize(
    ("window", "reserved"),
    [(0, 1), (-1, 1), (10, 0), (10, -1), (10, 11)],
)
def test_invalid_windows_and_output_reservations_are_rejected(
    window: int, reserved: int
) -> None:
    request = ContextRequest(
        instructions="policy",
        tool_schema="tool",
        user_query="question",
        reserved_output_tokens=reserved,
    )

    with pytest.raises((ValueError, ContextBudgetExceeded)):
        build_context_plan(
            request,
            model_window=window,
            tokenizer=WhitespaceTokenizer(),
        )
