CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS knowledge_chunks (
    tenant_id text NOT NULL,
    chunk_id text NOT NULL,
    source text NOT NULL,
    page integer NOT NULL CHECK (page > 0),
    content text NOT NULL,
    embedding vector(128) NOT NULL,
    metadata jsonb NOT NULL DEFAULT '{}'::jsonb,
    PRIMARY KEY (tenant_id, chunk_id)
);

CREATE INDEX IF NOT EXISTS knowledge_chunks_embedding_hnsw
ON knowledge_chunks USING hnsw (embedding vector_cosine_ops);

CREATE INDEX IF NOT EXISTS knowledge_chunks_tenant
ON knowledge_chunks (tenant_id);
