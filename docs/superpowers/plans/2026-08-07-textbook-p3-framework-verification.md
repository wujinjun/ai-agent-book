# Textbook P3 Framework Verification Plan

> 执行规则：每个版本敏感框架使用独立 Python 3.12 环境，先核对官方文档和安装包，再编写教材代码；不得把相互冲突的依赖合并进根环境。

## 目标与证据契约

P3 将第 11、12、21、22、38 章中尚未实测的框架描述转化为可重复证据。每个候选必须记录固定版本、Python 版本、核对日期、官方来源、离线 Fixture、直接测试、失败注入、源码哈希和升级说明。无法确认的接口保留明确 TODO，不凭记忆补写。

```mermaid
flowchart LR
    Docs["官方文档与发布包"] --> Pin["固定版本与隔离环境"]
    Pin --> Spike["同题最小垂直切片"]
    Spike --> Faults["超时、无效参数、恢复与权限测试"]
    Faults --> Evidence["版本、日志、指标与源码哈希"]
    Evidence --> Chapter["章节、选型矩阵与升级记录"]
```

图中每一步都是发布门禁：文档示例只有在隔离环境运行后才能升级为 `installed_and_tested`，比较结论必须指向同题证据而不是社区印象。

## Task 1：建立统一框架验收器

- [ ] 扩展 `scripts/verify_examples.py`，支持 P3 候选环境、超时、缓存和 JSON 证据。
- [ ] 定义统一研究/RAG Fixture、黄金答案、工具故障、权限拒绝和恢复场景。
- [ ] 为版本、Python、命令、源码哈希和指标建立稳定 Schema。
- [ ] 增加升级回归测试，依赖变化时明确显示 API 差异。

## Task 2：官方 MCP SDK

- [x] 核对当前 MCP 规范、Python SDK 官方仓库和安全建议。
- [x] 固定 `mcp==2.0.0`，分别实现并直接测试 stdio 与无状态 Streamable HTTP 最小工程。
- [ ] 覆盖 Tool、Resource、Prompt、能力发现、参数错误、取消和超时。
- [ ] 测试 Origin、授权、会话/无状态边界、日志输出不污染 stdio 协议。
- [x] 更新第 11、12 章和项目 3，保留 2025-11-25 教学子集的历史边界说明。

## Task 3：LangChain 与 LlamaIndex 同题 RAG

- [x] 分别固定 LangChain 1.3.14（core 1.5.3）和 LlamaIndex Core 0.14.23。
- [x] 使用同一文档、查询、确定性 Embedding、ACL、黄金集和拒答场景。
- [ ] 比较检索正确率、引用完整性、状态导出、P95 与成本代理。
- [x] 验证两个框架均在检索阶段执行租户权限，并用阈值拒绝零相关候选。
- [ ] 更新第 21、38 章，并生成可逆 ADR。

## Task 4：CrewAI、AutoGen 与 Semantic Kernel

- [ ] 每个框架只实现同一受限 Reviewer/Executor 协作任务，不堆叠角色。
- [ ] 测试消息上限、共享状态、工具权限、终止条件和循环检测。
- [ ] 记录单 Agent 基线，只有净收益为正时才推荐 Multi-Agent。
- [ ] 对 Semantic Kernel 使用独立 .NET 或 Python 环境，以官方当前支持面为准。
- [ ] 更新第 22、32、38 章的能力矩阵和不适用条件。

## Task 5：OpenAI Agents SDK 与 PydanticAI 补充验证

- [ ] 为 OpenAI Agents SDK 验证当前 MCP 集成和受预算真实 Provider 冒烟路径。
- [ ] 为 PydanticAI 验证真实 Provider、超时和生产服务关闭流程。
- [ ] 保持默认离线，在线测试必须显式启用、设置预算并脱敏 Trace。
- [ ] 将破坏性升级写入 `notes/version-check.md` 和 CHANGELOG。

## Task 6：P3 总验收

- [ ] 所有候选在独立 Python 3.12 环境安装并运行直接测试。
- [ ] 根测试、Ruff、mypy、断链、密钥扫描和出版审计通过。
- [ ] 更新完成矩阵、质量路线图、框架比较证据和版本核查日期。
- [ ] 重建 220+ 组 SVG/PNG、HTML、PDF 和 EPUB并完成人工抽样。
- [ ] 只把有安装运行证据的章节标记为 `installed_and_tested`。

## 完成标准

P3 完成时，官方 MCP SDK、LangChain、LlamaIndex、CrewAI、AutoGen 和 Semantic Kernel 均有固定版本的最小工程与直接测试；第 38 章的比较结论能够由隔离环境证据重放。真实账号不是默认测试的前提，但需要在线验证的能力必须清楚标记边界。
