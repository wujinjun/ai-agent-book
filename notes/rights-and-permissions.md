# 版权、商标与素材核查记录

核查日期：2026-08-08。范围为当前 Git 工作树，不包括外部网站在未来发生的变化。

## 原创与生成资产

正文、练习、项目说明和 Mermaid 源图由本仓库维护。236 张 SVG 与 2x PNG 由仓库内 Mermaid 源码确定性生成，`assets/diagrams/manifest.json` 保存源文件与内容哈希；它们不是从论文或博客复制的插图。培训幻灯片不包含外部照片、论文截图或厂商 Logo，缩略图由最终 PPTX 渲染生成。

代码使用本仓库原创教学实现、标准库和声明的开源依赖。外部框架示例以官方 API 为依据，但不复制大段官方源码。依赖本身继续适用各自许可证，MIT 代码许可不重新授权依赖。

## 引用资料

`notes/references.yml` 收录论文、标准、官方文档和官方仓库的书目信息与链接。仓库只保存引用元数据和独立概述，不镜像论文全文、官方文档全文或外部图片。商业版应再次检查直接引文长度、截图和任何新加入素材。

## 商标

OpenAI、ChatGPT、Claude、Anthropic、LangChain、LangGraph、LlamaIndex、Pydantic、CrewAI、AutoGen、Semantic Kernel、Docker、PostgreSQL、Redis、GitHub、Notion、飞书及其他名称可能是各自权利人的商标。本书只为技术识别、比较和互操作说明而使用这些名称，不暗示赞助、认证或背书。封面、营销页和付费课程不得把第三方 Logo 作为主视觉，除非获得明确许可。

## 字体与出版工具

PDF 构建固定使用仓库内的 Noto Sans SC 与 Source Code Pro，不再依赖构建机器上的 PingFang、Hiragino 或 Menlo。五个字体文件都固定到上游 commit、保存 SHA-256，并携带 SIL Open Font License 1.1；来源、许可文件和用途见 `assets/fonts/README.md` 与 `notes/asset-provenance.yml`。发行预检核对字体文件、许可文件、CSS 引用、PDF 字体嵌入/轮廓化状态及未批准系统字体，机器报告位于 `notes/distribution-asset-audit.json`。

EPUB 不嵌入字体，以避免显著增加文件体积，并允许阅读器采用用户可访问性设置；因此仍需在目标商店和实体设备测试系统字体替换。培训 PPTX 使用系统字体且不嵌入字体，进入商业发行包前仍需验证 PowerPoint、Keynote 和投影设备上的替换效果。工程清单不能替代对最终合同、OFL 通知方式及印厂要求的专业审核。

## 当前结论与保留项

- 开源内容、代码和商业版的许可边界已拆分，见 `LICENSE`、`LICENSE-CODE` 和 `COMMERCIAL_LICENSE.md`。
- 外部贡献进入商业版前需要接受 CLA 或另行授权。
- 当前未发现 Markdown 中直接嵌入的远程第三方图片；外链只作为引用或文档入口。
- PDF 的固定 OFL 字体、EPUB/PPTX 远程运行资源、源图片来源、页面盒和直接依赖许可元数据均已进入自动发行预检；当前硬失败为 0，人工复核项保留在报告中。
- 当前核查不是法律意见。商业合同、封面、ISBN 版 PDF/EPUB、字体和营销素材仍需出版社或法律顾问作最终核验。

P9 的独立商业权利核查使用 `external-validation/rights-review-protocol.md` 和对应 YAML 模板。仓库只保存匿名结论、目标 commit 和受控原件引用；法律意见正文及审阅者身份保存在私有档案。
