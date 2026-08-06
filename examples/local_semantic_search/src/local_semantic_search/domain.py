"""Versioned, tenant-aware local retrieval and evaluation."""

import math
from dataclasses import dataclass

from local_semantic_search.providers import EmbeddingProvider, lexical_terms


@dataclass(frozen=True)
class Document:
    document_id: str
    version: int
    tenant_id: str
    text: str


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    version: int
    tenant_id: str
    text: str
    embedding_version: str
    vector: tuple[float, ...]


@dataclass(frozen=True)
class SearchHit:
    document_id: str
    version: int
    tenant_id: str
    score: float
    source: str


@dataclass(frozen=True)
class EvaluationReport:
    query_count: int
    recall_at_k: float
    mean_reciprocal_rank: float


class LocalSearchIndex:
    def __init__(self, embedding: EmbeddingProvider) -> None:
        self.embedding = embedding
        self._dimension = embedding.dimension
        self._chunks: dict[tuple[str, str], Chunk] = {}

    def add_documents(self, documents: tuple[Document, ...]) -> None:
        for document in documents:
            key = (document.tenant_id, document.document_id)
            current = self._chunks.get(key)
            if current is not None and document.version <= current.version:
                raise ValueError("文档版本必须严格递增")
            vector = self.embedding.embed(document.text)
            self._validate_dimension(vector)
            self._chunks[key] = Chunk(
                chunk_id=f"{document.document_id}:v{document.version}:0",
                document_id=document.document_id,
                version=document.version,
                tenant_id=document.tenant_id,
                text=document.text,
                embedding_version=self.embedding.version,
                vector=vector,
            )

    def _validate_dimension(self, vector: tuple[float, ...]) -> None:
        if len(vector) != self._dimension:
            raise ValueError(
                f"Embedding 维度不匹配：index={self._dimension}, actual={len(vector)}"
            )

    def _authorized(self, tenant_id: str) -> list[Chunk]:
        return [chunk for chunk in self._chunks.values() if chunk.tenant_id == tenant_id]

    def search_sparse(self, query: str, *, tenant_id: str, limit: int = 5) -> list[SearchHit]:
        query_terms = set(lexical_terms(query))
        scored = []
        for chunk in self._authorized(tenant_id):
            overlap = len(query_terms & set(lexical_terms(chunk.text)))
            if overlap:
                scored.append(self._hit(chunk, float(overlap), "sparse"))
        return sorted(scored, key=lambda hit: (-hit.score, hit.document_id))[:limit]

    def search_dense(self, query: str, *, tenant_id: str, limit: int = 5) -> list[SearchHit]:
        query_vector = self.embedding.embed(query)
        self._validate_dimension(query_vector)
        scored = []
        for chunk in self._authorized(tenant_id):
            self._validate_dimension(chunk.vector)
            score = sum(
                left * right
                for left, right in zip(query_vector, chunk.vector, strict=True)
            )
            if math.isfinite(score):
                scored.append(self._hit(chunk, score, "dense"))
        return sorted(scored, key=lambda hit: (-hit.score, hit.document_id))[:limit]

    def search_hybrid(self, query: str, *, tenant_id: str, limit: int = 5) -> list[SearchHit]:
        lists = (
            self.search_sparse(query, tenant_id=tenant_id, limit=max(limit, 10)),
            self.search_dense(query, tenant_id=tenant_id, limit=max(limit, 10)),
        )
        scores: dict[str, float] = {}
        source: dict[str, SearchHit] = {}
        for hits in lists:
            for rank, hit in enumerate(hits, start=1):
                scores[hit.document_id] = scores.get(hit.document_id, 0.0) + 1.0 / (60 + rank)
                source[hit.document_id] = hit
        ordered = sorted(scores, key=lambda document_id: (-scores[document_id], document_id))
        return [
            SearchHit(
                document_id=document_id,
                version=source[document_id].version,
                tenant_id=source[document_id].tenant_id,
                score=scores[document_id],
                source="rrf",
            )
            for document_id in ordered[:limit]
        ]

    @staticmethod
    def _hit(chunk: Chunk, score: float, source: str) -> SearchHit:
        return SearchHit(chunk.document_id, chunk.version, chunk.tenant_id, score, source)


def evaluate_queries(
    index: LocalSearchIndex, *, tenant_id: str, limit: int
) -> EvaluationReport:
    cases = (
        ("context budget 上下文预算", "context-budget"),
        ("tool timeout 工具超时", "tool-timeout"),
        ("RAG citation 引用", "rag-citation"),
    )
    recalled = 0
    reciprocal_ranks = 0.0
    for query, expected in cases:
        identifiers = [
            hit.document_id for hit in index.search_hybrid(query, tenant_id=tenant_id, limit=limit)
        ]
        if expected in identifiers:
            recalled += 1
            reciprocal_ranks += 1.0 / (identifiers.index(expected) + 1)
    return EvaluationReport(
        query_count=len(cases),
        recall_at_k=recalled / len(cases),
        mean_reciprocal_rank=reciprocal_ranks / len(cases),
    )
