# 变更记录

## Unreleased - 2026-08-12

- 深化第 16 章向量数据库与第 34 章 Browser Agent：增加过滤后 Recall、权限泄漏、Freshness、删除延迟、可回滚索引发布、内容绑定审批、业务幂等和动作后验证。
- 新增第 13 个独立示例 Browser Safety Lab；在全新 Python 3.12 venv 中通过离线入口、6 项 pytest、Ruff 与严格 mypy，不访问真实浏览器、网络或账号。
- 深化第 25 章数据存储与第 27 章异步任务：增加状态所有权、Fencing、Outbox 崩溃窗口、删除恢复、领取 SQL、未知副作用对账、共享重试预算与受控 DLQ Replay，并明确项目 10 的当前实现边界。
- 深化第 24 章 FastAPI 服务化与第 28 章 Observability：增加 SSE 恢复和背压、WebSocket 长连接安全、断线/取消竞态、稳定错误协议、可计算 SLI/SLO、Span 状态、采样偏差、Telemetry 故障隔离与隐私数据流。
- 深化第 6 章 Prompt Engineering 与第 37 章从 Demo 到产品：增加有类型上下文契约、Few-shot 污染、端到端注入验收、服务蓝图、风险分级、产品指标树、降级路径与上线运营门禁。
- 深化第 4 章生成机制与第 23 章 Python 工程：增加数值稳定、解码过滤顺序、可重复性层级、结束原因、共享 Deadline、结构化并发、取消传播、资源关闭和 Protocol/Adapter 测试边界。
- 深化第 26 章 Docker 部署与第 32 章 Multi-Agent 原理：增加容器供应链、Secret 轮换、滚动排空、Schema 迁移、故障注入、任务契约、Blackboard 冲突、可判定终止与净收益门禁。
- 深化第 7 章 Structured Output：增加 Candidate/Validated/Committed 事务边界、错误责任分类、Schema 兼容矩阵、与离线抽取器的能力边界对照及练习参考答案，正文增至约 8.4 千字符。
- 深化第 31 章成本与性能：增加单位成功任务成本、关键路径、重试放大、权限版本缓存、Run deadline、性能实验矩阵和练习答案，正文增至约 9.2 千字符。
- 新增第 12 个独立示例 Cost/Latency Lab；在全新 Python 3.12 venv 中通过离线入口、7 项 pytest、Ruff 与严格 mypy，不写死模型价格或伪造真实性能数据。

- 完成出版信息图升级：A 级核心图 12/12、B 级增强图 20/20、全章与十项目覆盖图 16/16；本轮内容与项目增强后保留 240 张 Mermaid 作为精确工程图。
- 为上下文、生成控制、Embedding、Prompt Injection、Structured Output、Tool 权限、规划、MCP Server、高级 RAG、向量索引、原生 Runtime、Agents SDK、Agent API、存储、部署、队列、评估、成本、Browser Agent 和技术选型增加出版级信息图。
- 48 张信息图统一生成可编辑 SVG 与高分辨率 PNG，并补齐 manifest、SHA-256、来源、提示词台账、图号、长替代文本和图后解释；38 章和 10 个项目均有独立出版图。
- 重新构建并验收 MkDocs HTML、535 页 A4 PDF 与 EPUB3；Ruff、272 项测试、严格文档构建、出版和发行资产审计通过，并抽检新增图页 259、280、296、447、467、492。
- 项目 5 增加 Diff 审查预算、Webhook HMAC 验签与持久 delivery 去重，以及绑定仓库、PR、提交 SHA、报告哈希和有效期的评论审批令牌。
- 项目 6 增加持久内容/目标绑定审批、限时令牌、租约 Outbox、稳定幂等键、失败重试与跨进程恢复，并明确不支持幂等键的远端系统仍需结果对账。
- 项目 9 增加一次性 Git 克隆、补丁路径与规模策略、失败销毁、白名单测试执行、状态指纹循环终止和同任务单 Agent 成本基线，并明确进程边界不等于恶意代码 Sandbox。
- 项目 10 修复 Worker API 的跨租户领取风险，增加短事务 `worker_id` 租约、过期租约崩溃恢复和迟到结果覆盖保护。
- 内容终审将第 33、35 章扩展至约 8.9 千字符，补齐工作区 Patch 事务、多模态证据回溯、失败分析和练习答案；全章最低内容门禁提高到 5,000 字符。
- 在全新 Python 3.12 隔离环境重新安装并验证 `openai-agents==0.18.3`，6 个离线 SDK 测试通过，并记录 OpenAI 平台文档与 SDK 专站各自的证据边界。

## v2026.8.1 - 2026-08-08

- P7：完成 235 张图的作用域图号、联系表复审、真实离线 Trace 截图，以及 447 页 PDF、EPUB 跨 XHTML 链接、Apple Books、Calibre 与三视口验收。
- P8：重写 15 分钟 Quick Start 与十项目展示，增加网站截图、兼容/安全/行为政策、Issue/PR 模板、密钥与仓库卫生门禁，以及带变更摘要和 SHA-256 的确定性 Release 打包器。
- P9：发行预检加入直接与传递依赖许可证闭包；移除未被正式出版入口使用的 EbookLib/旧 EPUB 生成路径，正式 EPUB 统一由 Pandoc EPUB3 管线生成。
- P9：增加默认失败关闭的外部验收执行包生成器，自动绑定候选 commit、产物校验和及七份匿名证据模板。
- P9：发布 [`p9-candidate-e5ffef0`](https://github.com/wujinjun/ai-agent-book/releases/tag/p9-candidate-e5ffef0) 预发布执行包，供独立外审、试学、试讲和实体设备核验使用；它替代存在 Linux CI 缺陷的 `p9-candidate-034ac18`，但不替代正式版本。
- P8/P9：启用 [GitHub Pages 在线阅读预览](https://wujinjun.github.io/ai-agent-book/)，并实测首页、PDF 与 EPUB 下载入口；站点仍明确标记为候选预览。
- P9：按维护者范围决定完成仓库内验收；七类真人或专业外部活动改为明确排除且未通过，版本标签改为验证 `complete_repository_scope`，避免把范围缩减伪装成外部背书。
- 发布 454 页 PDF、EPUB3、离线 HTML、企业培训 PPTX、发行清单与 SHA-256；本版本声明范围为仓库验证，不包含七类外部背书。
- 修复 Release job 在未 checkout 仓库时缺少 `GH_REPO` 的问题；v2026.8.1 首次附件已从同一通过门禁的 Actions 产物恢复发布。

## v2026.8.0 - 2026-08-08

- 完成 38 章正文、逻辑关系、图表与多格式版式复审，生成 227 组 Mermaid SVG 与 2x PNG 资产。
- 完成 11 个独立可运行示例；十个项目均达到 `service_template`，项目 4、8、10 达到离线 `production_reference`。
- 在 Python 3.12.13 下通过 Ruff、mypy、206 项根级测试、MkDocs 严格构建与出版审计。
- 发布 HTML 完整包、400 页 PDF、EPUB3 与 SHA256 校验文件：[GitHub Release v2026.8.0](https://github.com/wujinjun/ai-agent-book/releases/tag/v2026.8.0)。

## 0.1.0 - 2026-07-10

- 建立七篇、38 章的教材信息架构。
- 完成第一章第一节“什么是大语言模型？”初稿。
- 加入离线工具调用运行时、测试与 MkDocs 构建配置。
- 建立版本核查与项目状态治理机制。
