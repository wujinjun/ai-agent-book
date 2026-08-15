"""Generate glossary, references, and a cross-chapter term index."""

from __future__ import annotations

import re
from collections import defaultdict
from pathlib import Path
from typing import Any, TypedDict, cast

import yaml
from markdown.extensions.toc import slugify, unique  # type: ignore[import-untyped]

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
        "本书采用“首次出现时给出中文解释，后续保留业界常用英文写法”的原则。"
        "协议名、框架名和代码标识不强行翻译；同一概念的别名只用于检索，不表示它们在所有语境下完全等价。",
        "",
        "## 写法约定",
        "",
        "| 类型 | 正文写法 | 说明 |",
        "|---|---|---|",
        "| 协议与框架 | MCP、LangGraph、PydanticAI | 保留官方名称与大小写 |",
        "| 核心工程词 | Tool、Runtime、Memory、Handoff、Guardrail | "
        "首次出现附中文解释，后续保持英文术语稳定 |",
        "| 组合词 | Multi-Agent、Tool Calling、Structured Output | "
        "使用半角连字符与空格，不在同章内混用多个译名 |",
        "| 缩写 | RAG、SSE、SLO、PII | 首次出现展开全称，后续可使用缩写 |",
    ]
    categories: dict[str, list[GlossaryItem]] = defaultdict(list)
    for item in items:
        categories[item["category"]].append(item)
    for category in sorted(categories):
        lines.extend(
            [
                "",
                f"## {category}",
                "",
                "| 术语与别名 | 定义 |",
                "|---|---|",
            ]
        )
        for item in sorted(
            categories[category], key=lambda value: value["term"].casefold()
        ):
            aliases = " / ".join(item["aliases"])
            term = item["term"] + (f"（{aliases}）" if aliases else "")
            lines.append(f"| {_escape(term)} | {_escape(item['definition'])} |")
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
        entry: (root / entry.path).read_text(encoding="utf-8") for entry in entries
    }
    sections = {entry: _parse_sections(source) for entry, source in documents.items()}
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
            ranked: list[tuple[int, BookEntry, str, str]] = []
            for entry, chapter_sections in sections.items():
                for heading, anchor, body in chapter_sections:
                    source = body.casefold()
                    count = sum(source.count(needle.casefold()) for needle in needles)
                    if count:
                        ranked.append((count, entry, heading, anchor))
            ranked.sort(key=lambda match: (-match[0], match[1].title, match[2]))
            links = "；".join(
                f"[{entry.title} · {heading}]"
                f"({entry.path.relative_to('docs').as_posix()}#{anchor})"
                for _, entry, heading, anchor in ranked[:5]
            )
            total = sum(count for count, *_ in ranked)
            lines.append(f"| {_escape(item['term'])} | {links or '—'} | {total} |")

    lines.extend(
        [
            "",
            "## 图表索引",
            "",
            "这里统计正文中的 Mermaid 工程图与插图。链接指向图所在小节；"
            "图后的正文负责解释阅读顺序、关键关系和工程结论。",
            "",
            "| 章节 | Mermaid | 插图 | 图示所在小节 |",
            "|---|---:|---:|---|",
        ]
    )
    for entry, source in documents.items():
        mermaid_count, image_count, topics = _asset_summary(source, kind="figure")
        image_total = cast(int, image_count)
        if not mermaid_count and not image_total:
            continue
        links = _topic_links(entry, topics)
        lines.append(
            f"| [{entry.title}]({entry.path.relative_to('docs').as_posix()}) | "
            f"{mermaid_count} | {image_total} | {links} |"
        )

    lines.extend(
        [
            "",
            "## 代码清单索引",
            "",
            "代码块按章节统计，Mermaid 不计入代码清单。语言标识来自 Markdown 围栏，"
            "可用于快速定位 Python、YAML、Shell、Dockerfile 等工程示例。",
            "",
            "| 章节 | 代码块 | 主要语言 | 代码所在小节 |",
            "|---|---:|---|---|",
        ]
    )
    for entry, source in documents.items():
        count, languages, topics = _asset_summary(source, kind="code")
        language_names = cast(list[str], languages)
        if not count:
            continue
        links = _topic_links(entry, topics)
        lines.append(
            f"| [{entry.title}]({entry.path.relative_to('docs').as_posix()}) | "
            f"{count} | {_escape('、'.join(language_names))} | {links} |"
        )
    return "\n".join(lines) + "\n"


def _parse_sections(source: str) -> list[tuple[str, str, str]]:
    """Split Markdown into linkable h2/h3 sections using MkDocs-compatible slugs."""

    lines = source.splitlines()
    headings: list[tuple[int, int, str, str]] = []
    for index, level, title, anchor in _markdown_headings(lines):
        if level >= 2:
            headings.append((index, level, title, anchor))

    sections: list[tuple[str, str, str]] = []
    for position, (start, level, title, anchor) in enumerate(headings):
        end = len(lines)
        for candidate, candidate_level, *_ in headings[position + 1 :]:
            if candidate_level <= level:
                end = candidate
                break
        sections.append((title, anchor, "\n".join(lines[start:end])))
    return sections


def _asset_summary(
    source: str, *, kind: str
) -> tuple[int, int | list[str], list[tuple[str, str]]]:
    """Return figure or code counts plus the nearest linkable section headings."""

    lines = source.splitlines()
    headings = _heading_positions(lines)
    positions: list[int] = []
    languages: list[str] = []
    in_fence = False
    current_language = ""
    mermaid_count = 0
    image_count = 0
    for index, line in enumerate(lines):
        fence = re.match(r"^```\s*([\w.+-]*)", line)
        if fence:
            if not in_fence:
                in_fence = True
                current_language = fence.group(1).lower()
                if kind == "figure" and current_language == "mermaid":
                    mermaid_count += 1
                    positions.append(index)
                elif kind == "code" and current_language != "mermaid":
                    positions.append(index)
                    languages.append(current_language or "text")
            else:
                in_fence = False
                current_language = ""
            continue
        if kind == "figure" and not in_fence and re.search(r"!\[[^]]*]\([^)]+\)", line):
            image_count += 1
            positions.append(index)

    topics: list[tuple[str, str]] = []
    for position in positions:
        preceding = [heading for heading in headings if heading[0] <= position]
        if preceding:
            _, title, anchor = preceding[-1]
            if (title, anchor) not in topics:
                topics.append((title, anchor))
    if kind == "figure":
        return mermaid_count, image_count, topics[:4]
    ordered_languages = list(dict.fromkeys(languages))
    return len(positions), ordered_languages[:5], topics[:4]


def _heading_positions(lines: list[str]) -> list[tuple[int, str, str]]:
    return [
        (index, title, anchor)
        for index, level, title, anchor in _markdown_headings(lines)
        if level >= 2
    ]


def _markdown_headings(lines: list[str]) -> list[tuple[int, int, str, str]]:
    """Return real Markdown headings while ignoring fenced-code contents."""

    used_ids: set[str] = set()
    headings: list[tuple[int, int, str, str]] = []
    in_fence = False
    for index, line in enumerate(lines):
        if re.match(r"^```", line):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        match = re.match(r"^(#{1,3})\s+(.+?)\s*$", line)
        if not match:
            continue
        level = len(match.group(1))
        title = re.sub(r"\s+#+$", "", match.group(2)).strip()
        anchor = unique(slugify(title, "-"), used_ids)
        headings.append((index, level, title, anchor))
    return headings


def _topic_links(entry: BookEntry, topics: list[tuple[str, str]]) -> str:
    path = entry.path.relative_to("docs").as_posix()
    return "；".join(f"[{title}]({path}#{anchor})" for title, anchor in topics) or "—"


def _escape(value: str) -> str:
    return value.replace("|", "\\|").replace("\n", " ")
