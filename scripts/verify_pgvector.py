"""在 Compose PostgreSQL 中验证项目 4 的 pgvector 摄取与检索。"""

from __future__ import annotations

import argparse
from pathlib import Path

from ai_agent_book.apps.knowledge_agent import KnowledgeBase, PgVectorKnowledgeRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--dsn", default="postgresql://agent:agent@127.0.0.1:55432/agent_book"
    )
    parser.add_argument(
        "--document", type=Path, default=Path("docs/part-02-agent-core/ch09-agent-runtime.md")
    )
    args = parser.parse_args()
    kb = KnowledgeBase(chunk_size=300, overlap=40)
    kb.ingest(args.document, tenant_id="pgvector-verify")
    repository = PgVectorKnowledgeRepository(args.dsn)
    repository.initialize()
    repository.upsert(kb.chunks)
    hits = repository.search("Agent Runtime 如何管理工具循环？", tenant_id="pgvector-verify")
    assert hits
    assert any("Agent" in hit.text or "工具" in hit.text for hit in hits)
    print(f"pgvector verification passed: {len(kb.chunks)} chunks, {len(hits)} hits")


if __name__ == "__main__":
    main()
