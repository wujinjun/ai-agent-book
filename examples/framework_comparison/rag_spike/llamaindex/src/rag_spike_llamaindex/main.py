from __future__ import annotations

import json
import math
import re
from importlib.metadata import version
from pathlib import Path
from typing import Any

from llama_index.core import Document, VectorStoreIndex
from llama_index.core.base.embeddings.base import BaseEmbedding
from llama_index.core.vector_stores import MetadataFilter, MetadataFilters

VOCABULARY = ("mcp", "stateless", "protocol", "rag", "citation", "source", "secret", "incident")


def _vector(text: str) -> list[float]:
    tokens = re.findall(r"[a-z]+", text.casefold())
    values = [float(tokens.count(term)) for term in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


class FixedEmbedding(BaseEmbedding):
    def _get_text_embedding(self, text: str) -> list[float]:
        return _vector(text)

    def _get_query_embedding(self, query: str) -> list[float]:
        return _vector(query)

    async def _aget_query_embedding(self, query: str) -> list[float]:
        return _vector(query)


def run(spec_path: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    documents = [
        Document(
            text=item["text"], id_=item["id"], metadata={"id": item["id"], "tenant": item["tenant"]}
        )
        for item in spec["documents"]
    ]
    index = VectorStoreIndex.from_documents(documents, embed_model=FixedEmbedding())
    results: list[dict[str, Any]] = []
    for query in spec["queries"]:
        filters = MetadataFilters(filters=[MetadataFilter(key="tenant", value=query["tenant"])])
        matches = index.as_retriever(similarity_top_k=3, filters=filters).retrieve(query["text"])
        top = (
            matches[0].node.metadata["id"]
            if matches and matches[0].score is not None and matches[0].score > 0.1
            else None
        )
        results.append({"query": query["id"], "top": top, "expected": query["expected"]})
    return {
        "candidate": "llamaindex",
        "version": version("llama-index-core"),
        "fixture": spec["fixture"],
        "results": results,
        "passed": all(item["top"] == item["expected"] for item in results),
    }


def main() -> None:
    spec = Path(__file__).parents[3] / "spec.json"
    print(json.dumps(run(spec), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
