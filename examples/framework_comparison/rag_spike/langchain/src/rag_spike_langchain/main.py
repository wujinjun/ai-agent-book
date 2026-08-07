from __future__ import annotations

import json
import math
import re
from importlib.metadata import version
from pathlib import Path
from typing import Any

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

VOCABULARY = ("mcp", "stateless", "protocol", "rag", "citation", "source", "secret", "incident")


def _vector(text: str) -> list[float]:
    tokens = re.findall(r"[a-z]+", text.casefold())
    values = [float(tokens.count(term)) for term in VOCABULARY]
    norm = math.sqrt(sum(value * value for value in values)) or 1.0
    return [value / norm for value in values]


class FixedEmbeddings(Embeddings):
    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [_vector(text) for text in texts]

    def embed_query(self, text: str) -> list[float]:
        return _vector(text)


def run(spec_path: Path) -> dict[str, Any]:
    spec = json.loads(spec_path.read_text(encoding="utf-8"))
    store = InMemoryVectorStore(FixedEmbeddings())
    store.add_documents(
        [
            Document(
                page_content=item["text"], metadata={"id": item["id"], "tenant": item["tenant"]}
            )
            for item in spec["documents"]
        ]
    )
    results: list[dict[str, Any]] = []
    for query in spec["queries"]:
        matches = store.similarity_search_with_score(
            query["text"],
            k=3,
            filter=lambda doc, tenant=query["tenant"]: doc.metadata["tenant"] == tenant,
        )
        top = matches[0][0].metadata["id"] if matches and matches[0][1] > 0.1 else None
        results.append({"query": query["id"], "top": top, "expected": query["expected"]})
    return {
        "candidate": "langchain",
        "version": version("langchain"),
        "fixture": spec["fixture"],
        "results": results,
        "passed": all(item["top"] == item["expected"] for item in results),
    }


def main() -> None:
    spec = Path(__file__).parents[3] / "spec.json"
    print(json.dumps(run(spec), ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
