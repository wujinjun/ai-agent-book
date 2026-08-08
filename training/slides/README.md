# 培训幻灯片交付说明

`ai-agent-engineering-training.pptx` 是 16:9、16 页的企业培训课件。所有可见文本显式使用
Noto Sans SC，字体文件固定在仓库的 `assets/fonts/noto-sans-sc/`，并携带 SIL Open Font
License 1.1。PPTX 不嵌入字体，因此授课电脑需要在打开 PowerPoint、Keynote 或
LibreOffice Impress 前安装 Regular 与 Bold 两个 OTF 文件。

## 交付前检查

1. 在 macOS 用“字体册”，或在 Windows 用字体文件右键菜单，安装
   `NotoSansSC-Regular.otf` 与 `NotoSansSC-Bold.otf`；关闭并重新打开演示软件。
2. 打开 PPTX 后检查字体替换功能，确认可见文本使用 `Noto Sans SC`，没有缺失字体提示。
3. 逐页播放并重点查看第 2、6、12、16 页：长标题不换行，中文无方框，页码可见，文字
   不越出画布。
4. 将投影比例设为 16:9，关闭“自动替换字体”类选项；在实际投影距离检查 16 pt 正文和
   浅灰卡片的对比度。
5. 讲师备注必须保持可见。16 页备注都包含 `[Sources]` 块，不能使用只保留页面图像、
   删除备注的二次导出件替代原始课件。

如果交付环境不允许安装字体，应先在目标电脑完成替换测试，再导出一次只读 PDF 作为
现场回退版本。不得在未经逐页检查的情况下把字体批量替换为另一字体，因为中文字面宽度
变化可能造成标题换行和正文裁切。

仓库内自动验收包括字体清单、外部运行资源、备注来源块、画布溢出和逐页桌面渲染。
不同 PowerPoint/Keynote 版本、会议室投影和辅助技术仍需要真实设备记录。
