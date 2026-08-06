"""Validation, bounded repair and stable public errors."""

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from structured_extractor.providers import ExtractionProvider


class Incident(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    title: str = Field(min_length=1, max_length=120)
    severity: Literal["low", "medium", "high"]
    affected_service: str = Field(min_length=1, max_length=80)


class SensitiveInputRejected(ValueError):
    pass


class ExtractionFailed(ValueError):
    def __init__(self, *, attempts: int) -> None:
        super().__init__("结构化抽取失败；请检查输入或稍后重试")
        self.attempts = attempts


SENSITIVE_PATTERNS = (
    re.compile(r"(?i)password\s*[:=]\s*\S+"),
    re.compile(r"(?i)(?:api[_-]?key|secret)\s*[:=]\s*\S+"),
    re.compile(r"\b\d{16}\b"),
)


class Extractor:
    def __init__(self, provider: ExtractionProvider, *, max_repairs: int = 1) -> None:
        if max_repairs < 0 or max_repairs > 3:
            raise ValueError("max_repairs 必须位于 0..3")
        self.provider = provider
        self.max_repairs = max_repairs

    def extract(self, text: str) -> Incident:
        if any(pattern.search(text) for pattern in SENSITIVE_PATTERNS):
            raise SensitiveInputRejected("输入包含禁止处理的敏感数据")
        repair_hints: tuple[str, ...] = ()
        for attempt in range(self.max_repairs + 1):
            proposal = self.provider.propose(
                text, attempt=attempt, repair_hints=repair_hints
            )
            try:
                return Incident.model_validate(proposal)
            except ValidationError as error:
                repair_hints = tuple(
                    sorted({str(item["type"]) for item in error.errors(include_input=False)})
                )
        raise ExtractionFailed(attempts=self.max_repairs + 1)
