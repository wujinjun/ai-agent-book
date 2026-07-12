"""项目 5：Git Diff、确定性规则、语义审查接口、报告与可审批 PR 评论。"""

from __future__ import annotations

import re
import subprocess
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


class SemanticReviewer(Protocol):
    def review(self, lines: list[ChangedLine]) -> list[ReviewFinding]: ...


class GitRepository:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
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
