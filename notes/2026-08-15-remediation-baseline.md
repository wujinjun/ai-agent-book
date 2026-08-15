# 教材整改执行基线

建立日期：2026-08-15
依据：`notes/2026-08-15-book-content-layout-visual-review.md` 与 `notes/2026-08-15-book-remediation-plan.md`

## 状态规则

本文件以现有清单作为唯一资产全集，不复制一份容易失真的 260 项图号列表：

- 章节全集：`docs/part-*/ch*.md`；
- 工程图全集：`assets/diagrams/manifest.json`；
- 信息图全集：`notes/infographic-review.yml`；
- HTML 当前成品：`output/html/`；
- PDF 当前成品：`output/pdf/ai-agent-book-2026.pdf`；
- EPUB 当前成品：`output/epub/ai-agent-book-2026.epub`。

资产状态按下列规则确定。规则覆盖全集，因此每个资产都有唯一当前状态：

1. 工程图若列入“第一优先重绘队列”，状态为 `redesign_required`；其余 manifest 图状态为 `editorial_recheck_required`，不得继续沿用旧 `completed` 结论。
2. 信息图若列入“拆分或重绘队列”，状态为 `split_or_redesign_required`；其余信息图状态为 `format_readability_recheck_required`。
3. 第6—10、14—35章状态为 `structure_rewrite_required`；其余章节状态为 `continuous_reading_recheck_required`。
4. HTML、PDF、EPUB 均为 `publication_rework_required`；构建成功不改变编辑状态。

## 章节批次

| 批次 | 章节 | 当前状态 |
|---|---|---|
| R1-A | 6—10 | `content_rewrite_complete` |
| R1-B | 14—16 | `content_rewrite_complete` |
| R1-C | 17—22 | `content_rewrite_complete` |
| R1-D | 23—31 | `content_rewrite_complete` |
| R1-E | 32—35 | `content_rewrite_complete` |
| 内容复核 | 1—5、11—13、36—38 | `continuous_reading_recheck_required` |

章节只有在总结位于真实章末、二级标题能够表达概念递进、重复摘要完成合并并通过连续阅读后，才可改为 `content_rewrite_complete`。

2026-08-15 更新：R1-A 至 R1-E 已完成结构重编并通过严格 MkDocs 构建；仍需在 R2/R6 连续阅读中删除少量重复定义和统一章首能力主线。项目1—10已建立独立教材章节并进入导航，不再仅依赖项目 README。

## 第一优先工程图重绘队列

以下图状态为 `redesign_required`：

- `agent-product-readiness-gates`；
- `framework-selection-evidence-funnel`；
- `fastapi-request-security-lifecycle`；
- `deployment-schema-expand-contract`；
- `multimodal-rag-main-pipeline`；
- `mcp-server-test-deploy-gates`；
- `structured-output-four-validation-layers`；
- `native-runtime-evolution-path`；
- `agent-product-feedback-release-loop`；
- `embedding-model-index-migration`；
- `autoregressive-token-generation-loop`；
- `agent-latency-critical-path`。

其余工程图在逐张判断前统一为 `editorial_recheck_required`。复核必须给出 `keep`、`merge`、`split`、`redesign` 或 `delete` 中的一项处置，不再使用只表示“成功渲染”的 `completed`。

## 信息图拆分或重绘队列

以下图状态为 `split_or_redesign_required`：

- `generation-control-infographic`；
- `vector-index-migration-infographic`；
- `multimodal-evidence-infographic`；
- `project08-research-workflow-infographic`；
- `agent-security-trust-boundary-infographic`；
- `project09-multi-agent-dev-infographic`；
- `framework-selection-map-infographic`；
- `agent-data-storage-infographic`；
- `tool-permission-execution-infographic`。

其余信息图状态为 `format_readability_recheck_required`。只有 PDF 100% 缩放和 390 px 阅读宽度下的核心文字均可读，且图与相邻 Mermaid 不重复表达，才可改为 `keep`。

## 三格式问题基线

| 格式 | 当前状态 | 必须解决的问题 |
|---|---|---|
| HTML | `publication_rework_required` | 章节目录嵌套、维护页占主导航、复杂图小屏不可读 |
| PDF | `publication_rework_required` | 封面断行、目录过密、前置材料过长、宽图压缩、代码对比度、稀疏尾页 |
| EPUB | `publication_rework_required` | 约128.5 MiB、309张 PNG 占约127.75 MiB、复杂图小屏不可读、层级继承错误 |

## 范围约束

本轮只修改读者可见内容、图稿和出版物。配套软件、示例实现、项目运行时、测试、CI 和外部验证维持现状，除非用户另行授权。
