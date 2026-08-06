"""A scripted logit provider; it is intentionally not an LLM."""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Protocol


class LogitProvider(Protocol):
    @property
    def vocabulary(self) -> tuple[str, ...]:
        """Return the immutable token vocabulary."""

    def next_logits(self, generated: Sequence[str]) -> tuple[float, ...]:
        """Return one logit per vocabulary item."""


@dataclass(frozen=True)
class FixedLogitModel:
    """Repeat fixed or scripted logits for offline control-flow tests."""

    vocabulary: tuple[str, ...] = ("A", "B", "<STOP>", "?")
    scripted_logits: tuple[tuple[float, ...], ...] = ((3.0, 2.0, 0.5, -1.0),)

    def next_logits(self, generated: Sequence[str]) -> tuple[float, ...]:
        index = min(len(generated), len(self.scripted_logits) - 1)
        return self.scripted_logits[index]
