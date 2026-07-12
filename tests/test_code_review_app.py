import subprocess
from pathlib import Path

import httpx
import pytest

from ai_agent_book.apps.code_review import (
    CodeReviewService,
    GitHubCommentClient,
    GitRepository,
    HeuristicSemanticReviewer,
)


def _git(repo: Path, *args: str) -> None:
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


def test_git_repository_and_review_report(tmp_path: Path) -> None:
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.test")
    _git(tmp_path, "config", "user.name", "Test")
    source = tmp_path / "app.py"
    source.write_text("def run():\n    return 1\n", encoding="utf-8")
    _git(tmp_path, "add", "app.py")
    _git(tmp_path, "commit", "-m", "base")
    source.write_text(
        (
            "API_KEY = 'sk-live-secret'\n\n"
            "def run(items=[]):\n"
            "    except_value = None\n"
            "    return items\n"
        ),
        encoding="utf-8",
    )

    diff = GitRepository(tmp_path).diff("HEAD")
    report = CodeReviewService(HeuristicSemanticReviewer()).review(diff)

    assert report.summary.total >= 2
    assert report.summary.high >= 1
    assert "hardcoded-secret" in report.markdown
    assert all(finding.file == "app.py" for finding in report.findings)


@pytest.mark.asyncio
async def test_github_comment_is_draft_until_explicitly_approved() -> None:
    calls = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        assert request.url.path.endswith("/issues/7/comments")
        return httpx.Response(201, json={"id": 99, "html_url": "https://example.test/comment/99"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        github = GitHubCommentClient("token", client=client)
        draft = await github.publish("o", "r", 7, "review", approved=False)
        posted = await github.publish("o", "r", 7, "review", approved=True)

    assert draft.status == "approval_required"
    assert posted.status == "posted"
    assert calls == 1
