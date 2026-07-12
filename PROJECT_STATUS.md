# 项目状态

核对日期：2026-07-11。状态原则：只有正文、代码、直接测试和运行证据同时存在时才标记完成；Mock/Fixture 会明确标注，未使用真实账号的第三方服务不会写成已经联调。

## 已完成

- 教材工程：README、贡献说明、学习路线、术语表、参考资料、版本核查、MkDocs Material 导航、发布脚本和 Python 3.12 CI 工作流齐全。
- 全书正文：第 1—38 章均通过统一内容门禁；第 2—7 篇已按要求完成。每章至少包含学习目标、前置知识、核心原理、Mermaid 图示、带语言的代码/配置块、工程示例、误区、调试、安全、总结、练习、面试、延伸阅读和代码目录。
- 图文与格式复审：38 章均含 Mermaid 图示和非图示代码块；围栏配对、语言标签、内部链接、项目 README 图示/命令/目录树均由自动测试检查。
- 项目 1—10：逐项功能与证据见 `PROJECT_ACCEPTANCE.md`，十项均已通过。每个项目有独立入口、README、架构图、环境样例、Dockerfile、项目目录测试和根级深度测试。
- 项目 10 基础设施：API、PostgreSQL 17、Redis 7 Compose 三服务均达到 healthy；纵向脚本实际创建 Agent、MCP Tool、Session 和 Run，Worker 完成任务，管理 API 查回结果。PostgreSQL 中成功 Run 可查询，Redis PING 为 PONG 且消费后队列为 0；API 重启后 Run 仍可读取。
- 项目 4 pgvector：Compose 使用 `pgvector/pgvector:pg17`；Psycopg Repository 实际创建 vector 扩展与 HNSW 索引，写入 11 个 128 维 Chunk，并在租户过滤下返回 5 个向量检索结果。切换 pgvector 镜像后项目 10 纵向验收再次通过。
- Python 3.12：本机 `.venv` 为 Python 3.12.13；十个 `main.py` 均直接运行；十个 Dockerfile 均基于 Python 3.12，其中项目 1—9 已逐一构建和运行，项目 10 已通过 Compose 构建与运行。
- 发布产物：MkDocs 严格构建成功；PDF 与 EPUB 从同一 Markdown 快照生成。PDF 为 138 页，已抽检封面、目录、各篇代表章、代码/图示页、项目 4/8/10、末章和末页；EPUB ZIP、导航、54 个条目、中文和图示回退文本通过检查。

## 版本敏感项

- LangGraph 固定并实测 `1.2.9`；项目 8 覆盖 `StateGraph`、`RetryPolicy`、Checkpoint、`interrupt` 与 `Command(resume)`。
- MCP 项目按 2025-11-25 规范实现 JSON-RPC/stdio 教学子集；没有声称覆盖远程授权规范的全部功能。
- SQLAlchemy 2.0.51、Psycopg 3.3.4 和 Redis client 8.0.1 已在项目 10 运行路径中验证。
- OpenAI Agents SDK、PydanticAI、LangChain、LlamaIndex、CrewAI、AutoGen 和 Semantic Kernel 的章节定位按 2026-07-11 官方文档核对；未安装运行的框架示例均明确要求按当前安装版本复验，不编造接口。

## 第三方账号边界

- GitHub 评论、办公 Webhook 和行情 HTTP 通过真实 HTTP 适配器加 `httpx.MockTransport` 验证请求边界；默认不执行外部写操作，写操作需要显式批准。
- Gmail/Outlook、Notion/飞书账号、真实证券数据和付费模型密钥不属于可自动提供的仓库凭证。项目提供 Provider/Adapter、Fixture、超时、审批和测试，因此无账号也能完整运行教学链路。
- 股票项目固定输出“不构成投资建议”，区分事实与推断，并记录数据时间与来源。

## 仍建议人工执行的出版工作

- 中文出版编辑、版权与商标表述复核。
- 在目标发行渠道的 EPUB 阅读器上做设备兼容性抽检。
- 发布前按 `notes/version-check.md` 再核对快速变化的框架与产品信息。

这些属于正式出版和持续维护流程，不是当前教材工程、代码或发布产物的未完成占位。

## 最终自动与运行验证

2026-07-11：Python 3.12.13 下根测试与十项目目录测试共 72 项通过；Ruff 全仓通过，mypy 严格检查 20 个源/入口模块通过，`mkdocs build --strict`、PDF/EPUB 构建和 `docker compose config --quiet` 均通过。十个项目入口和十个 Docker 部署路径均实际运行。项目 4 pgvector 与项目 10 Compose 纵向验证、数据库持久化、Redis 队列和 API 重启恢复通过，最近一次修复后的容器日志没有未处理 ERROR。最终 PDF 为 138 页、395,779 bytes，EPUB 为 188,529 bytes、54 个 ZIP 条目且无损坏条目；PDF 中 Python 路径下划线保真测试通过。
