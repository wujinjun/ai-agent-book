from pathlib import Path

import pytest

from ai_agent_book.apps.mcp_local import InProcessTransport, MCPClient, MCPLocalServer


@pytest.mark.asyncio
async def test_mcp_discovers_tools(tmp_path: Path) -> None:
    client = MCPClient(InProcessTransport(MCPLocalServer(tmp_path)))
    await client.initialize()
    assert {tool["name"] for tool in await client.list_tools()} >= {"read_file", "system_info"}
