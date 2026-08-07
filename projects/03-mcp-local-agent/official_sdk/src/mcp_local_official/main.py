"""Run the official SDK server over stdio or Streamable HTTP."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .server import create_server


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--transport", choices=("stdio", "streamable-http"), default="stdio")
    args = parser.parse_args()
    root = Path(os.getenv("MCP_ALLOWED_ROOT", "."))
    server = create_server(root)
    if args.transport == "stdio":
        server.run("stdio")
        return
    server.run(
        "streamable-http",
        host=os.getenv("MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("MCP_PORT", "8000")),
        stateless_http=True,
        json_response=True,
    )


if __name__ == "__main__":
    main()

