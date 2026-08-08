# 贡献指南

贡献前请先阅读 `PROJECT_STATUS.md`、`docs/QUALITY_ROADMAP.md`、`COMPATIBILITY.md` 与 `notes/version-check.md`。正文应使用正式中文，先定义问题与原理，再引入框架；涉及快速变化的 API 必须给出官方来源、依赖版本和核对日期。

提交贡献表示你确认拥有相应权利，并同意 [`CONTRIBUTOR_LICENSE_AGREEMENT.md`](CONTRIBUTOR_LICENSE_AGREEMENT.md)。正文、图表、截图或数据必须记录来源和许可；不得把博客改写、模型生成或“网上找到”的材料当作无来源原创。框架名和产品名只作指称性使用，不得暗示官方背书。

## 开发环境

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,docs,publish]'
npm ci
```

框架对照和 11 个独立示例拥有彼此隔离的依赖环境；不要为方便而把相互冲突的框架版本合并进根环境。只修改正文时可以先运行相关章节门禁，提交前仍应运行与变更风险相称的完整检查。

## 提交前检查

```bash
.venv/bin/python -m pytest tests projects/*/tests -q
ruff check .
mypy src/ai_agent_book scripts projects/10-enterprise-platform/api.py
python scripts/audit_repository_hygiene.py
python scripts/check_secrets.py
python scripts/build_chapter_citations.py --check
python scripts/build_html.py
PYTHONPATH=src python scripts/audit_visual_review.py
```

修改出版管线、图示、样式、索引或导航时，还要构建 PDF/EPUB 并执行 `PYTHONPATH=src python scripts/audit_publication.py all output`。修改框架/API 时，应在独立 Python 3.12 环境运行对应示例并附版本与源码哈希证据。

新章节只有在覆盖章节模板、示例可运行、引用可追溯时，才可以从“部分完成”改为“已完成”。请勿提交密钥、个人数据、未经验证的投资或医疗结论。

## Pull Request 要求

- 一个 PR 聚焦一个可审阅目标，并说明不在范围内的事项。
- PR 描述列出实际命令和输出，不使用“应该没问题”代替证据。
- 新代码包含成功、失败、超时、权限或恢复路径中的适用测试。
- 新图必须包含稳定 `id`、`title`、`alt` 和图后解释；截图要记录来源、脱敏与生成方式。
- 修订事实时优先引用论文、规范、官方文档或官方仓库，不以低质量博客作为唯一依据。
- 不直接编辑生成的索引、引用或图形资产而不更新其规范源与生成脚本。

维护者可能要求拆分过大的 PR、补充离线 Fixture、降低无界自治、修订版权来源或明确“尚未验证”的边界。内容、代码和出版物的通过状态以自动门禁与人工证据共同决定。

建议 commit 使用 DCO 风格签署行：`Signed-off-by: Name <email>`。签署行用于确认提交权利，不替代本协议中对商业发行的明确授权。
