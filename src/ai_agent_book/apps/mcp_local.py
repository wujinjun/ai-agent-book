"""项目 3：最小 JSON-RPC 2.0 MCP Server、Client 与 stdio 运行循环。

协议版本按 2025-11-25 规范固定；这里只实现教材项目所需的初始化、Tool 与 Resource 子集。
"""

from __future__ import annotations

import asyncio
import json
import platform
import sys
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, Field, ValidationError

from ai_agent_book.project_domains import LocalToolService

PROTOCOL_VERSION = "2025-11-25"


class ReadFileArguments(BaseModel):
    path: str = Field(min_length=1, max_length=500)


class QueryArguments(BaseModel):
    keyword: str = Field(min_length=1, max_length=100)


class MCPError(Exception):
    def __init__(self, code: int, message: str) -> None:
        super().__init__(message)
        self.code = code
        self.message = message


class MCPLocalServer:
    def __init__(self, allowed_root: Path) -> None:
        self.allowed_root = allowed_root.resolve()
        self.tools = LocalToolService(self.allowed_root)

    async def handle(self, request: dict[str, Any]) -> dict[str, Any]:
        request_id = request.get("id")
        try:
            if request.get("jsonrpc") != "2.0" or not isinstance(request.get("method"), str):
                raise MCPError(-32600, "invalid JSON-RPC request")
            result = await self._dispatch(str(request["method"]), request.get("params") or {})
            return {"jsonrpc": "2.0", "id": request_id, "result": result}
        except MCPError as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {"code": exc.code, "message": exc.message},
            }
        except ValidationError as exc:
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "error": {
                    "code": -32602,
                    "message": f"invalid params: {exc.error_count()} issue(s)",
                },
            }

    async def _dispatch(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        if method == "initialize":
            requested = str(params.get("protocolVersion", PROTOCOL_VERSION))
            if requested != PROTOCOL_VERSION:
                raise MCPError(-32602, "unsupported protocol version")
            return {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {"listChanged": False}, "resources": {}},
                "serverInfo": {"name": "ai-agent-book-local", "version": "1.0.0"},
            }
        if method == "tools/list":
            return {"tools": self._tool_definitions()}
        if method == "tools/call":
            return await self._call_tool(str(params.get("name", "")), params.get("arguments") or {})
        if method == "resources/list":
            return {
                "resources": [
                    {
                        "uri": "catalog://chapters",
                        "name": "教材目录",
                        "mimeType": "application/json",
                    }
                ]
            }
        if method == "resources/read":
            if params.get("uri") != "catalog://chapters":
                raise MCPError(-32002, "resource not found")
            catalog = self.tools.query_catalog("")
            return {
                "contents": [
                    {
                        "uri": "catalog://chapters",
                        "mimeType": "application/json",
                        "text": json.dumps(catalog, ensure_ascii=False),
                    }
                ]
            }
        raise MCPError(-32601, "method not found")

    @staticmethod
    def _tool_definitions() -> list[dict[str, Any]]:
        return [
            {
                "name": "read_file",
                "description": "读取允许根目录内的 UTF-8 文本文件",
                "inputSchema": ReadFileArguments.model_json_schema(),
            },
            {
                "name": "system_info",
                "description": "读取非敏感 Python 与操作系统信息",
                "inputSchema": {"type": "object", "properties": {}, "additionalProperties": False},
            },
            {
                "name": "query_catalog",
                "description": "按关键词查询内置教材目录",
                "inputSchema": QueryArguments.model_json_schema(),
            },
        ]

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        try:
            if name == "read_file":
                read_args = ReadFileArguments.model_validate(arguments)
                text = self.tools.read_file(read_args.path)
                return {"content": [{"type": "text", "text": text}], "isError": False}
            if name == "system_info":
                if arguments:
                    raise MCPError(-32602, "system_info takes no arguments")
                text = json.dumps(
                    {"python": platform.python_version(), "system": platform.system()},
                    ensure_ascii=False,
                )
                return {"content": [{"type": "text", "text": text}], "isError": False}
            if name == "query_catalog":
                query_args = QueryArguments.model_validate(arguments)
                text = json.dumps(
                    self.tools.query_catalog(query_args.keyword), ensure_ascii=False
                )
                return {"content": [{"type": "text", "text": text}], "isError": False}
        except (PermissionError, FileNotFoundError, UnicodeDecodeError):
            raise MCPError(-32001, "tool access denied or resource unavailable") from None
        raise MCPError(-32602, "unknown tool")


class MCPTransport(Protocol):
    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]: ...


class InProcessTransport:
    def __init__(self, server: MCPLocalServer) -> None:
        self.server = server
        self.next_id = 1

    async def request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        response = await self.server.handle(
            {"jsonrpc": "2.0", "id": request_id, "method": method, "params": params}
        )
        if error := response.get("error"):
            raise MCPError(int(error["code"]), str(error["message"]))
        return dict(response["result"])


class MCPClient:
    def __init__(self, transport: MCPTransport) -> None:
        self.transport = transport

    async def initialize(self) -> dict[str, Any]:
        return await self.transport.request(
            "initialize",
            {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {},
                "clientInfo": {"name": "ai-agent-book-client", "version": "1.0.0"},
            },
        )

    async def list_tools(self) -> list[dict[str, Any]]:
        result = await self.transport.request("tools/list", {})
        return list(result["tools"])

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
        return await self.transport.request("tools/call", {"name": name, "arguments": arguments})

    async def list_resources(self) -> list[dict[str, Any]]:
        result = await self.transport.request("resources/list", {})
        return list(result["resources"])

    async def read_resource(self, uri: str) -> dict[str, Any]:
        return await self.transport.request("resources/read", {"uri": uri})


async def run_stdio(server: MCPLocalServer) -> None:
    """一行一个 JSON-RPC 消息；协议 stdout 不混入日志。"""

    reader = asyncio.StreamReader()
    protocol = asyncio.StreamReaderProtocol(reader)
    loop = asyncio.get_running_loop()
    await loop.connect_read_pipe(lambda: protocol, sys.stdin)
    while line := await reader.readline():
        try:
            request = json.loads(line)
            response = await server.handle(request)
        except json.JSONDecodeError:
            response = {
                "jsonrpc": "2.0",
                "id": None,
                "error": {"code": -32700, "message": "parse error"},
            }
        sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
        sys.stdout.flush()
