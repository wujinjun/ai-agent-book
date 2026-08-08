# 出版字体资产

本目录只保存 PDF 出版构建所需的固定版本字体。构建脚本通过
`templates/pandoc/print.css` 引用这些文件，避免输出结果随构建机器的系统字体发生变化。
EPUB 当前不嵌入字体，以控制文件体积并尊重阅读器的可访问性设置；PPTX 仍需在交付设备
验证字体替换效果。

| 字体 | 用途 | 固定上游版本 | 许可 |
|---|---|---|---|
| Noto Sans SC Regular/Bold | 中文正文与标题 | `notofonts/noto-cjk@f8d157532fbfaeda587e826d4cd5b21a49186f7c` | SIL Open Font License 1.1，见 `noto-sans-sc/OFL.txt` |
| Source Code Pro Regular/Bold/Italic | 代码与等宽文本 | `adobe-fonts/source-code-pro@803b7e23ec97ae58b6232ea76519a76d428ba268` | SIL Open Font License 1.1，见 `source-code-pro/OFL.md` |

文件校验和与下载来源记录在 `notes/asset-provenance.yml`，自动发行预检会逐个核对。
OFL 允许在遵守许可条件的前提下使用、修改和再分发字体；本清单是工程证据，不替代最终
商业发行合同或专业法律意见。
