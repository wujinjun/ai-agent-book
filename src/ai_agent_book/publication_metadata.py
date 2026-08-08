"""Generate glossary, references, and a cross-chapter term index."""

from __future__ import annotations

from collections import defaultdict
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml

from ai_agent_book.book_manifest import BookEntry, load_book_entries


class GlossaryItem(TypedDict):
    term: str
    category: str
    aliases: list[str]
    definition: str


class ReferenceItem(TypedDict, total=False):
    id: str
    authors: str
    title: str
    publication: str
    year: int
    url: str
    checked: str
    kind: str
    note: str


def generate_supporting_pages(root: Path, destination: Path) -> dict[str, Path]:
    """Generate deterministic supporting pages from structured metadata."""

    metadata = _load_metadata(root / "notes/publication-metadata.yml")
    glossary = cast(list[GlossaryItem], metadata["glossary"])
    references_path = root / str(metadata.get("references_file", ""))
    if not references_path.is_file():
        raise ValueError("publication metadata must define a valid references_file")
    references = cast(
        list[ReferenceItem],
        yaml.safe_load(references_path.read_text(encoding="utf-8")),
    )
    _validate_metadata(glossary, references)

    destination.mkdir(parents=True, exist_ok=True)
    outputs = {
        "glossary": destination / "glossary.md",
        "references": destination / "references.md",
        "index": destination / "book-index.md",
    }
    outputs["glossary"].write_text(_render_glossary(glossary), encoding="utf-8")
    outputs["references"].write_text(_render_references(references), encoding="utf-8")
    entries = [
        entry
        for entry in load_book_entries(root / "mkdocs.yml")
        if entry.path.match("docs/part-*/ch*.md")
    ]
    outputs["index"].write_text(
        _render_index(root, glossary, entries),
        encoding="utf-8",
    )
    return outputs


def _load_metadata(path: Path) -> dict[str, Any]:
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError("publication metadata must be a mapping")
    return cast(dict[str, Any], raw)


def _validate_metadata(
    glossary: list[GlossaryItem], references: list[ReferenceItem]
) -> None:
    terms = [item["term"] for item in glossary]
    reference_ids = [item["id"] for item in references]
    if len(terms) != len(set(terms)):
        raise ValueError("duplicate glossary term")
    if len(reference_ids) != len(set(reference_ids)):
        raise ValueError("duplicate reference id")
    if len(glossary) < 30 or len(references) < 100:
        raise ValueError("publication metadata is below the minimum coverage")
    for item in references:
        if not item.get("url", "").startswith("https://"):
            raise ValueError(f"reference {item['id']} must use an HTTPS source")


def _render_glossary(items: list[GlossaryItem]) -> str:
    lines = [
        "# 术语表",
        "",
        "> 此文件由 `notes/publication-metadata.yml` 自动生成，请勿直接编辑。",
        "",
        "| 术语 | 类别 | 定义 |",
        "|---|---|---|",
    ]
    for item in sorted(items, key=lambda value: value["term"].casefold()):
        aliases = " / ".join(item["aliases"])
        term = item["term"] + (f"（{aliases}）" if aliases else "")
        lines.append(
            f"| {_escape(term)} | {_escape(item['category'])} | {_escape(item['definition'])} |"
        )
    return "\n".join(lines) + "\n"


def _render_references(items: list[ReferenceItem]) -> str:
    lines = [
        "# 参考资料",
        "",
        "> 此文件由 `notes/publication-metadata.yml` 自动生成。"
        "具体 API 资料仍在对应章节记录版本与核对日期。",
        "",
    ]
    for index, item in enumerate(items, start=1):
        note = f" {item['note']}" if item.get("note") else ""
        checked = f" 核对：{item['checked']}。" if item.get("checked") else ""
        title = f"[{item['title']}]({item['url']})"
        lines.append(
            f"{index}. <span id=\"ref-{item['id']}\"></span>"
            f"**[{item['id']}]** {item['authors']} *{title}*. "
            f"{item['publication']}, {item['year']}.{checked}{note}"
        )
    return "\n".join(lines) + "\n"


def _render_index(root: Path, items: list[GlossaryItem], entries: list[BookEntry]) -> str:
    documents = {
        entry: (root / entry.path).read_text(encoding="utf-8").casefold()
        for entry in entries
    }
    categories: dict[str, list[GlossaryItem]] = defaultdict(list)
    for item in items:
        categories[item["category"]].append(item)

    lines = [
        "# 全书索引",
        "",
        "> 此文件由 `notes/publication-metadata.yml` 与当前章节内容自动生成。"
        "链接按术语在章节中的实际出现次数排序。",
        "",
        "索引用于快速定位概念，正式定义以[术语表](glossary.md)为准。",
    ]
    for category in sorted(categories):
        lines.extend(
            [
                "",
                f"## {category}",
                "",
                "| 术语 | 重点章节 | 出现次数 |",
                "|---|---|---:|",
            ]
        )
        for item in sorted(categories[category], key=lambda value: value["term"].casefold()):
            needles = [item["term"], *item["aliases"]]
            ranked: list[tuple[int, BookEntry]] = []
            for entry, source in documents.items():
                count = sum(source.count(needle.casefold()) for needle in needles)
                if count:
                    ranked.append((count, entry))
            ranked.sort(key=lambda pair: (-pair[0], pair[1].title))
            links = "；".join(
                f"[{entry.title}]({entry.path.relative_to('docs').as_posix()})"
                for _, entry in ranked[:5]
            )
            total = sum(count for count, _ in ranked)
            lines.append(f"| {_escape(item['term'])} | {links or '—'} | {total} |")
    return "\n".join(lines) + "\n"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
