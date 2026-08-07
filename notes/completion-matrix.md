# 教材完成矩阵

状态审计日期：2026-08-07。该日期只表示仓库交付审计，不表示所有外部 API 在当天重新核对。

## 状态词汇

正文状态：

- `outline`：只有提纲或片段。
- `publishable_draft`：可连续阅读并通过结构门禁，仍需技术编辑和出版编辑。
- `editor_reviewed`：完成独立技术与中文编辑复审。

代码状态：

- `inline_only`：只有正文内代码，没有对应独立工程验收。
- `offline_verified`：独立模块或项目已用 Mock、Fixture 或本地服务验证。
- `online_verified`：使用受控真实供应商或远程系统完成联调。

版本状态：

- `stable_concepts`：主要讲稳定原理，仍需定期检查术语和引用。
- `official_docs_checked`：按记录日期核对官方文档，但没有安装运行全部示例。
- `installed_and_tested`：固定依赖版本并运行直接测试。

出版状态：

- `markdown_only`：仅原稿。
- `html_verified`：HTML 构建和审计通过。
- `pdf_epub_verified`：HTML、PDF、EPUB 自动出版审计通过，仍可能需要人工设备复验。

项目成熟度：

- `concept`：只有设计。
- `vertical_slice`：主要教学链路可离线运行。
- `service_template`：具备服务接口、配置、持久化和直接测试。
- `production_reference`：具备权限、观测、恢复、评估、部署和故障演练证据。
- `externally_validated`：使用真实外部账号或系统完成受控联调。

## 38 章完成矩阵

| 章节 | 正文 | 代码 | 版本 | 出版 | 主要缺口 | 目标阶段 |
|---|---|---|---|---|---|---|
| 第1章 | `publishable_draft` | `inline_only` | `stable_concepts` | `pdf_epub_verified` | 独立技术编辑、引用链接 | P6 |
| 第2章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 目标模型 Tokenizer 在线对照 | P3—P4 |
| 第3章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 与训练框架 Attention 对照 | P4 |
| 第4章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 真实模型参数对照实验 | P4 |
| 第5章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 正式 Embedding 与 Reranker 对照 | P4 |
| 第6章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 远程 Prompt Registry 与发布审批 | P4 |
| 第7章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 真实 Provider 受预算冒烟测试 | P3—P4 |
| 第8章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 独立幂等与审批恢复工程 | P2 |
| 第9章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 持久 Checkpoint、取消和恢复工程 | P2—P4 |
| 第10章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 将正文对照模板落为批量基准 | P4 |
| 第11章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 远程 OAuth、Origin 与对象授权 | P4 |
| 第12章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 取消、超时、远程授权和部署压测 | P4 |
| 第13章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 正式 Embedding、Reranker 和版本化黄金集 | P4 |
| 第14章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 将正文消融模板落为正式批量实验 | P4 |
| 第15章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 向量记忆、规模压测与跨系统删除 | P4 |
| 第16章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 多库性能与迁移实验 | P1—P4 |
| 第17章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 生产存储与分布式恢复 | P4 |
| 第18章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | MCP 与真实 Provider 受控联调 | P3 |
| 第19章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 真实 Provider 与生产服务部署 | P3—P4 |
| 第20章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 数据库 Checkpointer 和外部副作用恢复 | P4 |
| 第21章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 原生候选、真实 Embedding、Citation、P95 与成本 ADR | P3—P4 |
| 第22章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 真实 Provider、分布式恢复与 SK 原生 Agent Orchestration | P3—P4 |
| 第23章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 独立练习与答案 | P1—P5 |
| 第24章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | SSE 恢复、鉴权与限流实测 | P1—P4 |
| 第25章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 迁移、备份和故障恢复演练 | P1—P4 |
| 第26章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | HTTPS、Secret 和部署环境验收 | P1—P4 |
| 第27章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | DLQ、取消和分布式 Worker 演练 | P1—P4 |
| 第28章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | OpenTelemetry 后端和隐私策略实测 | P1—P4 |
| 第29章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 将正文 Schema 落为持续回归流水线 | P4 |
| 第30章 | `publishable_draft` | `offline_verified` | `official_docs_checked` | `pdf_epub_verified` | 将威胁模型落为项目攻击回归集 | P4 |
| 第31章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 压测、模型路由和质量约束实验 | P1—P4 |
| 第32章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 扩大黄金集并评估真实模型协作净收益 | P4 |
| 第33章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 沙箱、补丁回滚和真实仓库实验 | P1—P4 |
| 第34章 | `publishable_draft` | `inline_only` | `official_docs_checked` | `pdf_epub_verified` | Browser Agent 可重复 UI 测试工程 | P1—P4 |
| 第35章 | `publishable_draft` | `inline_only` | `official_docs_checked` | `pdf_epub_verified` | OCR、音频、视频和多模态评估 | P1—P4 |
| 第36章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 在项目 10 落地 Outbox 与拆分演练 | P4 |
| 第37章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | SLA、灰度、运营和商业化案例 | P1—P5 |
| 第38章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 完整 RAG ADR、真实 Provider 与升级回归 | P3—P4 |

## 10 个项目完成矩阵

| 项目 | 当前成熟度 | 已验证范围 | 主要缺口 | 目标阶段 |
|---|---|---|---|---|
| 项目1 | `vertical_slice` | 离线模型、流事件、历史、Usage 和错误 | 服务 API、恢复、预算、观测 | P4 |
| 项目2 | `vertical_slice` | Tool Loop、校验、并行、重试和审批 | 真实 Provider、幂等写入、审批恢复 | P4 |
| 项目3 | `vertical_slice` | 旧 JSON-RPC 教学子集；官方 SDK 2.0.0 Tool/Resource/Prompt、stdio 与无状态 HTTP | OAuth、Origin、取消、超时和部署治理 | P4 |
| 项目4 | `vertical_slice` | 四格式解析、检索、引用、评估和 pgvector 路径 | Worker、OCR、正式模型、索引版本和黄金集 | P4 |
| 项目5 | `vertical_slice` | Diff、规则、语义 Review、报告和 HTTP 边界 | GitHub App、Sandbox、Webhook 和去重 | P4 |
| 项目6 | `vertical_slice` | Provider 边界、总结、日报、审批和审计 | 真实账号适配、Outbox 和冲突处理 | P4 |
| 项目7 | `vertical_slice` | 多 Provider、技术指标、来源和事实/推断 | 正式数据源、财报解析和时效评估 | P4 |
| 项目8 | `vertical_slice` | LangGraph、RetryPolicy、Checkpoint 和中断 | 持久存储、真实检索、Worker 和恢复演练 | P4 |
| 项目9 | `vertical_slice` | 五角色、共享状态、预算和终止 | 仓库沙箱、补丁回滚、单 Agent 基线 | P4 |
| 项目10 | `service_template` | API、数据库、Redis 队列、租户、Trace 和 Eval 基础 | OIDC/RBAC、迁移、DLQ、管理面和备份恢复 | P4 |

当前没有项目标记为 `production_reference` 或 `externally_validated`。达到这些状态必须补齐相应阶段的直接证据，不能仅根据 README 描述升级状态。
