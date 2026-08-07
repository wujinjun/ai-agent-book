"""A constrained MCPServer built with the official MCP Python SDK 2.0.0."""

from __future__ import annotations

import json
import platform
from pathlib import Path

from mcp.server import MCPServer
from mcp.shared.path_security import PathEscapeError, safe_join

MAX_TEXT_BYTES = 64 * 1024
ALLOWED_SUFFIXES = {".md", ".py", ".txt"}
CATALOG: tuple[dict[str, int | str], ...] = (
    {"chapter": 11, "title": "MCP 基础"},
    {"chapter": 12, "title": "MCP Server 实战"},
)


def _read_allowed_text(root: Path, relative_path: str) -> str:
    try:
        target = safe_join(root, relative_path)
    except PathEscapeError as exc:
        raise ValueError("path is outside the allowed root") from exc
    if target.suffix.lower() not in ALLOWED_SUFFIXES:
        raise ValueError("file type is not allowed")
    if not target.is_file():
        raise ValueError("file is unavailable")
    if target.stat().st_size > MAX_TEXT_BYTES:
        raise ValueError("file exceeds the read limit")
    try:
        return target.read_text(encoding="utf-8")
    except UnicodeDecodeError as exc:
        raise ValueError("file is not valid UTF-8 text") from exc


def create_server(allowed_root: Path) -> MCPServer[None]:
    """Create a stateless-capable server whose handlers re-check authorization."""

    root = allowed_root.resolve()
    server: MCPServer[None] = MCPServer(
        "ai-agent-book-local",
        version="2.0.0",
        instructions="Read-only textbook tools. Never expose physical host paths.",
    )

    @server.tool(description="Read one UTF-8 text file below the configured root.")
    def read_file(path: str) -> str:
        return _read_allowed_text(root, path)

    @server.tool(description="Return a small allowlist of non-sensitive runtime fields.")
    def system_info() -> dict[str, str]:
        return {"python": platform.python_version(), "system": platform.system()}

    @server.tool(description="Search the fixed textbook chapter catalog.")
    def query_catalog(keyword: str) -> list[dict[str, int | str]]:
        normalized = keyword.strip().casefold()
        return [
            dict(item)
            for item in CATALOG
            if not normalized or normalized in str(item["title"]).casefold()
        ]

    @server.resource(
        "catalog://chapters",
        name="textbook-chapters",
        description="Versioned local chapter catalog.",
        mime_type="application/json",
    )
    def chapter_catalog() -> str:
        return json.dumps({"version": 1, "chapters": CATALOG}, ensure_ascii=False)

    @server.prompt(description="Prepare a bounded, read-only review request.")
    def review_file(path: str) -> str:
        return (
            "Review the named file for correctness and security. "
            f"Use read_file only after policy validation. Logical path: {path}"
        )

    return server
