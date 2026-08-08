# P9 十项目运行与容器验收

核对日期：2026-08-08。核对环境为 macOS、Python 3.12.13、Docker Client/Server 29.4.0。本文只记录本轮实际执行结果，不把 Mock、Fixture 或本地容器外推为真实供应商生产验证。

## 当前源码 CLI

使用 `PYTHONPATH=src .venv/bin/python projects/<项目>/main.py` 逐项运行十个入口，十项退出码均为 0。

| 项目 | 本轮观察到的关键结果 | 结果 |
|---|---|---|
| 1 最小 Assistant | 流式 Delta 与 prompt/completion/total Usage | 通过 |
| 2 天气工具 Agent | 天气工具一次失败后重试成功，再执行温度换算 | 通过 |
| 3 MCP 本地 Agent | initialize、tools/list、system_info；协议版本 2025-11-25 | 通过 |
| 4 企业知识库 | 检索第 9 章内容，返回带 chunk、来源、页码和分数的引用 | 通过 |
| 5 Code Review | 对硬编码凭证产生 high 风险、位置与修复建议 | 通过 |
| 6 自动办公 | 生成日报后停在 `approval_required`，未自动外发 | 通过 |
| 7 股票研究 | 事实、推断、时间和来源分离，包含“不构成投资建议” | 通过 |
| 8 研究工作流 | Reviewer 后产生 Interrupt，批准恢复后完成报告 | 通过 |
| 9 Multi-Agent 团队 | 五角色共享版本状态，以测试和 Review 条件终止 | 通过 |
| 10 企业平台 | 租户化 Run、会话、输出与 Trace ID，状态 `succeeded` | 通过 |

## 干净 Python 环境

在 `/tmp` 创建全新 Python 3.12.13 虚拟环境，安装 `.[dev,docs,publish]` 后执行完整测试、HTML、PDF、EPUB 和出版审计。增加培训课件字体、发行资产、候选清单、祖先关系、最终化差异和干净工作区门禁后的最终套件为 256 项并全部通过，三种出版格式构建与审计通过。该验证不复用项目内 `.venv` 的 site-packages；十项目 CLI 也使用该环境再次运行。

此外重新运行 11 个独立示例的隔离编排。每个示例在独立 Python 3.12 venv 中安装自己的 `pyproject.toml`，依次执行离线入口、直接测试、Ruff 和 mypy；Framework Comparison 还重新执行两个框架 Driver 的 strict mypy 与五轮隔离证据生成。报告 `tmp/p2-example-verification.json` 的 `passed` 为 `true`；该报告属于可再生临时证据，不提交虚拟环境。

## 当前源码容器

基础镜像 `python:3.12-slim` 使用本轮拉取的 digest `sha256:229a2c5bfa27522db7815ea81f9bed70af17ccb9de9fc7ad142b1877b5830d36`。项目 1—9 使用统一安全 Compose 从当前源码构建镜像并启动，端口 8101—8109 的 `/health/ready` 均返回对应项目的 `ready`。项目 10 使用独立 Compose 启动当前源码 API、pgvector PostgreSQL 与 Redis，数据库和 Redis 健康后 `/health/ready` 返回 `ready`。

运行结束后已关闭本教材容器；未操作本机其他项目的容器。

## 本轮捕获并关闭的问题

1. 首次干净构建在生成 Python 包元数据时失败，因为 Dockerfile 复制了 `pyproject.toml`，却没有复制其中声明的 `LICENSE-CODE`。全部项目 Dockerfile 和统一服务 Dockerfile 已修复，并增加契约测试。
2. 首次启动时项目 4、8 因只读根文件系统失败：主数据库已在 `/app/data`，但 Pipeline/Research 子数据库仍回退到 `.data`。Compose 现显式映射全部状态路径到可写卷，并增加配置回归测试。
3. 修复后重新执行完整构建和运行探针，十个项目服务全部通过。

## 最终发布门禁烟测

发布工作流原先允许版本标签沿用 `--allow-partial`，七份外部证据为空时仍可能进入 Release；该路径已改为失败关闭。进一步复审发现，要求证据中的 `source_commit` 等于包含证据本身的 `GITHUB_SHA` 会形成不可执行的 Git 哈希自引用。最终契约现改为：七份记录引用同一冻结候选 commit 和清单哈希；候选必须是标签祖先；候选之后只允许证据、冻结清单与少量状态文件变化，正文、项目、测试或构建代码变化会拒绝发布。P9 状态矩阵仍必须通过 `--require-complete`。

发布包烟测同时验证版本化 PDF、EPUB、培训 PPTX、发行说明、候选清单、SHA-256 和离线 HTML。第一次实测发现 HTML 下载目录可夹带上一轮 PDF/EPUB；打包器现于临时目录强制覆盖本轮文件，回归测试与压缩包内字节哈希均证明嵌套下载和根级产物一致。

## 证据边界

容器验收证明当前源码能够在 Python 3.12 Linux 镜像中安装、启动并响应健康检查。它不证明真实 OpenAI、邮件、行情、GitHub App、OIDC/JWKS、云数据库、生产负载、跨区灾备或正式安全认证；这些能力继续保留在最终缺口矩阵中。
