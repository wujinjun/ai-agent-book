"""项目 10 CLI：创建多租户平台数据并处理一个队列任务。"""

import json
import os
from pathlib import Path

from ai_agent_book.apps.enterprise_platform import EnterprisePlatform

if __name__ == "__main__":
    database = Path(os.getenv("DATABASE_PATH", ".data/enterprise-platform.db"))
    if database.exists():
        database.unlink()
    platform = EnterprisePlatform(database)
    platform.create_tenant("demo", "Demo Tenant")
    platform.create_user("demo", "admin", role="admin")
    platform.create_user("demo", "member", role="member")
    agent = platform.register_agent("demo", "admin", "knowledge", "rag")
    platform.register_tool("demo", "admin", "local-mcp", kind="mcp", endpoint="stdio://local")
    session = platform.create_session("demo", "member", agent.agent_id)
    platform.add_document("demo", "policy", "Agent 平台使用租户隔离和最小权限。")
    platform.submit_run("demo", "member", session.session_id, "平台如何隔离数据？")
    result = platform.process_next()
    print(json.dumps(result.model_dump() if result else None, ensure_ascii=False, indent=2))
