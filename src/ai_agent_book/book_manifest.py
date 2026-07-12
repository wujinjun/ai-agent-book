"""Canonical book order derived from the MkDocs navigation tree."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml


class _MkDocsNavigationLoader(yaml.SafeLoader):  # type: ignore[misc]
    """Safe YAML loader that treats MkDocs callable references as plain strings."""


def _construct_python_name(
    loader: _MkDocsNavigationLoader, suffix: str, node: yaml.Node
) -> str:
    del loader, node
    return suffix


_MkDocsNavigationLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/name:", _construct_python_name
)


@dataclass(frozen=True, slots=True)
class BookEntry:
    """One Markdown document in publication order."""

    title: str
    path: Path
    depth: int


def load_book_entries(config_path: Path) -> list[BookEntry]:
    """Load and validate the flattened navigation from a MkDocs config file."""

    config_path = config_path.resolve()
    raw = yaml.load(
        config_path.read_text(encoding="utf-8"),
        Loader=_MkDocsNavigationLoader,
    )
    if not isinstance(raw, dict):
        raise ValueError("MkDocs config must be a mapping")

    docs_dir = raw.get("docs_dir", "docs")
    nav = raw.get("nav")
    if not isinstance(docs_dir, str) or not isinstance(nav, list):
        raise ValueError("MkDocs config requires string docs_dir and list nav")

    repository_root = config_path.parent
    entries: list[BookEntry] = []
    _flatten_nav(nav, depth=0, docs_dir=docs_dir, entries=entries)

    seen: set[Path] = set()
    for entry in entries:
        if entry.path in seen:
            raise ValueError(f"duplicate navigation path: {entry.path.as_posix()}")
        seen.add(entry.path)
        if not (repository_root / entry.path).is_file():
            raise ValueError(f"navigation file does not exist: {entry.path.as_posix()}")
    return entries


def load_publication_entries(config_path: Path) -> list[BookEntry]:
    """Return book navigation with all ten project READMEs inserted after Part VI."""

    config_path = config_path.resolve()
    root = config_path.parent
    book_entries = load_book_entries(config_path)
    project_entries: list[BookEntry] = []
    for readme in sorted((root / "projects").glob("[0-9][0-9]-*/README.md")):
        relative = readme.relative_to(root)
        source = readme.read_text(encoding="utf-8")
        heading = next(
            (
                line.removeprefix("# ").strip()
                for line in source.splitlines()
                if line.startswith("# ")
            ),
            readme.parent.name,
        )
        project_entries.append(BookEntry(heading, relative, 1))
    if len(project_entries) != 10:
        raise ValueError(f"expected 10 project READMEs, found {len(project_entries)}")

    result: list[BookEntry] = []
    inserted = False
    for entry in book_entries:
        result.append(entry)
        if entry.path == Path("docs/part-06-projects/index.md"):
            result.extend(project_entries)
            inserted = True
    if not inserted:
        raise ValueError("Part VI index is missing from MkDocs navigation")
    return result


def _flatten_nav(
    nodes: list[Any],
    *,
    depth: int,
    docs_dir: str,
    entries: list[BookEntry],
) -> None:
    for node in nodes:
        if isinstance(node, str):
            title = Path(node).stem
            entries.append(BookEntry(title, Path(docs_dir) / node, depth))
            continue
        if not isinstance(node, dict) or len(node) != 1:
            raise ValueError(f"invalid navigation node: {node!r}")

        title, target = next(iter(node.items()))
        if not isinstance(title, str):
            raise ValueError(f"navigation title must be a string: {title!r}")
        if isinstance(target, str):
            entries.append(BookEntry(title, Path(docs_dir) / target, depth))
        elif isinstance(target, list):
            _flatten_nav(
                target,
                depth=depth + 1,
                docs_dir=docs_dir,
                entries=entries,
            )
        else:
            raise ValueError(f"invalid navigation target for {title!r}: {target!r}")
