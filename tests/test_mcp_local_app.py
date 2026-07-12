from pathlib import Path

import pytest

from ai_agent_book.apps.mcp_local import InProcessTransport, MCPClient, MCPLocalServer


@pytest.mark.asyncio
async def test_mcp_client_initializes_discovers_and_calls_tools(tmp_path: Path) -> None:
    (tmp_path / "note.md").write_text("MCP evidence", encoding="utf-8")
    client = MCPClient(InProcessTransport(MCPLocalServer(tmp_path)))

    initialized = await client.initialize()
    tools = await client.list_tools()
    result = await client.call_tool("read_file", {"path": "note.md"})

    assert initialized["protocolVersion"] == "2025-11-25"
    assert {tool["name"] for tool in tools} >= {"read_file", "system_info", "query_catalog"}
    assert result["content"][0]["text"] == "MCP evidence"


@pytest.mark.asyncio
async def test_mcp_server_returns_jsonrpc_errors_without_leaking_paths(tmp_path: Path) -> None:
    server = MCPLocalServer(tmp_path)
    response = await server.handle(
        {
            "jsonrpc": "2.0",
            "id": 7,
            "method": "tools/call",
            "params": {"name": "read_file", "arguments": {"path": "../secret"}},
        }
    )
    assert response["error"]["code"] == -32001
    assert str(tmp_path) not in response["error"]["message"]


@pytest.mark.asyncio
async def test_mcp_resource_can_be_read(tmp_path: Path) -> None:
    client = MCPClient(InProcessTransport(MCPLocalServer(tmp_path)))
    resources = await client.list_resources()
    resource = await client.read_resource(resources[0]["uri"])
    assert resource["contents"][0]["mimeType"] == "application/json"
