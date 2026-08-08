# EPUB 设备与兼容性验收

验收日期：2026-08-08

文件：`output/epub/ai-agent-book-2026.epub`

大小：13,391,817 字节

SHA-256：`93291583bc1587dc2100d4910a3ed35f4dd764746998e695264840c37dfcefd8`

## 结论

EPUB3 自动审计通过：76 个 XHTML 文档的本地文件引用、片段锚点、图片资源、替代文本、nav 与 spine 均有效。Apple Books 在当前 macOS 实机中完成目录、双页重排、正文、图示与 Python 代码块人工抽检；图形和代码均正常显示。Calibre 9.13.0 的解析与 HTMLZ 转换引擎完成独立交叉验证，没有 `Referenced file not found`、异常或回溯。

## 设备与阅读路径

| 路径 | 检查内容 | 结果 |
|---|---|---|
| Apple Books / macOS 实机 | 目录、章节跳转、单/双页正文、图、代码块 | 通过 |
| Calibre 9.13.0 转换引擎 | EPUB 解析、清单、XHTML、资源引用 | 通过 |
| 390px 阅读视口 | 单栏重排、图形缩放、代码容器、页面宽度 | 通过；无页面横向溢出 |
| 仓库出版审计 | nav、spine、资源、alt、XHTML 链接与片段 | 通过；0 项问题 |

Calibre 日志中的 `Trimming unused SVG` 表示转换器选择了 `<picture>` 中的 PNG 回退后清理未使用 SVG，不是源 EPUB 缺图。Apple Books 实测已证明正文图形可见。

## 本轮修复

- 将源 Markdown 的跨文档链接改写为稳定文档锚点，仓库外文件改写为 GitHub 链接。
- 在 Pandoc 分割 XHTML 后，将纯片段链接定位到实际目标 XHTML；修复前审计发现 187 个跨文件片段问题，修复后为 0。
- 保留 PNG 回退并嵌入 SVG 源，兼顾 Apple Books 与能力较弱的阅读器。
- 标题锚点改为不可见 HTML span，目录不再显示 `{#doc-…}` 技术文本。

## 边界

Calibre GUI 的完整逐页翻阅未作为通过依据，使用的是其独立解析/转换引擎；移动端为 390px 阅读视口仿真。实体 iPhone、iPad、Android 与不同系统字体的抽检继续列入 P9 外部设备验证，不在本记录中虚构完成。
