"""Run the bilingual offline retrieval fixture and print Recall/MRR."""

import argparse
import json
from dataclasses import asdict

from local_semantic_search.domain import LocalSearchIndex, evaluate_queries
from local_semantic_search.providers import HashedEmbedding, bilingual_fixture


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fixture", choices=("bilingual",), default="bilingual")
    args = parser.parse_args()
    del args

    index = LocalSearchIndex(HashedEmbedding(dimension=64))
    index.add_documents(bilingual_fixture())
    query = "context budget 上下文预算"
    hits = index.search_hybrid(query, tenant_id="acme", limit=3)
    report = evaluate_queries(index, tenant_id="acme", limit=3)
    print(
        json.dumps(
            {
                "query": query,
                "hits": [asdict(hit) for hit in hits],
                "evaluation": asdict(report),
                "warning": "Hash Fixture 仅用于离线控制流，不代表真实语义模型质量",
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
