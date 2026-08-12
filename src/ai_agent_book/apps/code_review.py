"""项目 5：Git Diff、确定性规则、语义审查接口、报告与可审批 PR 评论。"""

from __future__ import annotations

import hashlib
import hmac
import json
import re
import sqlite3
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Literal, Protocol

import httpx
from pydantic import BaseModel, Field


class ChangedLine(BaseModel):
    file: str
    line: int = Field(ge=1)
    content: str


class ReviewFinding(BaseModel):
    rule: str
    risk: Literal["low", "medium", "high"]
    file: str
    line: int
    message: str
    suggestion: str


class ReviewSummary(BaseModel):
    total: int
    low: int
    medium: int
    high: int


class ReviewReport(BaseModel):
    summary: ReviewSummary
    findings: list[ReviewFinding]
    markdown: str


class PublishResult(BaseModel):
    status: Literal["approval_required", "posted"]
    url: str | None = None


class DiffPolicyError(ValueError):
    """Diff 超出审查沙箱允许范围。"""


@dataclass(frozen=True, slots=True)
class DiffPolicy:
    max_bytes: int = 1_000_000
    max_files: int = 200
    max_added_lines: int = 20_000

    def validate(self, diff: str) -> None:
        encoded = diff.encode("utf-8")
        files = {
            line.removeprefix("+++ b/") for line in diff.splitlines() if line.startswith("+++ b/")
        }
        added = sum(
            line.startswith("+") and not line.startswith("+++") for line in diff.splitlines()
        )
        if len(encoded) > self.max_bytes:
            raise DiffPolicyError("diff exceeds byte budget")
        if len(files) > self.max_files:
            raise DiffPolicyError("diff exceeds file budget")
        if added > self.max_added_lines:
            raise DiffPolicyError("diff exceeds added-line budget")


class CommentApproval(BaseModel):
    owner: str
    repository: str
    pull_number: int = Field(ge=1)
    commit_sha: str = Field(pattern=r"^[0-9a-f]{7,64}$")
    report_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expires_at: int
    signature: str


class ApprovalAuthority:
    """把人工批准绑定到仓库、PR、提交和报告内容。"""

    def __init__(self, secret: bytes) -> None:
        if len(secret) < 16:
            raise ValueError("approval secret must contain at least 16 bytes")
        self.secret = secret

    @staticmethod
    def _payload(
        owner: str,
        repository: str,
        pull_number: int,
        commit_sha: str,
        report_sha256: str,
        expires_at: int,
    ) -> bytes:
        return json.dumps(
            {
                "owner": owner,
                "repository": repository,
                "pull_number": pull_number,
                "commit_sha": commit_sha,
                "report_sha256": report_sha256,
                "expires_at": expires_at,
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode()

    def issue(
        self,
        *,
        owner: str,
        repository: str,
        pull_number: int,
        commit_sha: str,
        markdown: str,
        ttl_seconds: int = 600,
        now: int | None = None,
    ) -> CommentApproval:
        issued_at = int(time.time()) if now is None else now
        report_sha256 = hashlib.sha256(markdown.encode()).hexdigest()
        expires_at = issued_at + ttl_seconds
        payload = self._payload(
            owner, repository, pull_number, commit_sha, report_sha256, expires_at
        )
        signature = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        return CommentApproval(
            owner=owner,
            repository=repository,
            pull_number=pull_number,
            commit_sha=commit_sha,
            report_sha256=report_sha256,
            expires_at=expires_at,
            signature=signature,
        )

    def verify(
        self,
        approval: CommentApproval,
        *,
        owner: str,
        repository: str,
        pull_number: int,
        commit_sha: str,
        markdown: str,
        now: int | None = None,
    ) -> None:
        current = int(time.time()) if now is None else now
        expected_report = hashlib.sha256(markdown.encode()).hexdigest()
        expected_fields = (
            approval.owner == owner
            and approval.repository == repository
            and approval.pull_number == pull_number
            and approval.commit_sha == commit_sha
            and approval.report_sha256 == expected_report
        )
        payload = self._payload(
            approval.owner,
            approval.repository,
            approval.pull_number,
            approval.commit_sha,
            approval.report_sha256,
            approval.expires_at,
        )
        expected_signature = hmac.new(self.secret, payload, hashlib.sha256).hexdigest()
        if not expected_fields or not hmac.compare_digest(approval.signature, expected_signature):
            raise PermissionError("approval is not bound to this review action")
        if approval.expires_at < current:
            raise PermissionError("approval has expired")


class WebhookDeliveryStore:
    """验证 GitHub Webhook，并以 delivery ID 防止重复执行。"""

    def __init__(self, path: Path, webhook_secret: bytes) -> None:
        self.path = path
        self.webhook_secret = webhook_secret
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with sqlite3.connect(self.path) as connection:
            connection.execute(
                """CREATE TABLE IF NOT EXISTS webhook_delivery (
                delivery_id TEXT PRIMARY KEY,
                payload_sha256 TEXT NOT NULL,
                status TEXT NOT NULL,
                updated_at INTEGER NOT NULL
                )"""
            )

    def claim(self, delivery_id: str, body: bytes, signature: str) -> bool:
        if not re.fullmatch(r"[A-Za-z0-9-]{1,128}", delivery_id):
            raise ValueError("invalid delivery id")
        expected = "sha256=" + hmac.new(self.webhook_secret, body, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(signature, expected):
            raise PermissionError("invalid webhook signature")
        digest = hashlib.sha256(body).hexdigest()
        with sqlite3.connect(self.path) as connection:
            row = connection.execute(
                "SELECT payload_sha256 FROM webhook_delivery WHERE delivery_id = ?",
                (delivery_id,),
            ).fetchone()
            if row:
                if row[0] != digest:
                    raise ValueError("delivery id reused with different payload")
                return False
            connection.execute(
                "INSERT INTO webhook_delivery VALUES (?, ?, 'claimed', ?)",
                (delivery_id, digest, int(time.time())),
            )
        return True

    def complete(self, delivery_id: str, *, succeeded: bool) -> None:
        with sqlite3.connect(self.path) as connection:
            cursor = connection.execute(
                "UPDATE webhook_delivery SET status = ?, updated_at = ? WHERE delivery_id = ?",
                ("completed" if succeeded else "failed", int(time.time()), delivery_id),
            )
            if cursor.rowcount != 1:
                raise KeyError(delivery_id)


class SemanticReviewer(Protocol):
    def review(self, lines: list[ChangedLine]) -> list[ReviewFinding]: ...


class GitRepository:
    def __init__(self, path: Path, *, policy: DiffPolicy | None = None) -> None:
        self.path = path.resolve()
        self.policy = policy or DiffPolicy()
        if not (self.path / ".git").exists():
            raise ValueError("not a Git repository")

    def diff(self, base: str, head: str | None = None) -> str:
        ref_pattern = re.compile(r"^[A-Za-z0-9._/@{}~^+-]+$")
        if not ref_pattern.fullmatch(base) or (head and not ref_pattern.fullmatch(head)):
            raise ValueError("invalid Git ref")
        refs = [base] if head is None else [base, head]
        completed = subprocess.run(
            ["git", "diff", "--unified=3", *refs, "--"],
            cwd=self.path,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.policy.validate(completed.stdout)
        return completed.stdout


def parse_added_lines(diff: str) -> list[ChangedLine]:
    current_file = "unknown"
    new_line = 0
    lines: list[ChangedLine] = []
    for raw in diff.splitlines():
        if raw.startswith("+++ b/"):
            current_file = raw.removeprefix("+++ b/")
            continue
        if raw.startswith("@@"):
            match = re.search(r"\+(\d+)", raw)
            if match:
                new_line = int(match.group(1))
            continue
        if raw.startswith("+") and not raw.startswith("+++"):
            lines.append(ChangedLine(file=current_file, line=max(1, new_line), content=raw[1:]))
            new_line += 1
        elif raw.startswith(" "):
            new_line += 1
    return lines


def run_static_rules(lines: list[ChangedLine]) -> list[ReviewFinding]:
    findings: list[ReviewFinding] = []
    patterns = [
        (
            "hardcoded-secret",
            "high",
            re.compile(r"(?:API_KEY|SECRET|TOKEN|PASSWORD)\s*=\s*['\"][^'\"]+"),
            "疑似硬编码凭证",
            "改为从 Secret 管理器或环境变量读取，并轮换已暴露凭证。",
        ),
        (
            "mutable-default",
            "medium",
            re.compile(r"^\s*def\s+\w+\([^)]*=\s*(?:\[|\{)"),
            "函数使用可变默认参数",
            "默认值改为 None，并在函数内部创建容器。",
        ),
        (
            "broad-exception",
            "medium",
            re.compile(r"^\s*except\s+(?:Exception|BaseException)"),
            "捕获异常范围过宽",
            "捕获可恢复的具体异常并保留上下文日志。",
        ),
        (
            "dynamic-eval",
            "high",
            re.compile(r"\b(?:eval|exec)\s*\("),
            "动态执行输入可能导致代码执行",
            "使用显式解析器、白名单或沙箱。",
        ),
    ]
    for line in lines:
        for rule, risk, pattern, message, suggestion in patterns:
            if pattern.search(line.content):
                findings.append(
                    ReviewFinding(
                        rule=rule,
                        risk=risk,  # type: ignore[arg-type]
                        file=line.file,
                        line=line.line,
                        message=message,
                        suggestion=suggestion,
                    )
                )
    return findings


class HeuristicSemanticReviewer:
    """无密钥语义替身；真实 LLM Reviewer 实现相同结构化接口。"""

    def review(self, lines: list[ChangedLine]) -> list[ReviewFinding]:
        findings: list[ReviewFinding] = []
        for line in lines:
            if "TODO" in line.content and "security" in line.content.lower():
                findings.append(
                    ReviewFinding(
                        rule="unresolved-security-todo",
                        risk="medium",
                        file=line.file,
                        line=line.line,
                        message="安全相关 TODO 尚未解决",
                        suggestion="在合并前关联问题单并明确缓解措施。",
                    )
                )
        return findings


class CodeReviewService:
    def __init__(self, semantic_reviewer: SemanticReviewer) -> None:
        self.semantic_reviewer = semantic_reviewer

    def review(self, diff: str) -> ReviewReport:
        lines = parse_added_lines(diff)
        findings = [*run_static_rules(lines), *self.semantic_reviewer.review(lines)]
        unique = {(item.rule, item.file, item.line): item for item in findings}
        ordered = sorted(
            unique.values(),
            key=lambda item: ({"high": 0, "medium": 1, "low": 2}[item.risk], item.file, item.line),
        )
        summary = ReviewSummary(
            total=len(ordered),
            low=sum(item.risk == "low" for item in ordered),
            medium=sum(item.risk == "medium" for item in ordered),
            high=sum(item.risk == "high" for item in ordered),
        )
        markdown_lines = [
            "# Code Review 报告",
            "",
            (
                f"共 {summary.total} 项：high={summary.high}，"
                f"medium={summary.medium}，low={summary.low}。"
            ),
        ]
        for item in ordered:
            markdown_lines.extend(
                [
                    "",
                    f"## [{item.risk}] {item.rule}",
                    f"- 位置：`{item.file}:{item.line}`",
                    f"- 问题：{item.message}",
                    f"- 建议：{item.suggestion}",
                ]
            )
        return ReviewReport(
            summary=summary,
            findings=ordered,
            markdown="\n".join(markdown_lines),
        )


class GitHubCommentClient:
    def __init__(self, token: str, *, client: httpx.AsyncClient | None = None) -> None:
        self.token = token
        self.client = client

    async def publish(
        self,
        owner: str,
        repository: str,
        pull_number: int,
        markdown: str,
        *,
        approved: bool,
    ) -> PublishResult:
        if not approved:
            return PublishResult(status="approval_required")
        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=10)
        try:
            response = await client.post(
                f"https://api.github.com/repos/{owner}/{repository}/issues/{pull_number}/comments",
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                json={"body": markdown},
            )
            response.raise_for_status()
            return PublishResult(status="posted", url=str(response.json().get("html_url", "")))
        finally:
            if owns_client:
                await client.aclose()

    async def publish_with_approval(
        self,
        owner: str,
        repository: str,
        pull_number: int,
        commit_sha: str,
        markdown: str,
        *,
        approval: CommentApproval,
        authority: ApprovalAuthority,
        now: int | None = None,
    ) -> PublishResult:
        authority.verify(
            approval,
            owner=owner,
            repository=repository,
            pull_number=pull_number,
            commit_sha=commit_sha,
            markdown=markdown,
            now=now,
        )
        marker = f"<!-- ai-agent-book-review:{approval.report_sha256} -->"
        return await self.publish(
            owner,
            repository,
            pull_number,
            f"{marker}\n{markdown}",
            approved=True,
        )
