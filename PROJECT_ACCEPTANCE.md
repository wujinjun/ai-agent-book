# 十个项目验收矩阵

核对日期：2026-08-08。`通过` 仅表示仓库内存在可运行实现和直接测试；README 描述、共享 Mock 返回或未执行的适配器不算通过。本轮还从当前源码构建十个 Python 3.12 服务镜像并逐项执行 Readiness，详细证据见 `notes/p9-project-runtime-qa.md`。

| 项目 | 原始功能范围 | 当前证据 | 状态 |
|---|---|---|---|
| 1 最小 Assistant | LLM、流式、Token、历史、配置、错误 | OpenAI-compatible SSE 适配器、离线模型、JSONL 历史、Usage/错误事件、独立 CLI 与 3 项直接测试 | 通过 |
| 2 天气工具 Agent | 多工具、校验、Tool Loop、重试、审批 | Planner 协议、天气/计算/外部写工具、Pydantic 校验、并行执行、有限重试、审批与 3 项直接测试 | 通过 |
| 3 MCP 本地工具 | Server、Client、文件、系统、数据库 | JSON-RPC 2.0 stdio Server、Client、初始化、Tool/Resource、路径沙箱、SQLite 查询与 3 项直接测试 | 通过 |
| 4 企业知识库 | PDF/Word/PPT/MD、Chunk、Embedding、pgvector、检索、重排、引用、评估 | 四格式解析、切分、混合重排、引用、Recall/MRR；Psycopg 实际写入 pgvector、创建 HNSW 并以租户条件检索 11 个 Chunk，返回 5 个 Hit | 通过 |
| 5 Code Review | 仓库、Diff、规则、LLM、风险、报告、可选 PR 评论 | 真实 Git Diff、四类规则、语义 Reviewer 协议、风险报告、审批式 GitHub HTTP 与 2 项直接测试 | 通过 |
| 6 自动办公 | 邮件、总结、日报、日历、外部集成、审批、审计 | Mail/Calendar Provider、日报、内容绑定批准、飞书/内部 Webhook、JSONL 审计与 2 项直接测试 | 通过 |
| 7 股票研究 | 行情、新闻、公告/财报、指标、行业、结构报告、时间、引用、事实/推断 | 三 Provider 并发、HTTP 行情边界、SMA/收益率/RSI、时间来源、事实/推断、免责声明与 2 项直接测试 | 通过 |
| 8 LangGraph 研究工作流 | 规划、搜索、读取、重试、Reviewer、报告、Checkpoint、HITL | 实测 LangGraph 1.2.9、RetryPolicy、条件 Reviewer、InMemorySaver、interrupt/Command 恢复、报告与 2 项直接测试 | 通过 |
| 9 Multi-Agent 开发团队 | 五角色、共享状态、成本、终止、无效对话控制 | 五角色、Coordinator、版本状态、Artifact/Test/Review、消息与 Token 硬预算、终止及 2 项直接测试 | 通过 |
| 10 企业平台 | 多用户/Agent/Tool、MCP、RAG、权限、会话、队列、Trace、Eval、管理 API、Compose | SQLAlchemy SQLite/PostgreSQL、Redis 唤醒+数据库恢复队列、全功能 API 和 5 项测试；Compose 三服务健康、纵向脚本通过、PostgreSQL 持久化与 API 重启恢复已验证 | 通过 |

## 通用完成条件

每个项目必须具备独立入口、配置模型、领域模块、Mock/本地适配器、错误边界、直接测试、README、架构图、数据流、Dockerfile 和可重复运行命令。需要账号的写操作必须默认关闭并有 Mock；无需账号即可实现的协议、文件、SQLite、HTTP Fake、状态持久化和评估不能只留 TODO。

P9 新增运行门禁：Dockerfile 必须复制 `pyproject.toml` 声明的许可证元数据；只读根文件系统下所有主状态和次级状态路径必须落入显式可写卷；镜像构建成功后还要启动服务并访问 Readiness。项目 1—10 已在 Docker 29.4.0 实际通过该门禁。

## 出版验收条件

38 章和十个项目 README 都必须检查图示、代码围栏、内部链接和术语。最终 PDF/EPUB 必须在所有内容固定后重建；PDF 至少按封面、目录、每篇首章、代码密集页、图示密集页和末页抽检，EPUB 必须验证结构、导航、中文、代码块与图示回退文本。
