# 贡献指南

贡献前请先阅读 `PROJECT_STATUS.md` 与 `notes/version-check.md`。正文应使用正式中文，先定义问题与原理，再引入框架；涉及快速变化的 API 必须给出官方来源、依赖版本和核对日期。

提交前运行：

```bash
python -m pytest
ruff check .
mypy src
mkdocs build --strict
```

新章节只有在覆盖章节模板、示例可运行、引用可追溯时，才可以从“部分完成”改为“已完成”。请勿提交密钥、个人数据、未经验证的投资或医疗结论。

