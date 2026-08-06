from token_counter.domain import ContextRequest, build_context_plan
from token_counter.providers import Utf8ByteTokenizer, WhitespaceTokenizer


def test_utf8_fixture_makes_language_cost_visible() -> None:
    tokenizer = Utf8ByteTokenizer()

    assert tokenizer.count("Agent") == 5
    assert tokenizer.count("智能体") == 9
    assert tokenizer.count("🤖") == 4


def test_budget_report_reserves_output_and_keeps_recent_history() -> None:
    request = ContextRequest(
        instructions="follow policy",
        tool_schema="read tool",
        user_query="answer now",
        history=("old low value message", "recent message"),
        evidence=("best evidence", "secondary evidence"),
        reserved_output_tokens=4,
        max_history_tokens=2,
        max_evidence_tokens=2,
    )

    plan = build_context_plan(
        request,
        model_window=16,
        tokenizer=WhitespaceTokenizer(),
    )

    assert plan.history == ("recent message",)
    assert plan.evidence == ("best evidence",)
    assert plan.partition_tokens == {
        "fixed": 6,
        "history": 2,
        "evidence": 2,
        "output_reserved": 4,
        "unused": 2,
    }
    assert plan.total_committed_tokens <= plan.model_window
