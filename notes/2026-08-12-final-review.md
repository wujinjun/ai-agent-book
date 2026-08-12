# 2026-08-12 内容、项目与出版终审增量

本记录只描述 2026-08-12 当前仓库可复现的增量证据，不替代独立外审、真实学员试学、企业试讲、实体印刷或专业法律意见。

## 内容与版本

- 38 章均达到至少 5,000 字符的内容门禁；第 33、35 章分别扩展到约 8.9 千字符，增加最小实验、工程案例、失败分析、图示与练习答案。
- `openai-agents==0.18.3` 在全新 Python 3.12 隔离环境重新安装，包自省确认版本，6 个离线测试通过；OpenAI Developer Platform 与 SDK 专站的证据范围分开记录。
- 编辑审计覆盖 38 章、113 条正式资料和 163 处章节引用；未发现远程第三方图片、未闭合代码围栏或正文 TODO。

## 项目工程

- 项目 5：Diff 预算、Webhook HMAC 验签/持久去重、绑定仓库/PR/提交/报告的限时审批。
- 项目 6：内容与目标绑定的持久限时审批、租约 Outbox、稳定幂等键、失败重试和跨进程恢复。
- 项目 9：一次性本地 Git 克隆、补丁路径与规模策略、失败销毁、白名单测试、状态指纹循环终止和单 Agent 基线。
- 项目 10：修复 Worker 跨租户领取风险，增加短事务 worker lease、过期租约恢复和迟到结果覆盖保护。

真实 OAuth/OIDC、外部 Provider、PostgreSQL RLS、操作系统级恶意代码 Sandbox、跨区域灾备和生产流量不在仓库测试范围内，继续明确标记为未验证。

## 图形与出版

- A 级核心信息图 12/12、B 级增强信息图 20/20；HTML 全站 Mermaid 240 张，正式 PDF/EPUB 书稿排除网站首页并收录 239 张。
- 所有 Mermaid manifest 记录具有唯一 `diagram_id`、资源路径和全局唯一 `semantic_id`；SVG、2x PNG 与源文件均存在。
- 新增的项目 6 Outbox、项目 9 工作区、第 33 章 Patch 事务和第 35 章多模态证据图完成 A4 栅格化抽检。项目 9 横向初稿因标签过小被拒绝，改为纵向后通过。
- HTML、517 页 A4 PDF 与 EPUB3 从同一原稿重建；PDF SHA-256 为 `66662e9c4ada16400e435d6b8835be4d18f76cc901fe186275103410b7601180`，EPUB SHA-256 为 `024b7afa235759e1147fbfce83d94284e5ba0112dceefc564a2594e047f929b8`。

## 自动门禁

- Python 3.12：Ruff 通过，269 项 pytest 通过，MkDocs strict 通过。
- Publication、Editorial、Privacy、Repository Hygiene、Visual Review 全部通过。
- Distribution preflight：`hard_issues=0`；6 项人工提示仍属于既有权利/设备复核边界。
