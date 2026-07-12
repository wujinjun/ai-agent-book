from pathlib import Path

import pytest

from ai_agent_book.apps.enterprise_platform import EnterprisePlatform


def test_cross_tenant_access_is_rejected(tmp_path: Path) -> None:
    platform = EnterprisePlatform(tmp_path / "platform.db")
    platform.create_tenant("a", "A")
    platform.create_tenant("b", "B")
    platform.create_user("a", "admin", role="admin")
    agent = platform.register_agent("a", "admin", "assistant", "assistant")
    session = platform.create_session("a", "admin", agent.agent_id)
    run = platform.submit_run("a", "admin", session.session_id, "task")
    with pytest.raises(PermissionError):
        platform.get_run("b", run.run_id)
