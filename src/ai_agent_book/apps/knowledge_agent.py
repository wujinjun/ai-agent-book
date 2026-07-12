"""项目 4：本地可运行的多格式摄取、检索、重排、引用与评估。"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from hashlib import sha256
from pathlib import Path
from zipfile import BadZipFile, ZipFile

import psycopg
from pydantic import BaseModel, Field


class ParsedPage(BaseModel):
    source: str
    page: int = Field(ge=1)
    text: str


class Chunk(BaseModel):
    chunk_id: str
    tenant_id: str
    source: str
    page: int
    text: str
    vector: list[float]


class Citation(BaseModel):
    chunk_id: str
    source: str
    page: int
    score: float


class KnowledgeAnswer(BaseModel):
    text: str
    citations: list[Citation]


class RetrievalMetrics(BaseModel):
    recall_at_k: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)


class PgVectorHit(BaseModel):
    chunk_id: str
    source: str
    page: int
    text: str
    score: float


class DocumentParser:
    """不依赖 Office 应用的安全子集解析器。"""

    max_archive_uncompressed = 50 * 1024 * 1024

    def parse(self, path: Path) -> list[ParsedPage]:
        path = path.resolve()
        suffix = path.suffix.lower()
        if suffix in {".md", ".txt"}:
            return [ParsedPage(source=str(path), page=1, text=path.read_text(encoding="utf-8"))]
        if suffix == ".pdf":
            return self._parse_pdf(path)
        if suffix == ".docx":
            return self._parse_office(path, "word/document.xml")
        if suffix == ".pptx":
            return self._parse_powerpoint(path)
        raise ValueError(f"unsupported document type: {suffix}")

    @staticmethod
    def _parse_pdf(path: Path) -> list[ParsedPage]:
        from pypdf import PdfReader

        reader = PdfReader(path)
        return [
            ParsedPage(source=str(path), page=index, text=page.extract_text() or "")
            for index, page in enumerate(reader.pages, start=1)
        ]

    def _validate_archive(self, archive: ZipFile) -> None:
        total = sum(info.file_size for info in archive.infolist())
        if total > self.max_archive_uncompressed:
            raise ValueError("Office archive exceeds uncompressed size limit")

    def _parse_office(self, path: Path, member: str) -> list[ParsedPage]:
        try:
            with ZipFile(path) as archive:
                self._validate_archive(archive)
                xml = archive.read(member)
        except (BadZipFile, KeyError) as exc:
            raise ValueError("invalid Office document") from exc
        text = " ".join(node.text or "" for node in ET.fromstring(xml).iter() if node.text)
        return [ParsedPage(source=str(path), page=1, text=text)]

    def _parse_powerpoint(self, path: Path) -> list[ParsedPage]:
        try:
            with ZipFile(path) as archive:
                self._validate_archive(archive)
                names = sorted(
                    name
                    for name in archive.namelist()
                    if re.fullmatch(r"ppt/slides/slide\d+\.xml", name)
                )
                pages = []
                for page, name in enumerate(names, start=1):
                    root = ET.fromstring(archive.read(name))
                    text = " ".join(node.text or "" for node in root.iter() if node.text)
                    pages.append(ParsedPage(source=str(path), page=page, text=text))
                return pages
        except BadZipFile as exc:
            raise ValueError("invalid PowerPoint document") from exc


def _terms(text: str) -> list[str]:
    latin = re.findall(r"[a-zA-Z][a-zA-Z0-9_-]*", text.lower())
    han = [character for character in text if "\u4e00" <= character <= "\u9fff"]
    return latin + han


def _embed(text: str, dimensions: int = 128) -> list[float]:
    vector = [0.0] * dimensions
    for term in _terms(text):
        digest = sha256(term.encode()).digest()
        index = int.from_bytes(digest[:4], "big") % dimensions
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(value * value for value in vector)) or 1.0
    return [value / norm for value in vector]


def _cosine(left: list[float], right: list[float]) -> float:
    return sum(a * b for a, b in zip(left, right, strict=True))


class KnowledgeBase:
    def __init__(self, *, chunk_size: int = 400, overlap: int = 60) -> None:
        if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
            raise ValueError("invalid chunk configuration")
        self.chunk_size = chunk_size
        self.overlap = overlap
        self.parser = DocumentParser()
        self.chunks: list[Chunk] = []

    def ingest(self, path: Path, *, tenant_id: str) -> list[str]:
        ids: list[str] = []
        for page in self.parser.parse(path):
            text = re.sub(r"\s+", " ", page.text).strip()
            step = self.chunk_size - self.overlap
            for start in range(0, len(text), step):
                content = text[start : start + self.chunk_size].strip()
                if not content:
                    continue
                chunk_id = sha256(
                    f"{tenant_id}:{page.source}:{page.page}:{start}:{content}".encode()
                ).hexdigest()[:20]
                self.chunks.append(
                    Chunk(
                        chunk_id=chunk_id,
                        tenant_id=tenant_id,
                        source=page.source,
                        page=page.page,
                        text=content,
                        vector=_embed(content),
                    )
                )
                ids.append(chunk_id)
        return ids

    def retrieve(self, query: str, *, tenant_id: str, top_k: int = 5) -> list[tuple[Chunk, float]]:
        query_vector = _embed(query)
        query_terms = set(_terms(query))
        candidates: list[tuple[Chunk, float]] = []
        for chunk in self.chunks:
            if chunk.tenant_id != tenant_id:
                continue
            dense = _cosine(query_vector, chunk.vector)
            lexical = len(query_terms & set(_terms(chunk.text))) / max(1, len(query_terms))
            score = dense * 0.65 + lexical * 0.35
            candidates.append((chunk, score))
        return sorted(candidates, key=lambda item: item[1], reverse=True)[:top_k]

    def answer(self, query: str, *, tenant_id: str, top_k: int = 3) -> KnowledgeAnswer:
        ranked = [
            (chunk, score)
            for chunk, score in self.retrieve(query, tenant_id=tenant_id, top_k=top_k)
            if score > 0
        ]
        if not ranked:
            return KnowledgeAnswer(text="证据不足，无法回答。", citations=[])
        evidence = "\n".join(chunk.text for chunk, _ in ranked)
        return KnowledgeAnswer(
            text=f"根据知识库证据：{evidence}",
            citations=[
                Citation(
                    chunk_id=chunk.chunk_id,
                    source=chunk.source,
                    page=chunk.page,
                    score=round(score, 4),
                )
                for chunk, score in ranked
            ],
        )


def evaluate_retrieval(
    kb: KnowledgeBase,
    dataset: list[tuple[str, str]],
    *,
    tenant_id: str,
    top_k: int = 5,
) -> RetrievalMetrics:
    hits = 0
    reciprocal_ranks = 0.0
    for query, expected_chunk_id in dataset:
        ranked = kb.retrieve(query, tenant_id=tenant_id, top_k=top_k)
        ids = [chunk.chunk_id for chunk, _ in ranked]
        if expected_chunk_id in ids:
            hits += 1
            reciprocal_ranks += 1 / (ids.index(expected_chunk_id) + 1)
    count = len(dataset) or 1
    return RetrievalMetrics(recall_at_k=hits / count, mrr=reciprocal_ranks / count)


class PgVectorKnowledgeRepository:
    """项目 4 的实际 pgvector Repository；维度与本地教学 Embedding 固定为 128。"""

    def __init__(self, dsn: str) -> None:
        self.dsn = dsn.replace("postgresql+psycopg://", "postgresql://", 1)

    def initialize(self) -> None:
        statements = [
            "CREATE EXTENSION IF NOT EXISTS vector",
            """
            CREATE TABLE IF NOT EXISTS knowledge_chunks (
                tenant_id text NOT NULL,
                chunk_id text NOT NULL,
                source text NOT NULL,
                page integer NOT NULL CHECK (page > 0),
                content text NOT NULL,
                embedding vector(128) NOT NULL,
                PRIMARY KEY (tenant_id, chunk_id)
            )
            """,
            """
            CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_hnsw
            ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)
            """,
        ]
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)

    @staticmethod
    def _vector_literal(vector: list[float]) -> str:
        if len(vector) != 128:
            raise ValueError("pgvector repository requires 128 dimensions")
        return "[" + ",".join(f"{value:.10f}" for value in vector) + "]"

    def upsert(self, chunks_to_write: list[Chunk]) -> None:
        query = """
            INSERT INTO knowledge_chunks
              (tenant_id, chunk_id, source, page, content, embedding)
            VALUES (%s, %s, %s, %s, %s, %s::vector)
            ON CONFLICT (tenant_id, chunk_id) DO UPDATE SET
              source=EXCLUDED.source, page=EXCLUDED.page,
              content=EXCLUDED.content, embedding=EXCLUDED.embedding
        """
        values = [
            (
                chunk.tenant_id,
                chunk.chunk_id,
                chunk.source,
                chunk.page,
                chunk.text,
                self._vector_literal(chunk.vector),
            )
            for chunk in chunks_to_write
        ]
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.executemany(query, values)

    def search(self, query: str, *, tenant_id: str, top_k: int = 5) -> list[PgVectorHit]:
        vector = self._vector_literal(_embed(query))
        statement = """
            SELECT chunk_id, source, page, content,
                   1 - (embedding <=> %s::vector) AS score
            FROM knowledge_chunks
            WHERE tenant_id = %s
            ORDER BY embedding <=> %s::vector
            LIMIT %s
        """
        with psycopg.connect(self.dsn) as connection:
            with connection.cursor() as cursor:
                cursor.execute(statement, (vector, tenant_id, vector, top_k))
                rows = cursor.fetchall()
        return [
            PgVectorHit(
                chunk_id=str(row[0]),
                source=str(row[1]),
                page=int(row[2]),
                text=str(row[3]),
                score=float(row[4]),
            )
            for row in rows
        ]
