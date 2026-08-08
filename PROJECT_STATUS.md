# 项目状态

仓库状态审计日期：2026-08-08。外部框架与规范的实际核对日期单独记录在 `notes/version-check.md`；仓库审计日期不能替代 API 版本核查日期。

完整的逐章、逐项目状态见 [`notes/completion-matrix.md`](notes/completion-matrix.md)，后续工作和验收标准见 [`docs/QUALITY_ROADMAP.md`](docs/QUALITY_ROADMAP.md)。

## 当前定位

当前版本是一套**可系统学习的多格式出版预览版**。38 章均有连续正文、图示、代码块和统一导航；十个项目均有可运行的领域纵切面与统一服务契约，其中项目 4、8、10 另有离线生产参考实现；HTML、PDF 和 EPUB 已建立可重复构建与自动审计流程。

“出版预览版”不等于商业出版终稿，也不等于十个项目均可直接投入生产。外部 Provider 联调、真实班级试讲、独立外部审稿、多设备版式验收和项目生产环境验证仍在质量路线图中跟踪。

基于 2026-08-06 P0 审计时的用途估计为：个人系统学习约 85%，企业内部培训约 80%，GitHub 开源展示约 85%，正式商业出版约 65%，十个生产项目模板约 55%。P1 已扩充核心章节，但在 P2—P9 完成和重新试学前不虚构新的百分比；这些数值只用于排序工作，不替代完成矩阵中的具体证据。

## 正文完成度

- 38 章正文齐全，约 29.1 万字符；本轮选定的 16 个核心章节均超过 8,000 字符，其余普通章节多数约 4,000—6,000 字符。
- 每章具备学习目标、前置知识、核心原理、Mermaid 图、代码或配置块、误区、调试、安全、总结、练习、面试和延伸阅读等结构要素。
- 第一章与第 2、5、8—15、17、20、29、30、36、38 章达到核心讲义深度，具备独立原理、最小实验、工程案例、失败调试与练习参考答案；其他普通章节仍需在后续编辑批次加深。
- 全书当前状态统一为 `publishable_draft`，尚未标记为 `editor_reviewed`。
- 章节门禁能验证结构、路径、围栏和最低内容要求，但不能替代人工技术审阅和出版编辑。

## 代码完成度

- 当前 Python 3.12.13 环境下，根级测试共 206 项通过；其中十项目共享服务契约按项目参数化验证持久化、幂等、租户权限、预算、取消、SSE 回放、指标与重建恢复，项目 4、8、10 另有生产恢复路径测试；独立示例及框架候选隔离测试也均通过。
- 根代码包含 Tool Runtime、十个项目领域模块、出版管线和质量审计；十个项目入口都能在离线模式运行。
- P2 规划的 11 个独立示例已全部完成目录契约、离线运行、直接测试、章节双向链接和根级隔离环境编排；Framework Comparison 还使用三个隔离环境生成带版本与源码哈希的同题证据。`tool_runtime` 是规划外的既有工程，不计入 11/11。P2 的索引、图示和三种出版格式也已重新构建并审计通过。
- LangGraph 项目使用固定版本并有直接测试；OpenAI Agents SDK 0.18.3、PydanticAI 2.25.0、LangChain 1.3.14、LlamaIndex Core 0.14.23、CrewAI 1.15.12、AutoGen AgentChat 0.7.5 与 Semantic Kernel 1.44.1 已在各自独立 Python 3.12 环境实测明确范围。
- Mock、Fixture 和本地协议测试只证明适配边界与控制逻辑，不代表真实第三方账号联调。

## 项目成熟度

- 项目 1—9 已达到 `service_template`：保留各自领域纵切面，并新增项目级 FastAPI、SQLite Run 状态、幂等、租户权限、预算、取消、SSE 回放、审计、Trace、指标和统一安全 Compose；真实 Provider 与专项恢复能力仍需增强。
- 项目 10 已达到离线 `production_reference`：具备多租户 API、PostgreSQL/SQLite、Redis 恢复队列、身份 Verifier 与数据库 RBAC、Agent/Tool/MCP/RAG、Trace/Eval/指标、有限重试、租户 DLQ、重放、取消和一致性备份；真实 OIDC/JWKS、RLS、独立 Worker 与灾备演练仍待外部验证。
- 项目 4 已达到离线 `production_reference`：在 pgvector 与四格式解析基础上新增持久摄取 Worker、内容/配置/黄金集指纹、索引版本、Recall/MRR 发布门禁、原子激活、失败脱敏、恢复和租户 API；正式 Embedding/Reranker 与 OCR 仍未外部验证。
- 项目 8 已达到离线 `production_reference`：在真实 LangGraph、RetryPolicy、Interrupt/Command 基础上增加 SQLite Run Journal、来源 Allowlist、证据哈希、租户 Worker、人工审批和跨进程确定性重放；原生数据库 Saver 与真实搜索仍待外部联调。当前没有项目标记为 `externally_validated`。
- GitHub 评论、办公 Webhook 和行情 HTTP 使用真实适配器接口与 `httpx.MockTransport` 验证请求边界；默认不执行外部写操作。

## 版本核查边界

- LangGraph 固定并实测 `1.2.9`；项目 8 覆盖 `StateGraph`、`RetryPolicy`、Checkpoint、`interrupt` 与 `Command(resume)`。
- LangChain 1.3.14（core 1.5.3）与 LlamaIndex Core 0.14.23 已在独立 Python 3.12 环境用同一 RAG/ACL Fixture 实测；当前证据覆盖确定性检索、租户过滤和拒答阈值，不外推真实 Embedding、生成、P95 或成本。
- MCP 第 11—12 章已于 2026-08-07 按 2026-07-28 规范与官方 Python SDK `mcp==2.0.0` 复核；项目 3 保留 2025-11-25 手写教学子集，并新增官方 SDK Tool、Resource、Prompt、stdio 与无状态 Streamable HTTP 实测。远程 OAuth、Origin、取消和高负载超时仍未标记完成。
- SQLAlchemy 2.0.51、Psycopg 3.3.4 和 Redis client 8.0.1 已用于项目路径测试。
- CrewAI 1.15.12、AutoGen AgentChat/Core 0.7.5 与 Semantic Kernel 1.44.1 已于 2026-08-07 隔离安装并完成同题离线实测；Semantic Kernel 证据只覆盖 Kernel/Plugin，不把原生 Agent Orchestration 标记为已验证。
- 2026 版是维护目标年份，不表示外部 API 在全年保持不变。

## 出版完成度

- 全仓库共有 235 张 Mermaid 图，已经生成 SVG、2x PNG 和内容哈希清单；HTML、PDF 和 EPUB 使用预渲染资产，不依赖阅读器现场执行 Mermaid。
- MkDocs HTML 严格构建、断链、缺图、alt、重复 ID 和残留 Mermaid 自动审计已建立。
- PDF 当前为 400 页 A4、11,740,686 字节；封面、目录、章节过渡、代码、表格、图示和末页已渲染抽样，自动出版审计通过。
- EPUB3 为 12,553,294 字节，包含 226 张正文 SVG 与 226 张 PNG 回退，具备 nav、spine、严格 XHTML 与资源引用检查；HTML 下载目录同时包含最新 PDF 和 EPUB。
- GitHub `main` 已包含教材完成提交 `54dc936` 与状态提交 `c21dd9c`，标签 `v2026.8.0` 已推送。公开 [GitHub Release v2026.8.0](https://github.com/wujinjun/ai-agent-book/releases/tag/v2026.8.0) 已发布完整 `output/` 压缩包、400 页 PDF、EPUB3 与 SHA256；公开 API 复核为正式发行、非草稿、非预发布，四个附件尺寸与本地产物一致。
- Apple Books、Calibre、移动阅读器、黑白打印、孤行寡行和最终商业版式仍需人工复验。

## 尚未完成

- P1 已完成：16 个核心章节已增加最小实验、工程案例、失败调试、练习答案和深度契约；普通章节扩写继续由后续编辑阶段跟踪。
- P2 已完成：11 个独立示例工程通过隔离安装、离线运行、直接测试、静态检查和三格式出版复验。
- P3 核心范围已完成：版本敏感框架与官方 MCP SDK 均有固定版本和直接实测；真实 Provider、完整 RAG ADR 与升级回归属于后续外部验证。
- P4 核心成熟度目标已完成：十个项目均达到 `service_template`，项目 4、8、10 达到离线 `production_reference`；各项目的真实供应商、规模、灾备与安全验证继续按明确清单跟踪。
- P5 已完成仓库交付：讲师手册、学员实验手册、12 个核心实验、题库、综合考试、评分标准、五类企业案例、三个工作坊、离线 Fixture、环境初始化脚本和 16 页培训幻灯片均已落盘并通过自动门禁；真实班级试讲和学习效果评估进入 P9。
- P6 已完成仓库内审：正式参考资料扩充至 113 条，38 章生成 163 处可追溯引用；外链、术语、代码围栏、远程图片和版本日期通过门禁；教材内容与代码拆分许可，并建立商业许可边界、CLA 和素材核查记录。出版社终审、法律意见和独立技术审稿进入 P9。
- P7：逐张编辑图示，并完成 PDF/EPUB 多设备人工验收。
- P8：完善 GitHub 展示、贡献流程和自动质量门禁。
- P9：完成外部技术审阅、试学、试讲和正式版发布。

## 当前验证证据

2026-08-08 在 Python 3.12.13 下重新运行 Ruff、mypy 和 218 项根级测试；独立示例、框架候选、企业培训、引用、编辑与许可门禁全部通过。十项目服务契约、项目 4 版本化发布、项目 8 持久重放、项目 10 认证/DLQ/备份路径及两套 Compose 配置已验证，重建 235 组图示资产。公开 v2026.8.0 的 HTML、400 页 PDF 和 EPUB3 已通过上一轮自动审计；包含培训版与正式引用的新出版物将在 P7 统一重建。最终多设备发行验收仍以 P7 和 P9 为准。
