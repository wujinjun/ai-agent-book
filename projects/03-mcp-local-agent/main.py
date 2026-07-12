"""项目 3 入口：`--server` 启动 stdio MCP Server，默认运行本地 Client 演示。"""

import argparse
import asyncio
import json
import os
from pathlib import Path

from ai_agent_book.apps.mcp_local import InProcessTransport, MCPClient, MCPLocalServer, run_stdio


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--server", action="store_true")
    args = parser.parse_args()
    root = Path(os.getenv("MCP_ALLOWED_ROOT", ".")).resolve()
    server = MCPLocalServer(root)
    if args.server:
        await run_stdio(server)
        return
    client = MCPClient(InProcessTransport(server))
    initialized = await client.initialize()
    tools = await client.list_tools()
    system = await client.call_tool("system_info", {})
    print(
        json.dumps(
            {"initialize": initialized, "tools": tools, "system": system},
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    asyncio.run(main())
