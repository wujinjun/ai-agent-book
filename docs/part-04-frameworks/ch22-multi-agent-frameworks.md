# 第22章：CrewAI、AutoGen 与其他 Multi-Agent 框架

![任务先判断是否需要协作，再比较单 Agent、确定性工作流、Supervisor 和角色团队，协作通过类型化状态交换工件与证据，并受回合、成本、延迟、权限、死锁和终止门约束，最后与单 Agent 基线比较](../assets/infographics/png/multi-agent-framework-decision-infographic-2x.png)

*图 22-A　Multi-Agent 框架的必要性与模式选择。*

多 Agent 是一种分工与隔离方案，不是默认升级路径。只有任务成功率或独立审查质量相对单 Agent 基线有可测收益，且收益覆盖额外成本和协调风险时，角色协作才值得保留。

最后核对日期：2026-08-07；CrewAI 1.15.12、AutoGen AgentChat 0.7.5 与 Semantic Kernel 1.44.1 已在独立 Python 3.12 环境安装实测。

## 导读、目标与前置知识
本章比较 CrewAI、AutoGen、Semantic Kernel 等角色协作与任务编排方案，重点是通信、成本、调试和“不使用 Multi-Agent”的判断。

学习目标是为真实任务选择或拒绝 Multi-Agent 框架。前置知识为第9、10、20章。

## 核心原理与架构

Multi-Agent 框架的关键不是角色数量，而是监督者、专业 Worker 与类型化共享状态之间的控制关系。

```mermaid
%% id: multi-agent-supervisor-shared-state
%% title: Supervisor、Worker 与共享状态架构
%% alt: Supervisor 向研究编码评审 Worker 分派任务，各 Worker 仅通过类型化共享状态提交产物
flowchart TB
    Supervisor --> Researcher
    Supervisor --> Coder
    Supervisor --> Reviewer
    Researcher --> Shared["Typed Shared State"]
    Coder --> Shared
    Reviewer --> Shared
```

角色只有在能力、权限、上下文或验收职责确实不同才有价值。CrewAI 常用角色/任务组织，AutoGen 强调可对话 Agent，Semantic Kernel 提供企业应用编排与插件抽象；实际能力随版本变化。

```mermaid
%% id: multi-agent-framework-pattern-selection
%% title: Multi-Agent 框架模式选择
%% alt: 根据流程确定性消息复杂度和企业技术栈选择 CrewAI Flow Crew AutoGen AgentChat Core 或 Semantic Kernel
flowchart TD
    Need[多 Agent 协作需求] --> Flow{流程与状态可明确枚举}
    Flow -->|是| CrewFlow[CrewAI Flow 或图工作流]
    Flow -->|否| Message{需要复杂消息与事件运行时}
    Message -->|快速对话原型| AgentChat[AutoGen AgentChat]
    Message -->|分布式事件系统| Core[AutoGen Core]
    Message -->|否| Role[CrewAI Crew]
    Need --> DotNet{Microsoft 或 .NET 企业栈}
    DotNet -->|是| SK[Semantic Kernel 候选]
```

框架定位随版本变化，最终选择还需用同一任务比较成功率、成本、终止和调试能力。

```mermaid
%% id: multi-agent-cost-termination-control
%% title: Multi-Agent 成本与终止控制
%% alt: 每个角色调用都经过任务去重证据增量和预算检查，无新增价值或达到上限时由 Runtime 强制终止
flowchart LR
    Message[候选 Agent 消息或调用] --> Duplicate{任务或证据重复}
    Duplicate -->|是| Stop[停止无效对话]
    Duplicate -->|否| Increment{产生可验证增量}
    Increment -->|否| Stop
    Increment -->|是| Budget{Token 时间轮数预算}
    Budget -->|不足| Stop
    Budget -->|足够| Execute[执行并写共享状态]
    Execute --> Message
```

终止由 Runtime 根据完成、预算、重复与无新增证据判定，不能依赖角色在自然语言中自觉结束。

## 最小与完整工程
先以单 Agent + 两工具建立基线，再实现 Supervisor/Worker，比较成功率、Token、延迟和重复消息。共享状态使用 Schema，消息只携带任务所需内容，终止由运行时而非角色自觉决定。

## 误区、调试、实践与安全
更多角色不等于更聪明；“辩论”可能放大共同错误；自然语言聊天难以保证状态一致。调试通信图、重复调用和终止原因。不同 Agent 使用最小权限，Reviewer 不持有执行密钥。

## 总结、练习、面试与阅读

### Multi-Agent 框架解决的问题

框架主要提供 Agent/Role 定义、任务分配、消息协议、共享状态、终止、工具、模型客户端和可观测。它们不能证明角色之间存在独立知识，也不能自动避免死循环。多 Agent 只有在上下文隔离、权限隔离、并行专业任务或独立 Reviewer 带来可测收益时成立。

### CrewAI：Crews 与 Flows

官方把 Crews 定位为角色与任务协作，把 Flows 定位为更明确的事件驱动控制、State、条件与恢复。开放研究可用 Crew，审核/集成流程更适合 Flow，常见生产形态是 Flow 提供确定性骨架，在少数节点调用 Crew。

Agent 配置角色、目标和 tools，Task 定义目标与 expected output，Process 决定顺序/层级，Crew 组合它们。角色描述只是 Prompt，不是权限；Tool allowlist 仍由运行时。Flow State 应类型化，不依赖角色对话作为事实源。

```mermaid
%% id: crewai-flow-crew-boundary
%% title: CrewAI Flow 与 Crew 的组合边界
%% alt: 确定性 Flow 在受控节点调用探索型 Research Crew，并校验其 Artifact 后推进下一状态
flowchart LR
    Event --> Flow["CrewAI Flow: deterministic state"]
    Flow --> ResearchCrew["Crew: exploratory subtask"]
    ResearchCrew --> Artifact
    Artifact --> Validate --> Next
```

生产形态通常由 Flow 持有状态和终止权，只把开放探索子任务交给 Crew，返回的 Artifact 仍需确定性校验。

### AutoGen：Core 与 AgentChat

当前官方文档区分 AgentChat 与 Core。AgentChat 提供 AssistantAgent、Teams、messages、state 与 termination，适合快速构建对话式单/多 Agent；Core 是事件驱动运行时，适合更可扩展的消息和分布式系统。Extensions 提供模型客户端、MCP Workbench 与 Docker code executor 等。

AgentChat 的 Agent 有状态，`run()` 会更新内部 history；调用方应传新任务而非每次重复完整历史。Team 必须配置 termination condition，保存/恢复 State 时绑定会话和租户。执行模型生成代码使用隔离容器、资源限制和无秘密环境。

```python
# 当前 AutoGen AgentChat 的结构示例；模型客户端配置按部署环境提供。
from autogen_agentchat.agents import AssistantAgent

agent = AssistantAgent(
    name="reviewer",
    model_client=model_client,
    tools=[read_diff],
    system_message="Review only the supplied diff and return typed findings.",
)
result = await agent.run(task="Review change set 42")
```

### Semantic Kernel：Plugin 与 Orchestration

Semantic Kernel 用 Plugin 封装 native code、OpenAPI 或 MCP 能力，和企业依赖注入较契合。Agent Framework 提供 Agent 抽象；官方 Agent Orchestration 文档列出 Concurrent、Sequential、Handoff、Group Chat 和 Magentic 等模式。2026-07-11 官方页面仍明确标注部分 Orchestration 能力为 experimental/prerelease，生产选型必须固定版本并接受变更风险。

Plugin 描述函数输入、输出与副作用，但授权仍在服务内部。Kernel/Runtime 管模型与消息，企业项目要把领域服务接口与框架 Plugin 分开。

### 框架比较

| 维度 | CrewAI | AutoGen | Semantic Kernel |
|---|---|---|---|
| 主要抽象 | Role/Task/Crew/Flow | AgentChat/Core/Team | Kernel/Plugin/Agent/Orchestration |
| 强项 | 角色任务与结构 Flow | 消息、事件与研究型协作 | .NET/企业 DI、Plugin 集成 |
| 状态风险 | Crew 对话替代 State | Stateful Agent/Team history | 实验 Orchestration 变化 |
| 适用 | 内容/研究 + Flow | 多 Agent 原型与事件系统 | Microsoft/.NET 企业应用 |

表格只描述当前总体定位，社区活跃、API 稳定和许可要在决策当天重查。不要根据 GitHub Star 或演示角色数量选型。

### 同题实测：通过接线不等于值得拆分

本书使用同一个受限补丁任务验证三个候选：Executor 只能修改 Fixture 中的 `app.py`，必须拒绝读取 Secret；Reviewer 决定批准或退回；运行时最多允许四条角色消息。CrewAI 版本使用类型化 `Flow`，AutoGen 使用原生 `RoundRobinGroupChat` 与组合终止条件，Semantic Kernel 使用 `Kernel` 与两个 `kernel_function` Plugin。全部离线测试均覆盖批准路径和强制不批准路径。

```mermaid
%% id: multi-agent-framework-evidence-gate
%% title: Multi-Agent 框架同题证据门禁
%% alt: 三个框架实现同一受限任务，并与单 Agent 基线比较权限状态消息和终止结果
flowchart LR
    Spec["同一任务契约"] --> Crew["CrewAI Flow"]
    Spec --> Auto["AutoGen Team"]
    Spec --> SK["Semantic Kernel Plugins"]
    Crew --> Gate["Tool Policy / State Export<br/>Message Limit / Termination"]
    Auto --> Gate
    SK --> Gate
    Base["单 Agent：1 条消息"] --> Compare{"协作净收益"}
    Gate --> Compare
    Compare -->|本 Fixture 未证明| Simple["优先单 Agent 或普通工作流"]
```

三个实现都用两条角色消息完成任务，单 Agent 基线只需一条。独立 Reviewer 提供职责隔离，但这个小型 Fixture 没有测出成功率收益，因此结论不是“三个框架都推荐”，而是“它们能表达该边界，但本任务应保留更简单方案”。完整代码、固定版本、源码哈希和直接测试见 `examples/framework_comparison/multi_agent_spike/`。Semantic Kernel 当前证据只覆盖 Kernel/Plugin 接线，不冒充原生 Agent Orchestration 实测。

### 成本、终止与调试

共享预算器限制总模型调用、Token、工具、时间和消息。终止条件包括任务验收、最大回合、无进展、重复消息、Policy 拒绝和人工停止。无进展可以比较 Artifact/State 哈希，而不是仅检测相同句子。

调试保存消息拓扑、sender/recipient、任务 ID、Artifact 版本、工具 Trace 和终止原因。每个角色的 Prompt 单独测试，团队测试再覆盖通信。Reviewer 使用独立 rubric，但若与 Coder 是同一模型和证据，应承认其相关性。

### 常见误区与安全

常见误区包括角色越多越好、群聊产生的共识等于事实、多个同模型 Agent 等于独立专家，以及框架 Memory 自动保持一致。外部动作仍需 Policy/审批，Agent 凭证最小化，消息不转发 secret，代码执行使用 Sandbox。若单 Agent + tools 达到相同成功率，应选择更简单方案。
总结：Multi-Agent 框架放大协作能力，也放大消息、状态、成本和安全复杂度。练习：用单 Agent 和两种团队方案完成同一任务，证明净收益，否则回退。面试：共享状态和消息历史如何区分？如何避免无效对话？实验性框架能力如何进入生产？延伸阅读：[CrewAI](https://docs.crewai.com/)、[AutoGen](https://microsoft.github.io/autogen/stable/)、[Semantic Kernel Agent Orchestration](https://learn.microsoft.com/en-us/semantic-kernel/frameworks/agent/agent-orchestration/) 官方文档。代码目录：`projects/09-multi-agent-dev-team/`。

## 本章引用
<!-- chapter-citations:start -->
以下资料用于支撑本章的核心原理、工程边界与版本敏感说明：

- [crewai-docs：CrewAI Documentation](../references.md#ref-crewai-docs)
- [autogen-docs：AutoGen Documentation](../references.md#ref-autogen-docs)
- [autogen-teams：AutoGen AgentChat Teams](../references.md#ref-autogen-teams)
- [semantic-kernel-docs：Semantic Kernel Documentation](../references.md#ref-semantic-kernel-docs)
- [wu2023autogen：AutoGen: Enabling Next-Gen LLM Applications via Multi-Agent Conversation](../references.md#ref-wu2023autogen)
<!-- chapter-citations:end -->
