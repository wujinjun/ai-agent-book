# 项目8：LangGraph 研究工作流 Agent

## 需求、架构与数据流
技术选型：Python 3.12、Pydantic 2、FastAPI、pytest 与 Docker；在线供应商通过适配器接入。

项目用真实 LangGraph 状态图组织规划、搜索、读取、评审、Checkpoint 与人工中断，恢复依赖稳定线程标识和证据状态。

```mermaid
%% id: project8-langgraph-research-state
%% title: LangGraph 研究工作流状态图
%% alt: 研究任务从规划搜索读取评审到写作，证据不足循环检索并在通过后结束
stateDiagram-v2
    [*] --> Plan
    Plan --> Search
    Search --> Read
    Read --> Review
    Review --> Search: evidence insufficient
    Review --> Write: approved
    Write --> [*]
```

实现规划、搜索、读取、证据表、重试、Reviewer、Checkpoint 和人工中断。 离线模式使用确定性 Mock，使无 API Key 也能运行和测试；在线服务通过适配器替换，领域结果保持稳定 Schema。

```mermaid
%% id: project8-checkpoint-interrupt-sequence
%% title: 研究图 Checkpoint 与人工恢复时序
%% alt: LangGraph 保存研究状态后发送审批中断，人工决定通过相同 thread_id 恢复并生成最终报告
sequenceDiagram
    participant G as Research Graph
    participant C as Checkpointer
    participant H as Human
    G->>C: save plan evidence review state
    G-->>H: interrupt approval payload
    H->>G: Command resume decision + same thread_id
    G->>C: load latest checkpoint
    G->>G: validate decision and continue
    G-->>H: report or cancelled result
```

恢复依赖稳定 `thread_id` 和可序列化 State。人工决定、证据版本和剩余预算都需在继续前重新校验。

```mermaid
%% id: project8-research-failure-recovery
%% title: 研究工作流失败恢复决策
%% alt: 搜索读取 Reviewer 失败按错误类型进入有限重试替换来源补充证据人工介入或终止并保留已验证产物
flowchart TD
    Failure[节点失败] --> Kind{失败位置}
    Kind -->|搜索暂时故障| Retry[RetryPolicy 预算内重试]
    Kind -->|来源不可读| Alternate[替换来源并保留其他证据]
    Kind -->|证据不足| More[Reviewer 返回具体缺口]
    Kind -->|注入或权限| Stop[停止并记录安全错误]
    Retry --> Search[继续 Search]
    Alternate --> Search
    More --> Limit{研究轮数剩余}
    Limit -->|是| Search
    Limit -->|否| Fail[失败或人工补充]
```

重试和重规划不改变系统目标或来源 allowlist；已经验证的 Evidence 不因单个下游失败而全部丢弃。

`输入 → LangGraph Plan → 带 RetryPolicy 的 Search → Read → Reviewer 条件边 → interrupt → Command(resume) → Report`。独立实现位于 `src/ai_agent_book/apps/langgraph_research.py`，固定使用并实测 `langgraph==1.2.9`，直接测试位于 `tests/test_langgraph_research_app.py`。

## 运行、测试与部署
```bash
PYTHONPATH=src .venv/bin/python projects/08-research-workflow/main.py
PYTHONPATH=src .venv/bin/python -m pytest tests/test_langgraph_research_app.py -q
docker build -f projects/08-research-workflow/Dockerfile -t ai-agent-book/project-8 .
docker run --rm ai-agent-book/project-8
```

配置只从环境读取，默认 `APP_MODE=offline`。常见问题：外部搜索内容不可信，重规划不能改变系统目标。扩展方向：按当前 LangGraph 版本实现持久图和恢复。

## 实现说明与验收

`build_research_graph` 使用真实 `StateGraph`、`InMemorySaver`、`RetryPolicy`、条件边、`interrupt` 和 `Command(resume=...)`。搜索瞬时失败会按节点策略重试；Reviewer 要求至少两个独立来源，证据不足在轮次上限后失败；通过后暂停等待人工批准。测试检查实际 Checkpoint 快照、待恢复节点、重试次数与恢复报告。生产环境应把内存 Checkpointer 替换为数据库实现。

## 目录、配置与扩展

```text
08-research-workflow/  README.md  main.py  .env.example  Dockerfile  tests/
src/ai_agent_book/apps/langgraph_research.py  # LangGraph 1.2.9 图
```

依赖固定 `langgraph==1.2.9`。常见问题是恢复时更换 `thread_id`，这会创建新线程而非恢复旧状态。扩展方向包括数据库 Checkpointer、真实搜索/读取 Provider、引用校验、流式事件和 Checkpoint Schema 迁移测试。
