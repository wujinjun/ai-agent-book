"""Deterministic fixture embedding and bilingual source data."""

import hashlib
import math
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from local_semantic_search.domain import Document


class EmbeddingProvider(Protocol):
    @property
    def dimension(self) -> int: ...

    @property
    def version(self) -> str: ...

    def embed(self, text: str) -> tuple[float, ...]: ...


def lexical_terms(text: str) -> tuple[str, ...]:
    lowered = text.lower()
    words = re.findall(r"[a-z0-9_]+", lowered)
    chinese_runs = re.findall(r"[\u4e00-\u9fff]+", lowered)
    chinese = [character for run in chinese_runs for character in run]
    bigrams = [run[index : index + 2] for run in chinese_runs for index in range(len(run) - 1)]
    return tuple(words + chinese + bigrams)


@dataclass(frozen=True)
class HashedEmbedding:
    """Signed feature hashing for repeatable retrieval tests, not semantic truth."""

    dimension: int = 64
    version: str = "fixture-hash-v1"

    def embed(self, text: str) -> tuple[float, ...]:
        if self.dimension <= 0:
            raise ValueError("dimension 必须为正数")
        values = [0.0] * self.dimension
        for term in lexical_terms(text):
            digest = hashlib.sha256(term.encode("utf-8")).digest()
            index = int.from_bytes(digest[:4], "big") % self.dimension
            sign = 1.0 if digest[4] % 2 == 0 else -1.0
            values[index] += sign
        norm = math.sqrt(sum(value * value for value in values))
        return tuple(value / norm for value in values) if norm else tuple(values)


@dataclass(frozen=True)
class WrongDimensionEmbedding:
    dimension: int
    version: str = "fixture-wrong-dimension"

    def embed(self, text: str) -> tuple[float, ...]:
        del text
        return (1.0,) * (self.dimension + 1)


def bilingual_fixture() -> tuple["Document", ...]:
    from local_semantic_search.domain import Document

    return (
        Document(
            "context-budget",
            2,
            "acme",
            "Context budget 上下文预算必须预留 output tokens，并保护系统规则。",
        ),
        Document(
            "tool-timeout",
            1,
            "acme",
            "Tool timeout 工具超时需要有限重试、幂等键和状态核实。",
        ),
        Document(
            "rag-citation",
            3,
            "acme",
            "RAG citation 引用必须保留文档版本与证据片段。",
        ),
        Document(
            "other-secret",
            1,
            "other",
            "Context budget confidential tenant document.",
        ),
    )
