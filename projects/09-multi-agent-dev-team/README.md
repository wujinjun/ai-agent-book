# 项目9：Multi-Agent 软件开发团队

## 需求、架构与数据流
技术选型：Python 3.12、Pydantic 2、FastAPI、pytest 与 Docker；在线供应商通过适配器接入。

项目不允许五个角色自由群聊，而是由 Coordinator 驱动有序职责，并用版本化共享状态与硬预算约束协作。

```mermaid
%% id: project9-shared-state-team-architecture
%% title: Multi-Agent 开发团队共享状态架构
%% alt: Product Planner Coder Tester Reviewer 通过版本化共享状态协作，只有测试与评审同时通过才终止
flowchart LR
    Product --> State[("Versioned Shared State")]
    Planner --> State
    Coder --> Sandbox --> State
    Tester --> State
    Reviewer --> Gate{"tests passed AND reviewed?"}
    State --> Gate -->|yes| Stop
```

实现 Product、Planner、Coder、Reviewer、Tester 五角色的结构化协作。 离线模式使用确定性 Mock，使无 API Key 也能运行和测试；在线服务通过适配器替换，领域结果保持稳定 Schema。

```mermaid
%% id: project9-role-artifact-sequence
%% title: 软件团队角色与 Artifact 时序
%% alt: Product 定义验收，Planner 形成计划，Coder 交付 Artifact，Tester 和 Reviewer 分别提交结构化结果给 Coordinator
sequenceDiagram
    participant P as Product
    participant L as Planner
    participant C as Coder
    participant T as Tester
    participant R as Reviewer
    participant S as Shared State
    P->>S: acceptance criteria
    L->>S: executable plan
    C->>S: artifact version + evidence
    T->>S: test result
    R->>S: review decision
    S->>S: coordinator validates terminal gate
```

角色之间禁止点对点自由闲聊，所有事实和产物通过带版本的共享状态提交，Coordinator 负责 Schema、顺序和所有权校验。

```mermaid
%% id: project9-cost-termination-gate
%% title: Multi-Agent 成本与硬终止门禁
%% alt: 每次角色调用检查消息 Token 和轮数预算，重复或无新增 Artifact 时停止，测试与评审均通过才成功
flowchart TD
    Next[候选角色调用] --> Budget{消息 Token 轮数预算}
    Budget -->|耗尽| Stop[budget_exceeded]
    Budget -->|剩余| Progress{产生新 Artifact 或验证证据}
    Progress -->|否| Stop
    Progress -->|是| Gate{tests_passed 且 review_approved}
    Gate -->|是| Success[成功终止]
    Gate -->|否| Next
```

角色数量增加必须与单 Agent 基线比较质量、费用和尾延迟；无独立信息或权限边界的角色应删除。

`需求 → Product 验收条件 → Planner 计划 → Coder Artifact → Tester → Reviewer → 硬终止`。所有角色只能通过版本化共享状态通信，独立实现位于 `src/ai_agent_book/apps/multi_agent_team.py`，直接测试位于 `tests/test_multi_agent_team_app.py`。

## 运行、测试与部署
```bash
PYTHONPATH=src .venv/bin/python projects/09-multi-agent-dev-team/main.py
PYTHONPATH=src .venv/bin/python -m pytest tests/test_multi_agent_team_app.py -q
docker build -f projects/09-multi-agent-dev-team/Dockerfile -t ai-agent-book/project-9 .
docker run --rm ai-agent-book/project-9
```

配置只从环境读取，默认 `APP_MODE=offline`。常见问题：角色越多不一定更好，消息与费用均有硬上限。扩展方向：加入共享状态版本、Sandbox 和单 Agent 基线对照。

## 实现说明与验收

`DevelopmentTeam` 包含 Product、Planner、Coder、Tester、Reviewer 五个独立角色，但禁止点对点自由闲聊；Coordinator 校验输出并将共享状态版本递增。消息数与估算 Token 都有硬预算，只有 `tests_passed` 与 `review_approved` 同时成立才成功终止。测试验证角色次序、版本、成本上限和预算提前停止，避免无效对话与死循环。

## 目录、配置与扩展

```text
09-multi-agent-dev-team/  README.md  main.py  .env.example  Dockerfile  tests/
src/ai_agent_book/apps/multi_agent_team.py  # 五角色与 Coordinator
```

默认 Artifact 在内存中生成并由 AST 检查，不执行不可信模型代码。常见问题是不断增加角色却没有独立信息或权限边界。扩展方向包括真正的临时 Git Worktree、容器 Sandbox、补丁应用、pytest Runner，以及与单 Agent 基线的质量/成本对照。
