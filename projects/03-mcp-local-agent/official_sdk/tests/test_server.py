from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest
from mcp.client import Client
from mcp.client.stdio import StdioServerParameters, stdio_client

from mcp_local_official.server import create_server


@pytest.mark.asyncio
async def test_official_client_discovers_tool_resource_and_prompt(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("MCP v2 evidence", encoding="utf-8")
    async with Client(create_server(tmp_path)) as client:
        tools = await client.list_tools()
        result = await client.call_tool("read_file", {"path": "note.md"})
        resources = await client.list_resources()
        resource = await client.read_resource("catalog://chapters")
        prompts = await client.list_prompts()
        prompt = await client.get_prompt("review_file", {"path": "note.md"})

    assert {tool.name for tool in tools.tools} == {"query_catalog", "read_file", "system_info"}
    assert result.is_error is False
    assert result.structured_content == {"result": "MCP v2 evidence"}
    assert [str(item.uri) for item in resources.resources] == ["catalog://chapters"]
    assert json.loads(resource.contents[0].text)["version"] == 1  # type: ignore[union-attr]
    assert [item.name for item in prompts.prompts] == ["review_file"]
    assert "note.md" in prompt.messages[0].content.text  # type: ignore[union-attr]


@pytest.mark.asyncio
@pytest.mark.parametrize("path", ["../secret.md", "/etc/passwd", "missing.md", "image.png"])
async def test_file_policy_returns_sanitized_tool_error(tmp_path: Path, path: str) -> None:
    async with Client(create_server(tmp_path)) as client:
        result = await client.call_tool("read_file", {"path": path})

    assert result.is_error is True
    rendered = " ".join(getattr(item, "text", "") for item in result.content)
    assert str(tmp_path) not in rendered
    assert "/etc/passwd" not in rendered


def test_streamable_http_app_is_stateless_and_has_mcp_route(tmp_path: Path) -> None:
    app = create_server(tmp_path).streamable_http_app(
        stateless_http=True,
        json_response=True,
        host="127.0.0.1",
    )

    assert any(getattr(route, "path", None) == "/mcp" for route in app.routes)


@pytest.mark.asyncio
async def test_stdio_transport_spawns_real_server_process(tmp_path: Path) -> None:
    (tmp_path / "stdio.md").write_text("stdio evidence", encoding="utf-8")
    params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_local_official.main", "--transport", "stdio"],
        env={"MCP_ALLOWED_ROOT": str(tmp_path)},
    )
    async with Client(stdio_client(params), read_timeout_seconds=2) as client:
        result = await client.call_tool("read_file", {"path": "stdio.md"})

    assert result.structured_content == {"result": "stdio evidence"}


def _reserve_port() -> int:
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        return int(probe.getsockname()[1])


def _start_http_server(root: Path, port: int) -> subprocess.Popen[bytes]:
    environment = os.environ.copy()
    environment.update(
        {"MCP_ALLOWED_ROOT": str(root), "MCP_HOST": "127.0.0.1", "MCP_PORT": str(port)}
    )
    return subprocess.Popen(  # noqa: S603 - fixed interpreter and module
        [sys.executable, "-m", "mcp_local_official.main", "--transport", "streamable-http"],
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def _wait_for_port(port: int, timeout: float = 5.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        with socket.socket() as probe:
            if probe.connect_ex(("127.0.0.1", port)) == 0:
                return
        time.sleep(0.02)
    raise TimeoutError("Streamable HTTP server did not start")


def _stop_process(process: subprocess.Popen[bytes]) -> None:
    process.terminate()
    try:
        process.wait(timeout=3)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=3)


@pytest.mark.asyncio
async def test_streamable_http_transport_calls_real_server(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "http.md").write_text("http evidence", encoding="utf-8")
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    for key in ("ALL_PROXY", "all_proxy", "HTTP_PROXY", "http_proxy", "HTTPS_PROXY", "https_proxy"):
        monkeypatch.delenv(key, raising=False)
    port = _reserve_port()
    process = await asyncio.to_thread(_start_http_server, tmp_path, port)
    try:
        await asyncio.to_thread(_wait_for_port, port)
        async with Client(
            f"http://127.0.0.1:{port}/mcp", read_timeout_seconds=2
        ) as client:
            result = await client.call_tool("read_file", {"path": "http.md"})
        assert result.structured_content == {"result": "http evidence"}
    finally:
        await asyncio.to_thread(_stop_process, process)
