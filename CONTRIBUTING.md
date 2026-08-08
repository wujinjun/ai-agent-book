# 贡献指南

贡献前请先阅读 `PROJECT_STATUS.md` 与 `notes/version-check.md`。正文应使用正式中文，先定义问题与原理，再引入框架；涉及快速变化的 API 必须给出官方来源、依赖版本和核对日期。

提交贡献表示你确认拥有相应权利，并同意 [`CONTRIBUTOR_LICENSE_AGREEMENT.md`](CONTRIBUTOR_LICENSE_AGREEMENT.md)。正文、图表、截图或数据必须记录来源和许可；不得把博客改写、模型生成或“网上找到”的材料当作无来源原创。框架名和产品名只作指称性使用，不得暗示官方背书。

提交前运行：

```bash
python -m pytest
ruff check .
mypy src
mkdocs build --strict
python scripts/build_chapter_citations.py --check
```

新章节只有在覆盖章节模板、示例可运行、引用可追溯时，才可以从“部分完成”改为“已完成”。请勿提交密钥、个人数据、未经验证的投资或医疗结论。

建议 commit 使用 DCO 风格签署行：`Signed-off-by: Name <email>`。签署行用于确认提交权利，不替代本协议中对商业发行的明确授权。
