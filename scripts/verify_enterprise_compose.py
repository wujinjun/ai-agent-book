"""启动 Compose 后执行项目 10 的 PostgreSQL/Redis/API 纵向验收。"""

from __future__ import annotations

import argparse
import time

import httpx


def wait_for_health(client: httpx.Client, attempts: int = 30) -> None:
    for _ in range(attempts):
        try:
            if client.get("/health").json() == {"status": "ok"}:
                return
        except httpx.HTTPError:
            pass
        time.sleep(1)
    raise RuntimeError("enterprise API did not become healthy")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    headers = {"X-Tenant-ID": "demo", "X-User-ID": "admin"}
    with httpx.Client(base_url=args.base_url, timeout=5, trust_env=False) as client:
        wait_for_health(client)
        agent_response = client.post(
            "/admin/agents", headers=headers, json={"name": "compose-agent", "kind": "rag"}
        )
        agent_response.raise_for_status()
        tool_response = client.post(
            "/admin/tools",
            headers=headers,
            json={"name": "compose-mcp", "kind": "mcp", "endpoint": "stdio://local"},
        )
        tool_response.raise_for_status()
        session_response = client.post(
            "/sessions",
            headers=headers,
            json={"agent_id": agent_response.json()["agent_id"]},
        )
        session_response.raise_for_status()
        run_response = client.post(
            "/runs",
            headers=headers,
            json={"session_id": session_response.json()["session_id"], "prompt": "compose test"},
        )
        run_response.raise_for_status()
        processed = client.post("/worker/process-one", headers=headers)
        processed.raise_for_status()
        assert processed.json()["run_id"] == run_response.json()["run_id"]
        assert processed.json()["status"] == "succeeded"
        listed = client.get("/admin/runs", headers=headers)
        listed.raise_for_status()
        assert any(item["run_id"] == run_response.json()["run_id"] for item in listed.json())
    print("enterprise compose verification passed")


if __name__ == "__main__":
    main()
