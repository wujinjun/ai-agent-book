# 版本核查清单

官方资料最后核对：各条目单独记录。仓库完成度审计：2026-08-07。

两个日期含义不同：完成度审计只核对仓库中已有文件、测试与声明，不能据此推断外部框架 API 已在 2026-08-07 重新验证。

本文件只记录版本敏感项，不用“记忆中的 API”填补空白。写作对应章节前，必须同时检查当前安装版本、官方文档和官方仓库示例。

| 主题 | 当前状态 | 核查要求 |
|---|---|---|
| OpenAI Agents SDK | 2026-08-07 固定并安装实测 `openai-agents==0.18.3` | `examples/openai_agents_sdk/` 离线验证 Runner、工具、结构化输出、handoff、agent-as-tool、阻塞 guardrail、SQLiteSession 与敏感 Trace 配置；MCP 在线/远程集成仍留待 P3 |
| PydanticAI | 2026-08-07 固定并安装实测 `pydantic-ai-slim==2.25.0` | `examples/pydanticai_service/` 离线验证 Agent、`deps_type`、`output_type`、`RunContext`、Tool Schema、output validator、`TestModel`、`FunctionModel`、`Agent.override` 与 FastAPI 错误映射；真实 Provider 联调仍留待后续受控验证 |
| Framework Comparison | 2026-08-07 隔离实跑 Native、OpenAI Agents SDK 0.18.3、PydanticAI 2.25.0 | 同一研究 Fixture 运行 20 次，记录工具准确率、瞬时恢复、P95、请求成本代理、状态导出、Python/框架版本与实现 SHA-256；不外推真实 Provider 质量或网络延迟 |
| LangGraph | 已安装实测 | 1.2.9；项目 8 覆盖 StateGraph、RetryPolicy、Checkpoint、interrupt 与 Command(resume) |
| MCP | 2026-08-07 固定并安装实测官方 Python SDK `mcp==2.0.0`，对应 2026-07-28 规范 | 项目 3 保留 2025-11-25 手写教学子集，并在 `official_sdk/` 直接验证 Tool、Resource、Prompt、stdio 子进程与无状态 Streamable HTTP；OAuth、Origin、取消和高负载超时留待 P4 |
| LangChain / LlamaIndex | 2026-08-07 隔离安装实测 LangChain 1.3.14（core 1.5.3）与 LlamaIndex Core 0.14.23 | `rag_spike/` 使用同一确定性 Embedding、文档、Metadata ACL、黄金查询和拒答阈值；真实 Embedding、生成、外部 Vector Store、P95 与成本尚未验证 |
| CrewAI / AutoGen / Semantic Kernel | 官方文档已核对；未安装实测 | 当前稳定版、实验特性和维护状态在选型当天复核 |
| SQLAlchemy / Psycopg / Redis | 已安装实测基础路径 | SQLAlchemy 2.0.51、Psycopg 3.3.4、Redis client 8.0.1；Docker 服务集成待 daemon 验证 |
| NumPy | 2026-08-06 已隔离安装实测 | 2.5.1；`examples/attention_demo/` 覆盖缩放点积、Mask、多头形状和 SVG/PNG 导出 |

依赖固定于 `requirements.txt` 的日期快照并不意味着这些版本长期推荐。升级应先运行测试与文档构建，再更新章节的“最后核对日期”。
