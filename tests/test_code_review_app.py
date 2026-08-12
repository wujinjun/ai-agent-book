import hashlib
import hmac
import subprocess
from pathlib import Path

import httpx
import pytest

from ai_agent_book.apps.code_review import (
    ApprovalAuthority,
    CodeReviewService,
    DiffPolicy,
    DiffPolicyError,
    GitHubCommentClient,
    GitRepository,
    HeuristicSemanticReviewer,
    WebhookDeliveryStore,
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


def test_diff_policy_rejects_oversized_review_scope() -> None:
    policy = DiffPolicy(max_bytes=20, max_files=1, max_added_lines=1)
    with pytest.raises(DiffPolicyError, match="byte budget"):
        policy.validate("+++ b/a.py\n@@ -0,0 +1,2 @@\n+one\n+two\n")


def test_webhook_signature_and_delivery_deduplication(tmp_path: Path) -> None:
    secret = b"webhook-secret"
    body = b'{"action":"synchronize"}'
    signature = "sha256=" + hmac.new(secret, body, hashlib.sha256).hexdigest()
    store = WebhookDeliveryStore(tmp_path / "deliveries.db", secret)

    assert store.claim("delivery-1", body, signature) is True
    assert store.claim("delivery-1", body, signature) is False
    store.complete("delivery-1", succeeded=True)
    with pytest.raises(PermissionError, match="signature"):
        store.claim("delivery-2", body, "sha256=invalid")
    with pytest.raises(ValueError, match="different payload"):
        store.claim(
            "delivery-1",
            b"different",
            "sha256=" + hmac.new(secret, b"different", hashlib.sha256).hexdigest(),
        )


@pytest.mark.asyncio
async def test_comment_approval_is_bound_to_commit_and_report() -> None:
    posted_body = ""

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal posted_body
        posted_body = str(request.read().decode())
        return httpx.Response(201, json={"html_url": "https://example.test/comment/1"})

    authority = ApprovalAuthority(b"0123456789abcdef")
    approval = authority.issue(
        owner="o",
        repository="r",
        pull_number=7,
        commit_sha="abcdef1",
        markdown="review",
        ttl_seconds=60,
        now=100,
    )
    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        github = GitHubCommentClient("token", client=client)
        posted = await github.publish_with_approval(
            "o",
            "r",
            7,
            "abcdef1",
            "review",
            approval=approval,
            authority=authority,
            now=120,
        )
        with pytest.raises(PermissionError, match="bound"):
            await github.publish_with_approval(
                "o",
                "r",
                7,
                "abcdef2",
                "review",
                approval=approval,
                authority=authority,
                now=120,
            )

    assert posted.status == "posted"
    assert approval.report_sha256 in posted_body
