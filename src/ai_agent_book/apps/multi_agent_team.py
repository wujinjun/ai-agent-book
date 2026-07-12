"""项目 9：五角色、中心化共享状态、预算和硬终止的开发团队。"""

from __future__ import annotations

import ast
from typing import Literal, Protocol

from pydantic import BaseModel, Field

RoleName = Literal["product", "planner", "coder", "tester", "reviewer"]


class TeamMessage(BaseModel):
    role: RoleName
    content: str
    state_version: int


class SharedState(BaseModel):
    version: int = 0
    requirement: str = ""
    acceptance_criteria: list[str] = Field(default_factory=list)
    plan: list[str] = Field(default_factory=list)
    artifact: str = ""
    tests_passed: bool = False
    review_approved: bool = False


class RoleOutput(BaseModel):
    content: str
    updates: dict[str, object]


class RoleAgent(Protocol):
    name: RoleName

    def act(self, state: SharedState) -> RoleOutput: ...


class ProductAgent:
    name: RoleName = "product"

    def act(self, state: SharedState) -> RoleOutput:
        criteria = [
            "健康检查函数返回明确状态",
            "代码可以被 Python 解析",
            "测试通过且 Reviewer 批准",
        ]
        return RoleOutput(
            content="已把需求压缩为三个可验证验收条件。",
            updates={"acceptance_criteria": criteria},
        )


class PlannerAgent:
    name: RoleName = "planner"

    def act(self, state: SharedState) -> RoleOutput:
        plan = ["实现 health 函数", "执行语法和行为检查", "按验收条件 Review"]
        return RoleOutput(content="计划只包含实现、测试和评审三个步骤。", updates={"plan": plan})


class CoderAgent:
    name: RoleName = "coder"

    def act(self, state: SharedState) -> RoleOutput:
        artifact = (
            "from typing import Literal\n\n"
            "def health() -> dict[str, Literal['ok']]:\n"
            "    return {'status': 'ok'}\n"
        )
        return RoleOutput(content="生成最小健康检查实现。", updates={"artifact": artifact})


class TesterAgent:
    name: RoleName = "tester"

    def act(self, state: SharedState) -> RoleOutput:
        passed = False
        try:
            tree = ast.parse(state.artifact)
            functions = [node for node in tree.body if isinstance(node, ast.FunctionDef)]
            has_health = any(node.name == "health" for node in functions)
            passed = has_health and "'status': 'ok'" in state.artifact
        except SyntaxError:
            passed = False
        return RoleOutput(
            content="语法与健康状态契约测试通过。" if passed else "测试失败。",
            updates={"tests_passed": passed},
        )


class ReviewerAgent:
    name: RoleName = "reviewer"

    def act(self, state: SharedState) -> RoleOutput:
        approved = state.tests_passed and bool(state.acceptance_criteria) and bool(state.artifact)
        return RoleOutput(
            content="验收条件满足，批准终止。" if approved else "证据不足，拒绝终止。",
            updates={"review_approved": approved},
        )


class TeamResult(BaseModel):
    status: Literal["completed", "failed", "stopped"]
    termination: str
    messages: list[TeamMessage]
    shared_state: SharedState
    estimated_tokens: int


class DevelopmentTeam:
    """所有角色只通过 Coordinator 更新状态，不允许角色间自由对话。"""

    def __init__(self, *, max_messages: int = 5, token_budget: int = 2_000) -> None:
        self.max_messages = max_messages
        self.token_budget = token_budget
        self.roles: list[RoleAgent] = [
            ProductAgent(),
            PlannerAgent(),
            CoderAgent(),
            TesterAgent(),
            ReviewerAgent(),
        ]

    def run(self, requirement: str) -> TeamResult:
        state = SharedState(requirement=requirement)
        messages: list[TeamMessage] = []
        estimated_tokens = 0
        for role in self.roles:
            if len(messages) >= self.max_messages:
                return self._result(
                    "stopped", "message_budget_exceeded", messages, state, estimated_tokens
                )
            output = role.act(state)
            next_tokens = max(1, len(output.content) // 2)
            if estimated_tokens + next_tokens > self.token_budget:
                return self._result(
                    "stopped", "token_budget_exceeded", messages, state, estimated_tokens
                )
            state = state.model_copy(update={**output.updates, "version": state.version + 1})
            estimated_tokens += next_tokens
            messages.append(
                TeamMessage(
                    role=role.name,
                    content=output.content,
                    state_version=state.version,
                )
            )
        if state.tests_passed and state.review_approved:
            return self._result(
                "completed", "tests_passed_and_reviewed", messages, state, estimated_tokens
            )
        return self._result("failed", "review_rejected", messages, state, estimated_tokens)

    @staticmethod
    def _result(
        status: Literal["completed", "failed", "stopped"],
        termination: str,
        messages: list[TeamMessage],
        state: SharedState,
        estimated_tokens: int,
    ) -> TeamResult:
        return TeamResult(
            status=status,
            termination=termination,
            messages=messages,
            shared_state=state,
            estimated_tokens=estimated_tokens,
        )
