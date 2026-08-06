from local_semantic_search.domain import Document, LocalSearchIndex, evaluate_queries
from local_semantic_search.providers import HashedEmbedding, bilingual_fixture


def test_sparse_dense_and_rrf_hybrid_return_authorized_results() -> None:
    index = LocalSearchIndex(HashedEmbedding(dimension=64))
    index.add_documents(bilingual_fixture())

    sparse = index.search_sparse("如何配置 context budget", tenant_id="acme", limit=3)
    dense = index.search_dense("上下文预算", tenant_id="acme", limit=3)
    hybrid = index.search_hybrid("context budget 上下文预算", tenant_id="acme", limit=3)

    assert sparse[0].document_id == "context-budget"
    assert dense[0].document_id == "context-budget"
    assert hybrid[0].document_id == "context-budget"
    assert all(hit.tenant_id == "acme" for hit in sparse + dense + hybrid)


def test_fixed_query_set_reports_recall_and_mrr() -> None:
    index = LocalSearchIndex(HashedEmbedding(dimension=64))
    index.add_documents(bilingual_fixture())

    report = evaluate_queries(index, tenant_id="acme", limit=3)

    assert report.query_count == 3
    assert report.recall_at_k == 1.0
    assert report.mean_reciprocal_rank == 1.0


def test_newer_document_version_replaces_old_chunks() -> None:
    index = LocalSearchIndex(HashedEmbedding(dimension=32))
    index.add_documents((Document("guide", 1, "acme", "legacy retry rule"),))
    index.add_documents((Document("guide", 2, "acme", "current timeout policy"),))

    hits = index.search_sparse("timeout", tenant_id="acme", limit=3)

    assert [(hit.document_id, hit.version) for hit in hits] == [("guide", 2)]
