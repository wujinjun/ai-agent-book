"""Provider-neutral context budgeting domain."""

from dataclasses import dataclass

from token_counter.providers import Tokenizer


class ContextBudgetExceeded(ValueError):
    """The non-negotiable context cannot fit in the selected model window."""


@dataclass(frozen=True)
class ContextRequest:
    instructions: str
    tool_schema: str
    user_query: str
    reserved_output_tokens: int
    history: tuple[str, ...] = ()
    evidence: tuple[str, ...] = ()
    max_history_tokens: int | None = None
    max_evidence_tokens: int | None = None


@dataclass(frozen=True)
class ContextPlan:
    tokenizer: str
    model_window: int
    history: tuple[str, ...]
    evidence: tuple[str, ...]
    partition_tokens: dict[str, int]

    @property
    def total_committed_tokens(self) -> int:
        return self.model_window - self.partition_tokens["unused"]


def build_context_plan(
    request: ContextRequest,
    *,
    model_window: int,
    tokenizer: Tokenizer,
) -> ContextPlan:
    """Keep hard context, then recent history and ranked evidence.

    History is considered from newest to oldest but returned in chronological
    order. Evidence is expected to be ordered best-first by the retriever.
    Whole items are selected; this example never cuts text mid-unit.
    """
    if model_window <= 0:
        raise ValueError("model_window 必须为正数")
    if request.reserved_output_tokens <= 0:
        raise ValueError("reserved_output_tokens 必须为正数")
    for label, limit in (
        ("max_history_tokens", request.max_history_tokens),
        ("max_evidence_tokens", request.max_evidence_tokens),
    ):
        if limit is not None and limit < 0:
            raise ValueError(f"{label} 不能为负数")

    fixed_tokens = sum(
        tokenizer.count(part)
        for part in (request.instructions, request.tool_schema, request.user_query)
    )
    input_limit = model_window - request.reserved_output_tokens
    if input_limit < 0 or fixed_tokens > input_limit:
        raise ContextBudgetExceeded("固定上下文与输出保留量超过模型窗口")

    remaining = input_limit - fixed_tokens
    history_tokens = 0
    selected_history: list[str] = []
    history_limit = min(
        remaining,
        remaining if request.max_history_tokens is None else request.max_history_tokens,
    )
    for message in reversed(request.history):
        cost = tokenizer.count(message)
        if cost <= remaining and history_tokens + cost <= history_limit:
            selected_history.append(message)
            history_tokens += cost
            remaining -= cost
    selected_history.reverse()

    evidence_tokens = 0
    selected_evidence: list[str] = []
    evidence_limit = min(
        remaining,
        remaining if request.max_evidence_tokens is None else request.max_evidence_tokens,
    )
    for chunk in request.evidence:
        cost = tokenizer.count(chunk)
        if cost <= remaining and evidence_tokens + cost <= evidence_limit:
            selected_evidence.append(chunk)
            evidence_tokens += cost
            remaining -= cost

    return ContextPlan(
        tokenizer=tokenizer.name,
        model_window=model_window,
        history=tuple(selected_history),
        evidence=tuple(selected_evidence),
        partition_tokens={
            "fixed": fixed_tokens,
            "history": history_tokens,
            "evidence": evidence_tokens,
            "output_reserved": request.reserved_output_tokens,
            "unused": remaining,
        },
    )
