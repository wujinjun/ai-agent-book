# 教材完成矩阵

状态审计日期：2026-08-13。该日期只表示仓库交付审计，不表示所有外部 API 在当天重新核对。十项目的逐项路径证据另见 `notes/project-capability-matrix.yml`，该文件由根测试校验。

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
| 第1章 | `publishable_draft` | `inline_only` | `stable_concepts` | `pdf_epub_verified` | P9 独立技术与中文审稿 | P9 |
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
| 第34章 | `publishable_draft` | `offline_verified` | `official_docs_checked` | `pdf_epub_verified` | 真实浏览器供应商联调与动态站点回归 | P4 |
| 第35章 | `publishable_draft` | `inline_only` | `official_docs_checked` | `pdf_epub_verified` | OCR、音频、视频和多模态评估 | P1—P4 |
| 第36章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | 在项目 10 落地 Outbox 与拆分演练 | P4 |
| 第37章 | `publishable_draft` | `offline_verified` | `stable_concepts` | `pdf_epub_verified` | SLA、灰度、运营和商业化案例 | P1—P5 |
| 第38章 | `publishable_draft` | `offline_verified` | `installed_and_tested` | `pdf_epub_verified` | 完整 RAG ADR、真实 Provider 与升级回归 | P3—P4 |

## 10 个项目完成矩阵

| 项目 | 当前成熟度 | 已验证范围 | 主要缺口 | 目标阶段 |
|---|---|---|---|---|
| 项目1 | `service_template` | 离线模型、流事件、历史、Usage；持久 Run、SSE 回放、预算、取消与审计 | Provider 受控联调、流中断续传压测 | P4 |
| 项目2 | `service_template` | Tool Loop、校验、并行、重试、审批；持久 Run 与幂等服务边界 | 真实天气、审批恢复专项链路 | P4 |
| 项目3 | `service_template` | 官方 SDK 2.0.0 Tool/Resource/Prompt、stdio/HTTP；租户化服务边界 | OAuth、Origin、取消、超时和部署治理 | P4 |
| 项目4 | `production_reference` | 四格式解析、pgvector、持久摄取 Worker、输入与 Chunk 完整性指纹、版本索引、黄金发布门禁、原子切换、租户限定回滚、恢复、租户 API 与引用 | OCR、正式 Embedding/Reranker、删除传播、规模压测与外部验证 | P4—P9 |
| 项目5 | `service_template` | Diff、规则、语义 Review、报告、Diff 预算 Sandbox、Webhook HMAC/持久去重、绑定提交与报告哈希的限时审批、评论标记远端查询去重、HTTP、权限与审计 | 真实 GitHub App 安装鉴权、多语言静态分析容器和并发评论单写领取 | P4 |
| 项目6 | `service_template` | Provider、日报、内容/目标绑定限时审批、持久租约 Outbox、幂等发布、确定失败重试、未知结果冻结、可选远端回执对账、审计与持久服务状态 | 真实账号 OAuth、真实供应商回执查询适配和限流联调 | P4 |
| 项目7 | `service_template` | 多 Provider、指标、来源、事实/推断；持久服务状态 | 正式数据源、财报解析和时效评估 | P4 |
| 项目8 | `production_reference` | LangGraph、RetryPolicy、Interrupt、持久 Run Journal、证据 Allowlist/哈希、租户 Worker、审批、跨进程确定性重放，以及报告发布 Outbox、稳定幂等键和回执恢复 | 真实搜索、原生数据库 Saver、真实 Publisher 幂等/未知结果对账与外部验证 | P4—P9 |
| 项目9 | `service_template` | 五角色、版本共享状态、预算、指纹循环终止、单 Agent 基线、一次性 Git 克隆、补丁策略、失败销毁与白名单测试；权限、取消与审计 | OCI/微虚拟机强隔离、依赖供应链治理和真实任务基准 | P4 |
| 项目10 | `production_reference` | 多租户 API、PostgreSQL/SQLite、Redis 恢复队列、Verifier/RBAC、租户限定 Worker、短事务租约、心跳、崩溃恢复、协作式运行中取消、内容绑定一次性 DLQ 重放批准、Trace/Eval/指标和一致性备份 | 真实 OIDC/JWKS、RLS、独立 Worker Deployment、管理前端、OpenTelemetry 与灾备演练 | P4—P9 |

项目 4、8、10 已达到离线 `production_reference`，但没有项目标记为 `externally_validated`。外部状态必须有真实账号、远程系统或设备验收证据，不能仅根据 README 描述升级。

P9 于 2026-08-08 从当前源码重建十个 Python 3.12 Linux 服务镜像，并逐个执行 Readiness；项目 10 同时启动 pgvector PostgreSQL 与 Redis。该结果关闭了“容器仅静态配置验证”的缺口，但不改变上述外部供应商和生产环境边界。运行证据见 `notes/p9-project-runtime-qa.md`。

## 企业培训交付矩阵

| 交付物 | 状态 | 验收证据 | 后续边界 |
|---|---|---|---|
| 讲师与学员手册 | `repository_verified` | 课前、课中、课后节奏；12 个实验；提交与失败证据契约 | 真实班级试讲在 P9 |
| 学习路线与评分 | `repository_verified` | 8/12/24 周路线、周任务、时间、输出、检查标准和双层 Rubric | 根据试学数据校准难度 |
| 题库与案例 | `repository_verified` | 38 章题目、100 分综合考试、参考答案、五类企业案例 | 外部技术审阅在 P9 |
| 工作坊 | `repository_verified` | 架构评审、威胁建模、成本估算的输入、流程与产出 | 企业场景试讲在 P9 |
| 离线培训包 | `offline_verified` | 四组稳定 Fixture、内容哈希、Pydantic 校验与确定性清单 | 在线 Provider 仅作可选扩展 |
| 培训幻灯片 | `visual_verified` | 16 页 PPTX、逐页渲染、溢出检查、讲师备注与来源块 | 投影设备实测在 P9 |

## 引用与出版编辑矩阵

| 维度 | 状态 | 验收证据 | 后续边界 |
|---|---|---|---|
| 正式资料 | `repository_verified` | 113 条论文、标准、官方文档和官方仓库资料 | 版本敏感页面持续复核 |
| 章节引用 | `repository_verified` | 38 章、163 处生成引用、每章至少 3 条 | 逐句引文由独立审稿人抽检 |
| 外链 | `network_checked` | 113/113 有解释结果，0 个未处理失败 | 发行前重新运行网络核查 |
| 中文与技术编辑 | `maintainer_reviewed` | 编辑规范、自动审计和 P6 复审记录 | `editor_reviewed` 仍要求 P9 独立审稿 |
| 权利与许可 | `boundary_documented` | 内容 CC BY-NC-SA、代码 MIT、商业许可说明、CLA、素材清单 | 商业合同与法律意见在 P9 |
