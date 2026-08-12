"""项目 4：本地可运行的多格式摄取、检索、重排、引用与评估。"""

from __future__ import annotations

import json
import math
import re
import sqlite3
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path
from typing import Literal
from uuid import uuid4
from zipfile import BadZipFile, ZipFile

import psycopg
from fastapi import FastAPI
from pydantic import BaseModel, Field

from ai_agent_book.project_service import PrincipalDep


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


class GoldenCase(BaseModel):
    query: str
    expected_text: str


class IngestionJob(BaseModel):
    job_id: str
    tenant_id: str
    source: str
    source_hash: str
    status: Literal["queued", "running", "succeeded", "failed"]
    attempts: int = Field(ge=0)
    version_id: str | None = None
    error_type: str | None = None


class IndexVersion(BaseModel):
    version_id: str
    tenant_id: str
    source_hash: str
    status: Literal["candidate", "active", "archived", "rejected"]
    recall_at_k: float = Field(ge=0, le=1)
    mrr: float = Field(ge=0, le=1)
    chunk_count: int = Field(ge=0)


class VersionedKnowledgePipeline:
    """Durable ingestion queue with evaluation-gated index activation.

    The pipeline uses the deterministic embedding only as an offline adapter. The
    versioning, tenant boundary, release gate and recovery rules are production
    concerns and remain unchanged when a real embedding/reranker is injected.
    """

    def __init__(
        self,
        database_path: Path,
        *,
        minimum_recall: float = 0.8,
        minimum_mrr: float = 0.7,
        chunk_size: int = 400,
        overlap: int = 60,
    ) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self.minimum_recall = minimum_recall
        self.minimum_mrr = minimum_mrr
        self.chunk_size = chunk_size
        self.overlap = overlap
        self._migrate()

    @staticmethod
    def _now() -> str:
        return datetime.now(UTC).isoformat(timespec="milliseconds")

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=5)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        return connection

    def _migrate(self) -> None:
        with self._connect() as db:
            db.executescript(
                """
                CREATE TABLE IF NOT EXISTS ingestion_jobs (
                    job_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    golden_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    attempts INTEGER NOT NULL DEFAULT 0,
                    version_id TEXT,
                    error_type TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    UNIQUE(tenant_id, source_hash)
                );
                CREATE TABLE IF NOT EXISTS index_versions (
                    version_id TEXT PRIMARY KEY,
                    tenant_id TEXT NOT NULL,
                    source_hash TEXT NOT NULL,
                    status TEXT NOT NULL,
                    recall_at_k REAL NOT NULL,
                    mrr REAL NOT NULL,
                    chunk_count INTEGER NOT NULL,
                    chunks_json TEXT NOT NULL,
                    chunks_hash TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL
                );
                CREATE UNIQUE INDEX IF NOT EXISTS one_active_index_per_tenant
                    ON index_versions(tenant_id) WHERE status='active';
                CREATE TABLE IF NOT EXISTS ingestion_events (
                    sequence INTEGER PRIMARY KEY AUTOINCREMENT,
                    job_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )
            columns = {
                str(row[1]) for row in db.execute("PRAGMA table_info(index_versions)").fetchall()
            }
            if "chunks_hash" not in columns:
                db.execute(
                    "ALTER TABLE index_versions ADD COLUMN chunks_hash TEXT NOT NULL DEFAULT ''"
                )
            rows = db.execute(
                "SELECT version_id,chunks_json FROM index_versions WHERE chunks_hash=''"
            ).fetchall()
            for row in rows:
                db.execute(
                    "UPDATE index_versions SET chunks_hash=? WHERE version_id=?",
                    (sha256(str(row["chunks_json"]).encode()).hexdigest(), row["version_id"]),
                )

    @staticmethod
    def _job(row: sqlite3.Row) -> IngestionJob:
        return IngestionJob(
            job_id=row["job_id"],
            tenant_id=row["tenant_id"],
            source=row["source"],
            source_hash=row["source_hash"],
            status=row["status"],
            attempts=row["attempts"],
            version_id=row["version_id"],
            error_type=row["error_type"],
        )

    def _fingerprint(self, source: Path, golden_json: str) -> str:
        material = b"\0".join(
            (
                source.read_bytes(),
                golden_json.encode(),
                f"chunk={self.chunk_size};overlap={self.overlap}".encode(),
            )
        )
        return sha256(material).hexdigest()

    def submit(
        self,
        path: Path,
        *,
        tenant_id: str,
        golden_cases: list[GoldenCase],
    ) -> tuple[IngestionJob, bool]:
        source = path.resolve()
        golden_json = json.dumps(
            [case.model_dump() for case in golden_cases], ensure_ascii=False, sort_keys=True
        )
        source_hash = self._fingerprint(source, golden_json)
        now = self._now()
        with self._connect() as db:
            existing = db.execute(
                "SELECT * FROM ingestion_jobs WHERE tenant_id=? AND source_hash=?",
                (tenant_id, source_hash),
            ).fetchone()
            if existing:
                return self._job(existing), False
            job_id = str(uuid4())
            db.execute(
                """INSERT INTO ingestion_jobs
                   (job_id,tenant_id,source,source_hash,golden_json,status,created_at,updated_at)
                   VALUES (?,?,?,?,?,'queued',?,?)""",
                (
                    job_id,
                    tenant_id,
                    str(source),
                    source_hash,
                    golden_json,
                    now,
                    now,
                ),
            )
            db.execute(
                "INSERT INTO ingestion_events(job_id,event_type,created_at) VALUES (?,?,?)",
                (job_id, "queued", now),
            )
            row = db.execute("SELECT * FROM ingestion_jobs WHERE job_id=?", (job_id,)).fetchone()
            assert row is not None
            return self._job(row), True

    def recover_incomplete(self) -> int:
        """Return interrupted leases to the queue after a process restart."""
        with self._connect() as db:
            rows = db.execute(
                "SELECT job_id FROM ingestion_jobs WHERE status='running'"
            ).fetchall()
            now = self._now()
            db.execute(
                "UPDATE ingestion_jobs SET status='queued',updated_at=? WHERE status='running'",
                (now,),
            )
            for row in rows:
                db.execute(
                    "INSERT INTO ingestion_events(job_id,event_type,created_at) VALUES (?,?,?)",
                    (row["job_id"], "recovered", now),
                )
        return len(rows)

    def process_next(self, *, tenant_id: str | None = None) -> IngestionJob | None:
        with self._connect() as db:
            if tenant_id is None:
                row = db.execute(
                    """SELECT * FROM ingestion_jobs WHERE status='queued'
                       ORDER BY created_at LIMIT 1"""
                ).fetchone()
            else:
                row = db.execute(
                    """SELECT * FROM ingestion_jobs
                       WHERE status='queued' AND tenant_id=?
                       ORDER BY created_at LIMIT 1""",
                    (tenant_id,),
                ).fetchone()
            if row is None:
                return None
            job_id = str(row["job_id"])
            attempts = int(row["attempts"]) + 1
            db.execute(
                """UPDATE ingestion_jobs SET status='running',attempts=?,updated_at=?
                   WHERE job_id=? AND status='queued'""",
                (attempts, self._now(), job_id),
            )

        try:
            return self._build_candidate(job_id)
        except Exception as exc:
            with self._connect() as db:
                db.execute(
                    """UPDATE ingestion_jobs SET status='failed',error_type=?,updated_at=?
                       WHERE job_id=?""",
                    (type(exc).__name__, self._now(), job_id),
                )
                db.execute(
                    "INSERT INTO ingestion_events(job_id,event_type,created_at) VALUES (?,?,?)",
                    (job_id, "failed", self._now()),
                )
                failed = db.execute(
                    "SELECT * FROM ingestion_jobs WHERE job_id=?", (job_id,)
                ).fetchone()
                assert failed is not None
                return self._job(failed)

    def _build_candidate(self, job_id: str) -> IngestionJob:
        with self._connect() as db:
            job = db.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            assert job is not None
        source = Path(str(job["source"]))
        if self._fingerprint(source, str(job["golden_json"])) != job["source_hash"]:
            raise ValueError("source changed after ingestion was queued")
        kb = KnowledgeBase(chunk_size=self.chunk_size, overlap=self.overlap)
        kb.ingest(source, tenant_id=str(job["tenant_id"]))
        golden = [GoldenCase.model_validate(item) for item in json.loads(job["golden_json"])]
        dataset: list[tuple[str, str]] = []
        for case in golden:
            expected = next(
                (chunk.chunk_id for chunk in kb.chunks if case.expected_text in chunk.text),
                "missing-expected-chunk",
            )
            dataset.append((case.query, expected))
        metrics = evaluate_retrieval(kb, dataset, tenant_id=str(job["tenant_id"]))
        version_seed = (
            f"{job['tenant_id']}:{job['source_hash']}:{self.chunk_size}:{self.overlap}"
        )
        version_id = sha256(version_seed.encode()).hexdigest()[:20]
        accepted = (
            bool(kb.chunks)
            and metrics.recall_at_k >= self.minimum_recall
            and metrics.mrr >= self.minimum_mrr
        )
        version_status = "active" if accepted else "rejected"
        now = self._now()
        chunks_json = json.dumps(
            [chunk.model_dump() for chunk in kb.chunks],
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        chunks_hash = sha256(chunks_json.encode()).hexdigest()
        with self._connect() as db:
            if accepted:
                db.execute(
                    """UPDATE index_versions SET status='archived'
                       WHERE tenant_id=? AND status='active'""",
                    (job["tenant_id"],),
                )
            db.execute(
                """INSERT OR REPLACE INTO index_versions
                   (version_id,tenant_id,source_hash,status,recall_at_k,mrr,
                    chunk_count,chunks_json,chunks_hash,created_at)
                   VALUES (?,?,?,?,?,?,?,?,?,?)""",
                (
                    version_id,
                    job["tenant_id"],
                    job["source_hash"],
                    version_status,
                    metrics.recall_at_k,
                    metrics.mrr,
                    len(kb.chunks),
                    chunks_json,
                    chunks_hash,
                    now,
                ),
            )
            db.execute(
                """UPDATE ingestion_jobs SET status='succeeded',version_id=?,updated_at=?
                   WHERE job_id=?""",
                (version_id, now, job_id),
            )
            db.execute(
                "INSERT INTO ingestion_events(job_id,event_type,created_at) VALUES (?,?,?)",
                (job_id, "activated" if accepted else "rejected", now),
            )
            completed = db.execute(
                "SELECT * FROM ingestion_jobs WHERE job_id=?", (job_id,)
            ).fetchone()
            assert completed is not None
            return self._job(completed)

    def active_version(self, tenant_id: str) -> IndexVersion | None:
        with self._connect() as db:
            row = db.execute(
                """SELECT * FROM index_versions
                   WHERE tenant_id=? AND status='active'""",
                (tenant_id,),
            ).fetchone()
        if row is None:
            return None
        return IndexVersion(
            version_id=row["version_id"],
            tenant_id=row["tenant_id"],
            source_hash=row["source_hash"],
            status=row["status"],
            recall_at_k=row["recall_at_k"],
            mrr=row["mrr"],
            chunk_count=row["chunk_count"],
        )

    def answer(self, query: str, *, tenant_id: str, top_k: int = 3) -> KnowledgeAnswer:
        with self._connect() as db:
            row = db.execute(
                """SELECT chunks_json,chunks_hash FROM index_versions
                   WHERE tenant_id=? AND status='active'""",
                (tenant_id,),
            ).fetchone()
        if row is None:
            return KnowledgeAnswer(text="证据不足，无法回答。", citations=[])
        chunks_json = str(row["chunks_json"])
        if sha256(chunks_json.encode()).hexdigest() != row["chunks_hash"]:
            raise ValueError("active index chunk digest mismatch")
        kb = KnowledgeBase(chunk_size=self.chunk_size, overlap=self.overlap)
        kb.chunks = [Chunk.model_validate(item) for item in json.loads(chunks_json)]
        return kb.answer(query, tenant_id=tenant_id, top_k=top_k)

    def rollback(self, tenant_id: str, version_id: str) -> IndexVersion:
        """原子激活同租户已归档版本；拒绝版本不能绕过发布门禁。"""
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            target = db.execute(
                """SELECT * FROM index_versions
                   WHERE tenant_id=? AND version_id=? AND status='archived'""",
                (tenant_id, version_id),
            ).fetchone()
            if target is None:
                raise KeyError(version_id)
            chunks_json = str(target["chunks_json"])
            if sha256(chunks_json.encode()).hexdigest() != target["chunks_hash"]:
                raise ValueError("rollback target chunk digest mismatch")
            db.execute(
                "UPDATE index_versions SET status='archived' WHERE tenant_id=? AND status='active'",
                (tenant_id,),
            )
            updated = db.execute(
                """UPDATE index_versions SET status='active'
                   WHERE tenant_id=? AND version_id=? AND status='archived'""",
                (tenant_id, version_id),
            )
            if updated.rowcount != 1:
                raise RuntimeError("rollback target changed during activation")
        active = self.active_version(tenant_id)
        assert active is not None
        return active


class IngestionCreate(BaseModel):
    content: str = Field(min_length=1, max_length=2_000_000)
    golden_cases: list[GoldenCase] = Field(min_length=1, max_length=100)


class KnowledgeQuery(BaseModel):
    query: str = Field(min_length=1, max_length=20_000)
    top_k: int = Field(default=3, ge=1, le=20)


def attach_knowledge_routes(
    app: FastAPI,
    pipeline: VersionedKnowledgePipeline,
    *,
    import_root: Path,
) -> None:
    """Attach tenant-scoped ingestion, worker and query routes to project 4."""
    import_root.mkdir(parents=True, exist_ok=True)

    @app.post("/v1/knowledge/ingestions", response_model=IngestionJob)
    async def create_ingestion(body: IngestionCreate, principal: PrincipalDep) -> IngestionJob:
        principal.require("project:run")
        tenant_dir = import_root / sha256(principal.tenant_id.encode()).hexdigest()[:16]
        tenant_dir.mkdir(parents=True, exist_ok=True)
        content_hash = sha256(body.content.encode()).hexdigest()
        source = tenant_dir / f"{content_hash}.md"
        if not source.exists():
            source.write_text(body.content, encoding="utf-8")
        job, _ = pipeline.submit(
            source,
            tenant_id=principal.tenant_id,
            golden_cases=body.golden_cases,
        )
        return job

    @app.post("/v1/knowledge/worker/process-one", response_model=IngestionJob | None)
    async def process_ingestion(principal: PrincipalDep) -> IngestionJob | None:
        principal.require("project:admin")
        return pipeline.process_next(tenant_id=principal.tenant_id)

    @app.get("/v1/knowledge/index", response_model=IndexVersion | None)
    async def active_index(principal: PrincipalDep) -> IndexVersion | None:
        return pipeline.active_version(principal.tenant_id)

    @app.post("/v1/knowledge/query", response_model=KnowledgeAnswer)
    async def query_knowledge(body: KnowledgeQuery, principal: PrincipalDep) -> KnowledgeAnswer:
        return pipeline.answer(body.query, tenant_id=principal.tenant_id, top_k=body.top_k)
