# 版本核查清单

最后更新：2026-07-11。

本文件只记录版本敏感项，不用“记忆中的 API”填补空白。写作对应章节前，必须同时检查当前安装版本、官方文档和官方仓库示例。

| 主题 | 当前状态 | 核查要求 |
|---|---|---|
| OpenAI Agents SDK | 官方文档已核对；未安装实测 | Agent、Runner、handoff、guardrail、session、MCP 与 tracing 的具体代码仍以安装版复验为准 |
| PydanticAI | 官方文档已核对；未安装实测 | Agent、deps_type、output_type、RunContext、TestModel 与 override 需在引入依赖时复验 |
| LangGraph | 已安装实测 | 1.2.9；项目 8 覆盖 StateGraph、RetryPolicy、Checkpoint、interrupt 与 Command(resume) |
| MCP | 规范已核对，未引入官方 SDK | 按 2025-11-25 实现项目 3 的 JSON-RPC/stdio 子集；远程授权与官方 SDK 仍需单独实测 |
| LangChain / LlamaIndex | 官方文档已核对；未安装实测 | 包拆分、推荐抽象、弃用接口在添加示例依赖时复验 |
| CrewAI / AutoGen / Semantic Kernel | 官方文档已核对；未安装实测 | 当前稳定版、实验特性和维护状态在选型当天复核 |
| SQLAlchemy / Psycopg / Redis | 已安装实测基础路径 | SQLAlchemy 2.0.51、Psycopg 3.3.4、Redis client 8.0.1；Docker 服务集成待 daemon 验证 |

依赖固定于 `requirements.txt` 的日期快照并不意味着这些版本长期推荐。升级应先运行测试与文档构建，再更新章节的“最后核对日期”。
