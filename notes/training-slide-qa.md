# 培训幻灯片视觉验收记录

验收日期：2026-08-08。验收对象：`training/slides/ai-agent-engineering-training.pptx`，60,416 字节，SHA-256 `cfc281aa33ee40752da69cad9b434ed6f8a21832be83d9cc9b1753af1e1ea644`。

## 验收方法

1. 将最终 PPTX 的 16 页逐页渲染为 1600×900 PNG。
2. 逐页以原始尺寸检查标题换行、正文溢出、边缘裁切、页码、对齐和投影可读性。
3. 运行幻灯片画布溢出检测；最终结果为零溢出。
4. 检查 PPTX 压缩包中 16 个 slide XML 与 16 个 notes XML；每页讲师备注均包含 `[Sources]` 来源块。
5. 生成缩略预览 `docs/assets/training-deck-preview.png`，检查整套叙事节奏与相邻页面轮廓变化。
6. 将 105 个可见文本框统一为 Noto Sans SC；检查模板保真、显式运行字体、16 份讲师备注和 `[Sources]` 块，并使用独立 LibreOffice 渲染器再次输出全部页面。

## 逐页结果

| 页 | 教学任务 | 结果 |
|---:|---|---|
| 1 | 课程定位 | 通过 |
| 2 | 模型能力与系统边界 | 通过 |
| 3 | 三层责任 | 修复英文拆词后通过 |
| 4 | 学习顺序 | 缩短三阶段文案、修复页码后通过 |
| 5 | Context Engineering | 通过 |
| 6 | Tool Calling 执行责任 | 通过 |
| 7 | 工具安全门禁 | 通过 |
| 8 | RAG 完整链路 | 通过 |
| 9 | RAG 与 Memory | 通过 |
| 10 | 框架选型 | 缩短底部文案后通过 |
| 11 | 生产证据 | 通过 |
| 12 | Prompt Injection | 扩展页码区域后通过 |
| 13 | Evaluation | 通过 |
| 14 | 三条学习路线 | 缩短文案、修复页码后通过 |
| 15 | 实验提交证据 | 通过 |
| 16 | 结课行动 | 通过 |

## 字体与可移植性

最终 PPTX 的可见文本运行字体只有 `Noto Sans SC`，未发现 Calibri、Calibri Light 或 Helvetica Neue 的可见运行。文件仍保留 Office 主题和两个空段落的旧回退元数据，但所有有内容的运行都显式指定 Noto Sans SC。字体文件、上游 commit、SHA-256 和 OFL 许可保存在 `assets/fonts/` 与 `notes/asset-provenance.yml`。

PPTX 没有嵌入字体。仓库内检查证明使用当前桌面渲染器时 16 页无溢出、缺字或异常换行，但接收方仍须按 `training/slides/README.md` 安装字体，并在实际 PowerPoint、Keynote 和投影设备上复验。

## 验收边界

本记录证明文件结构和桌面渲染通过，不替代真实会议室投影、不同版本 PowerPoint、Keynote 或无障碍辅助技术的设备验证；这些验证进入 P7 与 P9。
