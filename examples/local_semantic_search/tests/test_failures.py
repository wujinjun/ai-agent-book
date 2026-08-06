import pytest

from local_semantic_search.domain import Document, LocalSearchIndex
from local_semantic_search.providers import HashedEmbedding, WrongDimensionEmbedding


def test_embedding_dimension_mismatch_is_rejected() -> None:
    index = LocalSearchIndex(HashedEmbedding(dimension=16))
    index.add_documents((Document("one", 1, "acme", "context budget"),))
    index.embedding = WrongDimensionEmbedding(dimension=8)

    with pytest.raises(ValueError, match="维度"):
        index.search_dense("context", tenant_id="acme")


def test_cross_tenant_documents_never_enter_candidate_lists() -> None:
    index = LocalSearchIndex(HashedEmbedding(dimension=32))
    index.add_documents(
        (
            Document("public", 1, "acme", "incident response"),
            Document("secret", 1, "other", "incident response secret"),
        )
    )

    for search in (index.search_sparse, index.search_dense, index.search_hybrid):
        assert [hit.document_id for hit in search("incident response", tenant_id="acme")] == [
            "public"
        ]


def test_stale_version_cannot_overwrite_current_document() -> None:
    index = LocalSearchIndex(HashedEmbedding(dimension=16))
    index.add_documents((Document("guide", 2, "acme", "current"),))

    with pytest.raises(ValueError, match="版本"):
        index.add_documents((Document("guide", 1, "acme", "stale"),))
