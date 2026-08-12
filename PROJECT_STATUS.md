# 项目状态

仓库状态审计日期：2026-08-12。外部框架与规范的实际核对日期单独记录在 `notes/version-check.md`；仓库审计日期不能替代 API 版本核查日期。

完整的逐章、逐项目状态见 [`notes/completion-matrix.md`](notes/completion-matrix.md)，后续工作和验收标准见 [`docs/QUALITY_ROADMAP.md`](docs/QUALITY_ROADMAP.md)。

## 当前定位

当前版本是一套**可系统学习的多格式出版预览版**。38 章均有连续正文、图示、代码块和统一导航；十个项目均有可运行的领域纵切面与统一服务契约，其中项目 4、8、10 另有离线生产参考实现；HTML、PDF 和 EPUB 已建立可重复构建与自动审计流程。

“出版预览版”不等于商业出版终稿，也不等于十个项目均可直接投入生产。外部 Provider 联调、真实班级试讲、独立外部审稿、多设备版式验收和项目生产环境验证仍在质量路线图中跟踪。

P9 当前状态为 `complete_repository_scope`。仓库证据分为个人系统学习 90%、企业内部培训 85%、GitHub 开源展示 93%、正式商业出版 82%、十个生产项目模板 80%，均达到本次仓库范围目标。原始完整目标继续保留；真人试学、试讲、独立外审、实体设备/印刷和专业权利意见被明确排除并标记为未验证。评分与边界见 [`FINAL_ACCEPTANCE.md`](FINAL_ACCEPTANCE.md) 和 [`notes/p9-acceptance.yml`](notes/p9-acceptance.yml)。

## 正文完成度

- 38 章正文齐全，所有章节至少 5,000 字符；本轮选定的 16 个核心章节均超过 8,000 字符。第 33、35 章已补充可运行最小实验、工程案例、失败调试与练习答案，分别达到约 8.9 千字符。
- 每章具备学习目标、前置知识、核心原理、Mermaid 图、代码或配置块、误区、调试、安全、总结、练习、面试和延伸阅读等结构要素。
- 第一章与第 2、5、8—15、17、20、29、30、36、38 章达到核心讲义深度，具备独立原理、最小实验、工程案例、失败调试与练习参考答案；其他普通章节仍需在后续编辑批次加深。
- 全书当前状态统一为 `publishable_draft`，尚未标记为 `editor_reviewed`。
- 章节门禁能验证结构、路径、围栏和最低内容要求，但不能替代人工技术审阅和出版编辑。

## 代码完成度

- 当前 Python 3.12.13 环境下，279 项根级与项目测试全量通过。其中十项目共享服务契约按项目参数化验证持久化、幂等、租户权限、预算、取消、SSE 回放、指标与重建恢复，项目 4、8、10 另有生产恢复路径测试；独立示例、框架候选、发行资产、培训课件字体与范围化发布契约测试也纳入同一根测试集合。
- 根代码包含 Tool Runtime、十个项目领域模块、出版管线和质量审计；十个项目入口都能在离线模式运行。
- 当前 13 个独立示例已全部完成目录契约、离线运行、直接测试、章节双向链接和根级隔离环境编排。Browser Safety Lab 在全新 Python 3.12 venv 中通过离线入口、6 项测试、Ruff 与严格 mypy，验证语义目标唯一性、页面与动作绑定审批、主体和 Origin Policy、幂等抑制及动作后业务状态复核；Cost/Latency Lab 同样保留全新环境验证。Framework Comparison 还使用三个隔离环境生成带版本与源码哈希的同题证据。`tool_runtime` 是清单外的既有工程，不计入 13 个示例。索引、图示和三种出版格式均由统一流水线维护。
- OpenAI Agents SDK 0.18.3 已于 2026-08-12 在全新 Python 3.12 环境重新安装并通过 6 个离线测试；LangGraph、PydanticAI、LangChain、LlamaIndex、CrewAI、AutoGen 与 Semantic Kernel 保留各自固定版本和隔离实测范围。
- Mock、Fixture 和本地协议测试只证明适配边界与控制逻辑，不代表真实第三方账号联调。

## 项目成熟度

- 项目 1—9 已达到 `service_template`：保留各自领域纵切面，并新增项目级 FastAPI、SQLite Run 状态、幂等、租户权限、预算、取消、SSE 回放、审计、Trace、指标和统一安全 Compose。项目 5、6、9 已进一步补齐 Diff/审批、Outbox/失败恢复、一次性 Git 工作区/循环终止等专项边界；真实 Provider 与操作系统级 Sandbox 仍需外部联调。
- 项目 10 已达到离线 `production_reference`：具备多租户 API、PostgreSQL/SQLite、Redis 恢复队列、身份 Verifier 与数据库 RBAC、租户限定 Worker、短事务租约与崩溃恢复、Agent/Tool/MCP/RAG、Trace/Eval/指标、有限重试、租户 DLQ、重放、取消和一致性备份；真实 OIDC/JWKS、RLS、独立 Worker Deployment 与灾备演练仍待外部验证。
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

- 当前 HTML 全站共有 240 张 Mermaid 图，已经生成 SVG、2x PNG 和内容哈希清单；正式书稿排除网站首页，PDF/EPUB 收录其余 239 张。三种格式均使用预渲染资产，不依赖阅读器现场执行 Mermaid。
- 出版级信息图采用分层视觉体系：A 级核心信息图 12/12、B 级增强信息图 20/20、全章与十项目覆盖图 16/16 已完成；48 张信息图均保留生成式无文字底稿、可编辑 SVG、高分辨率 PNG、中文语义层、图号、长替代文本、图后解释、来源与 SHA-256。38 个正文章节和 10 个项目均有独立出版图，240 张 Mermaid 继续作为精确工程图保留。
- MkDocs HTML 严格构建、断链、缺图、alt、重复 ID 和残留 Mermaid 自动审计已建立。
- 当前本地候选 PDF 为 535 页 A4、约 170 MiB；48 张出版信息图进入同一出版管线，新增正文图代表页 259、280、296、447、467、492 完成栅格化抽查，图片未裁切、未跨页且图题清晰。Noto Sans SC 与 Source Code Pro 固定到上游 commit 并携带 OFL，发行预检硬失败为 0。
- 当前本地 EPUB3 约 127 MiB，出版信息图 PNG 均进入容器且不依赖 JavaScript 渲染；MkDocs HTML、PDF 和 EPUB 已于 2026-08-12 从同一源码重新构建并通过出版审计。
- P7 本地候选 EPUB3 为 13,443,800 字节，具备 nav、spine、严格 XHTML、跨文件片段和资源引用检查；Apple Books 实机与 Calibre 9.13.0 解析引擎复验通过，HTML 下载目录同时包含同次构建的 PDF 与 EPUB。
- GitHub `main` 已合并 P0—P9 仓库范围成果；[GitHub Release v2026.8.1](https://github.com/wujinjun/ai-agent-book/releases/tag/v2026.8.1) 发布完整 HTML 压缩包、454 页 PDF、EPUB3、企业培训 PPTX、发行清单与 SHA-256。
- P7 的 macOS 实机、Calibre 引擎、390/768/1440px 视口与 12 页图稿联系表复验已完成；实体 iOS/Android、商业印刷样张和出版社终审仍由 P9 跟踪。

## 尚未完成

- P1 已完成：16 个核心章节已增加最小实验、工程案例、失败调试、练习答案和深度契约；普通章节扩写继续由后续编辑阶段跟踪。
- P2 已完成并继续扩展：13 个独立示例工程通过目录契约；新增 Browser Safety Lab 已通过全新 Python 3.12 隔离安装、离线运行、6 项直接测试、Ruff 和严格 mypy。第 16、34 章分别达到约 8.9 千和 8.1 千字符，并补齐向量发布验收与浏览器副作用事务。完整三格式出版会在本轮内容批次结束后统一复验。
- 十项目工程复审正在进行：新增 `notes/project-capability-matrix.yml`，以存在的 CLI、API、领域实现、直接测试、Dockerfile、恢复能力、副作用安全与外部缺口逐项约束十个项目。项目 10 已补齐当前 Worker 租约心跳、协作式运行中取消，以及绑定租户、Run、Prompt、Trace、错误类型和尝试次数哈希的一次性限时 DLQ 重放批准；18 项企业平台聚焦测试、Ruff 与 strict mypy 已通过。该机制不等同于线程强杀、真实 OIDC/RLS、独立 Worker 部署或跨区域灾备。
- 内容深化继续覆盖第 25、27 章，两章均达到约 8.9 千字符：数据存储补齐状态所有权、条件写入、Outbox 崩溃窗口、Fencing、删除与恢复；任务队列补齐领取 SQL、未知外部状态对账、共享重试预算、运行中取消边界和受控 DLQ Replay。正文与项目 10 当前实现逐项对照，并明确其尚未实现运行中协作取消、租约心跳和内容绑定的 Replay 再审批。
- 第 24、28 章分别深化至约 9.0 千和 10.0 千字符：FastAPI 服务化补齐 SSE 游标/保留期、慢消费者、WebSocket 鉴权续期、断线取消与稳定错误协议；Observability 补齐可计算 SLI/SLO、Span 状态语义、采样偏差、Telemetry 故障隔离与数据流脱敏，并明确项目 10 的离线事件证据不等于完整 OTel 生产链路。
- 第 6、37 章分别深化至约 9.2 千和 10.3 千字符：Prompt Engineering 补齐有类型上下文契约、Few-shot 污染、端到端间接注入测试和回归分类；从 Demo 到产品补齐服务蓝图、风险分级、产品指标树、诚实降级、上线门禁、SLA 与持续运营责任。
- 第 4、23 章分别深化至约 9.0 千和 10.4 千字符：生成机制补齐稳定 Softmax、过滤顺序差异、可重复性分层、Finish Reason 与 Sampling Lab 证据边界；Python 工程补齐共享 Deadline、结构化并发、取消传播、资源生命周期、Protocol/Adapter 错误契约和测试替身选择。
- 第 26、32 章分别深化至约 9.2 千和 8.7 千字符：部署补齐镜像供应链、Digest/SBOM、Secret 轮换、滚动排空、Expand/Migrate/Contract 与故障注入；Multi-Agent 补齐任务契约、消息幂等、Blackboard 并发冲突、状态指纹终止和单 Agent 净收益门禁。
- 第 3、18 章分别深化至约 9.4 千和 10.0 千字符：Transformer 补齐 Mask 组合、真实复杂度、KV Cache 容量/并发与注意力解释边界；Agents SDK 补齐版本证据链、应用 Runtime 边界、工具事务、Handoff/Guardrail 并发窗口、Session 与 MCP 数据边界。`openai-agents==0.18.3` 已再次在全新 Python 3.12 环境安装并通过离线入口、6 项测试、Ruff 与严格 mypy。
- 第 19、22 章分别深化至约 9.1 千和 9.7 千字符：PydanticAI 补齐类型证据边界、Capability 依赖、ModelRetry 放大、离线/在线证据分层与 FastAPI 错误映射；Multi-Agent 框架补齐等价任务契约、证据深度、状态恢复、上下文经济性、Adapter 锁定风险和独立环境升级门禁。
- 第 21 章深化至约 10.5 千字符，补齐摄取幂等、领域 ACL/版本映射、跨框架分数语义、Query Engine 分层、Callback 隐私、升级回归与退场策略。至此 38 个正文章节均超过 8,000 字符的核心讲义深度门槛；这项内容长度与结构门禁不替代后续十项目生产化复审、技术一致性终审和三格式逐页检查。
- P3 核心范围已完成：版本敏感框架与官方 MCP SDK 均有固定版本和直接实测；真实 Provider、完整 RAG ADR 与升级回归属于后续外部验证。
- P4 核心成熟度目标已完成：十个项目均达到 `service_template`，项目 4、8、10 达到离线 `production_reference`；各项目的真实供应商、规模、灾备与安全验证继续按明确清单跟踪。
- P5 已完成仓库交付：讲师手册、学员实验手册、12 个核心实验、题库、综合考试、评分标准、五类企业案例、三个工作坊、离线 Fixture、环境初始化脚本和 16 页培训幻灯片均已落盘并通过自动门禁；真实班级试讲和学习效果评估进入 P9。
- P6 已完成仓库内审：正式参考资料扩充至 113 条，38 章生成 163 处可追溯引用；外链、术语、代码围栏、远程图片和版本日期通过门禁；教材内容与代码拆分许可，并建立商业许可边界、CLA 和素材核查记录。出版社终审、法律意见和独立技术审稿进入 P9。
- P7 已完成仓库内范围；本轮新增后共 240 张 Mermaid 图，均统一图号与出版资产，过密图已修订，项目 10 真实离线 Trace 截图可复现。HTML 三视口、固定字体 PDF、Apple Books 和 Calibre 均有人工或引擎验收记录；实体移动设备和印刷样张保留到 P9。
- P8 已完成仓库内范围：README 提供经全新 Python 3.12 虚拟环境复验的 15 分钟 Quick Start、网站截图、十项目展示和多格式入口；Issue/PR、安全、兼容、行为与支持政策齐全；断链、密钥、仓库卫生和版本化 Release 校验和门禁通过。GitHub Pages 公网启用与最终附件发布属于 P9。
- P9 仓库范围验收已取得当前源码证据：十项目 CLI 与服务容器均运行，干净 Python 3.12 环境完成测试和三格式出版，三类维护者角色复审、外链、密钥与隐私审计完成。独立外部技术/中文审阅、真实试学、企业试讲和实体设备/印刷不在本次范围内，状态为未验证。

## 当前验证证据

2026-08-12 在 Python 3.12 环境重新运行 Ruff、272 项根级测试、MkDocs 严格构建和 HTML/PDF/EPUB 出版审计，全部通过。发行资产预检无硬失败，仍保留 6 项既有人工权利/设备复核提示。当前 48 张出版信息图及 240 张全站 Mermaid 图的 manifest、章节引用、PNG、SVG 和 SHA-256 均有直接测试；38 个正文章节和 10 个项目均有独立出版图，正式书稿收录 239 张 Mermaid，A4 PDF 为 535 页。新增图页 259、280、296、447、467、492 已进行渲染抽检。更早的十项目容器和隔离框架证据继续见 `notes/p9-project-runtime-qa.md`、`notes/distribution-asset-audit.json` 和 `notes/p9-acceptance.yml`。
