# 兼容性与升级策略

## 支持基线

| 范围 | 支持级别 | 说明 |
|---|---|---|
| Python 3.12.x | 完整支持 | 教材、根测试、十项目和独立示例的验收基线 |
| Python 3.13+ | 未承诺 | 依赖兼容后才进入矩阵，不以“可以安装”代替全量验证 |
| Python 3.11 及以下 | 不支持 | 不接受为兼容旧解释器而降低类型、安全或异步设计的修改 |
| macOS / Ubuntu | 构建支持 | macOS 用于 Apple Books、Chrome 与本地开发；Ubuntu 用于自动门禁 |
| Windows / WSL2 | 社区验证 | 接受附完整复现环境的修复，不虚构为持续验证平台 |

核心离线示例不需要 API Key。真实模型、GitHub、邮件、日历、行情和办公系统属于可选 Adapter；接口契约可在 MockTransport 或 Fixture 中验证，但供应商端到端能力只有在单独记录账号、区域、日期、版本和结果后才算外部验证。

## 出版工具

- Node.js 22 与仓库锁定的 Mermaid CLI 用于 SVG/2x PNG。
- Pandoc 3.x 与 Chrome/Chromium 用于 PDF、EPUB 和打印 HTML。
- MkDocs Material 的精确版本由 `pyproject.toml` 固定。
- Apple Books/macOS 与 Calibre 9.13.0 已完成 P7 抽检；实体 iOS/Android 与商业印刷样张由 P9 跟踪。

没有 Pandoc、Chrome 或 Mermaid CLI 时，发布脚本会失败并指出缺失工具，不会静默回退到旧制品。

## 框架版本

框架实测版本、核对日期和未验证能力以 [`notes/version-check.md`](notes/version-check.md) 与 [`notes/example-matrix.yml`](notes/example-matrix.yml) 为准。章节中的“支持”分为三层：

1. `documented`：官方文档或规范明确描述；
2. `locally_verified`：固定版本在 Python 3.12 环境直接运行；
3. `externally_validated`：真实供应商或生产相邻环境验证。

低层证据不能冒充高层。升级框架时必须更新固定版本、官方来源、最小实测、失败路径和版本核查日期，并运行对应独立环境，不能只修改文案。

## 兼容性变更流程

- 补丁更新：修复错误，不改变教材示例的公共契约。
- 教材小版本：允许增加章节、示例或可选字段；迁移说明写入 `CHANGELOG.md`。
- 破坏性变更：必须提供迁移说明、替代路径和至少一个发行周期的弃用提示。
- 被上游弃用的接口：先在 `notes/version-check.md` 标记，再修订代码与正文；未经实测不得宣称迁移完成。

报告兼容问题时请使用“框架/API 版本核查”Issue 模板，并附 Python、操作系统、精确依赖版本、最小复现和官方来源。
