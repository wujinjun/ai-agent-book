# Publication Redesign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将现有 Markdown 教材改造成 HTML 优先、图形可移植，并可稳定导出专业 PDF 与 EPUB 的出版工程。

**Architecture:** Markdown 与 `mkdocs.yml` 是内容和顺序的权威源；Python 出版模块提取 Mermaid、生成清单并为各目标格式替换图形引用。MkDocs Material 负责在线/离线 HTML，Pandoc 负责出版语义与 EPUB，Chrome Headless 负责将打印 HTML 输出为 PDF。

**Tech Stack:** Python 3.12、MkDocs Material 9.6、PyYAML、BeautifulSoup、Mermaid CLI、Pandoc、Google Chrome Headless、pytest、CSS/JavaScript。

---

## 文件结构

- `src/ai_agent_book/diagram_pipeline.py`：提取 Mermaid、生成稳定 ID、图形清单与替换后的出版 Markdown。
- `src/ai_agent_book/book_manifest.py`：读取 MkDocs 导航并展平为唯一出版顺序。
- `src/ai_agent_book/publication_audit.py`：检查 HTML、SVG/PNG、EPUB 和 PDF 产物契约。
- `scripts/build_diagrams.py`：Mermaid CLI 图形构建入口。
- `scripts/build_html.py`：严格构建 MkDocs 到 `output/html/`。
- `scripts/build_pandoc.py`：组合 Markdown，输出 EPUB3、打印 HTML 与 PDF。
- `docs/assets/stylesheets/extra.css`：三栏文档站、正文、表格、代码、图形和响应式样式。
- `docs/assets/javascripts/reader.js`：锚点、返回顶部、图形灯箱等渐进增强。
- `overrides/home.html`：克制的教材首页模板扩展。
- `templates/pandoc/print.css`：PDF 打印分页与版心。
- `templates/pandoc/epub.css`：EPUB 中文、代码、表格和图片样式。
- `templates/mermaid-config.json`：统一蓝灰图形主题。
- `tests/test_book_manifest.py`、`tests/test_diagram_pipeline.py`、`tests/test_publication_audit.py`：新增出版行为测试。
- `mkdocs.yml`、`pyproject.toml`、`README.md`、`PROJECT_STATUS.md`：接入新管线和操作说明。

### Task 1: 建立唯一出版清单

**Files:**
- Create: `src/ai_agent_book/book_manifest.py`
- Test: `tests/test_book_manifest.py`

- [ ] **Step 1: 编写失败测试**

```python
from pathlib import Path
from ai_agent_book.book_manifest import load_book_entries

ROOT = Path(__file__).parents[1]

def test_manifest_uses_mkdocs_navigation_order() -> None:
    entries = load_book_entries(ROOT / "mkdocs.yml")
    paths = [entry.path.as_posix() for entry in entries]
    assert paths[0] == "docs/index.md"
    assert "docs/part-01-foundations/ch01-what-is-llm.md" in paths
    assert "docs/part-07-advanced/ch38-selection-guide.md" in paths
    assert len(paths) == len(set(paths))
```

- [ ] **Step 2: 运行测试并确认因模块缺失而失败**

Run: `.venv/bin/pytest tests/test_book_manifest.py -v`
Expected: `ModuleNotFoundError: ai_agent_book.book_manifest`

- [ ] **Step 3: 实现清单解析器**

实现不可变 `BookEntry(title: str, path: Path, depth: int)`，使用 `yaml.safe_load` 读取 `docs_dir` 与 `nav`，递归展平字典和列表；文件不存在、路径重复或导航节点类型错误时抛出 `ValueError`。

- [ ] **Step 4: 验证测试通过**

Run: `.venv/bin/pytest tests/test_book_manifest.py -v`
Expected: `1 passed`

- [ ] **Step 5: 提交**

```bash
git add src/ai_agent_book/book_manifest.py tests/test_book_manifest.py
git commit -m "feat: add canonical book manifest"
```

### Task 2: 建立 Mermaid 提取和替换管线

**Files:**
- Create: `src/ai_agent_book/diagram_pipeline.py`
- Create: `tests/test_diagram_pipeline.py`
- Create: `templates/mermaid-config.json`
- Create: `scripts/build_diagrams.py`

- [ ] **Step 1: 编写稳定 ID 与替换行为的失败测试**

```python
from pathlib import Path
from ai_agent_book.diagram_pipeline import extract_diagrams, replace_mermaid

def test_diagram_ids_are_stable_and_markdown_is_replaced(tmp_path: Path) -> None:
    source = "# Runtime\n\n```mermaid\nflowchart LR\nA --> B\n```\n"
    diagrams = extract_diagrams(Path("docs/runtime.md"), source)
    assert diagrams[0].diagram_id.startswith("runtime-")
    assert diagrams == extract_diagrams(Path("docs/runtime.md"), source)
    rendered = replace_mermaid(source, diagrams, Path("assets/diagrams"))
    assert "```mermaid" not in rendered
    assert ".svg" in rendered
    assert "Runtime 图 1" in rendered
```

- [ ] **Step 2: 确认测试失败**

Run: `.venv/bin/pytest tests/test_diagram_pipeline.py -v`
Expected: `ModuleNotFoundError: ai_agent_book.diagram_pipeline`

- [ ] **Step 3: 实现提取、清单和替换**

实现 `DiagramRecord`、基于规范化源码 SHA-256 前 12 位的 ID、Mermaid 围栏扫描、JSON 清单输出和 `<picture>` 替换。替换结果固定为 SVG `source` 与 PNG `img`，包含 alt、图题和来源路径。

- [ ] **Step 4: 实现渲染 CLI**

`scripts/build_diagrams.py` 必须检查 `mmdc`，逐图写入 `assets/diagrams/source|svg|png`，对每个命令设置 30 秒超时；命令失败时报告源 Markdown 和图序号并以非零状态退出。

- [ ] **Step 5: 验证单元测试**

Run: `.venv/bin/pytest tests/test_diagram_pipeline.py -v`
Expected: all tests pass

- [ ] **Step 6: 提交**

```bash
git add src/ai_agent_book/diagram_pipeline.py tests/test_diagram_pipeline.py templates/mermaid-config.json scripts/build_diagrams.py
git commit -m "feat: add portable diagram pipeline"
```

### Task 3: 重设计 MkDocs HTML

**Files:**
- Modify: `mkdocs.yml`
- Create: `docs/assets/stylesheets/extra.css`
- Create: `docs/assets/javascripts/reader.js`
- Create: `overrides/home.html`
- Create: `scripts/build_html.py`
- Create: `tests/test_html_contract.py`

- [ ] **Step 1: 编写 HTML 配置契约的失败测试**

```python
from pathlib import Path
import yaml

ROOT = Path(__file__).parents[1]

def test_mkdocs_loads_reader_assets_and_custom_directory() -> None:
    config = yaml.safe_load((ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    assert config["theme"]["custom_dir"] == "overrides"
    assert "assets/stylesheets/extra.css" in config["extra_css"]
    assert "assets/javascripts/reader.js" in config["extra_javascript"]
    assert "toc.follow" in config["theme"]["features"]
```

- [ ] **Step 2: 确认测试失败**

Run: `.venv/bin/pytest tests/test_html_contract.py -v`
Expected: failure because custom assets are absent

- [ ] **Step 3: 接入主题与三栏版式**

CSS 定义色彩、字号、行高、760–820px 正文、代码块、表格、admonition、图题、首页卡片及 1220/960/720px 响应式规则；深色模式使用对应蓝灰令牌。JS 只做增强，不阻断无脚本阅读。

- [ ] **Step 4: 实现严格 HTML 构建入口**

`scripts/build_html.py` 调用当前解释器的 `mkdocs build --strict --site-dir output/html`，设置 180 秒超时并原样转发错误。

- [ ] **Step 5: 运行配置测试与严格构建**

Run: `.venv/bin/pytest tests/test_html_contract.py -v && .venv/bin/python scripts/build_html.py`
Expected: tests pass; MkDocs exits 0 and writes `output/html/index.html`

- [ ] **Step 6: 提交**

```bash
git add mkdocs.yml docs/assets overrides scripts/build_html.py tests/test_html_contract.py
git commit -m "feat: redesign the HTML reading experience"
```

### Task 4: 增加 HTML 自动审计与视觉抽检

**Files:**
- Create: `src/ai_agent_book/publication_audit.py`
- Create: `tests/test_publication_audit.py`
- Create: `scripts/audit_publication.py`

- [ ] **Step 1: 编写断链、缺失 alt 与 Mermaid 源码检测的失败测试**

```python
from pathlib import Path
from ai_agent_book.publication_audit import audit_html

def test_html_audit_reports_reader_breakages(tmp_path: Path) -> None:
    (tmp_path / "index.html").write_text(
        '<a href="missing/">broken</a><img src="x.png"><code class="mermaid">A--B</code>',
        encoding="utf-8",
    )
    issues = audit_html(tmp_path)
    assert {issue.code for issue in issues} == {"broken-link", "missing-alt", "raw-mermaid"}
```

- [ ] **Step 2: 确认测试失败**

Run: `.venv/bin/pytest tests/test_publication_audit.py -v`
Expected: module/function missing

- [ ] **Step 3: 实现审计器和命令行**

使用 BeautifulSoup 解析站点 HTML，检查内部链接、图片资源、alt、原始 Mermaid、重复 ID 和空标题；CLI 按文件和行号排序输出并在有问题时退出 1。

- [ ] **Step 4: 验证审计测试和真实站点**

Run: `.venv/bin/pytest tests/test_publication_audit.py -v && .venv/bin/python scripts/audit_publication.py html output/html`
Expected: tests pass; real site audit exits 0

- [ ] **Step 5: 使用 Chrome 截取首页和正文的桌面/手机图并人工检查**

Run headless Chrome at 1440×1000 and 390×844 for `index.html` and `part-01-foundations/ch01-what-is-llm/`.
Expected: no overlap, no clipped navigation, readable body, code scrolls horizontally.

- [ ] **Step 6: 提交**

```bash
git add src/ai_agent_book/publication_audit.py tests/test_publication_audit.py scripts/audit_publication.py
git commit -m "test: audit publication HTML"
```

### Task 5: 建立 Pandoc EPUB3 和打印 HTML

**Files:**
- Create: `templates/pandoc/epub.css`
- Create: `templates/pandoc/print.css`
- Create: `templates/pandoc/metadata.yaml`
- Create: `scripts/build_pandoc.py`
- Create: `tests/test_pandoc_pipeline.py`
- Modify: `pyproject.toml`

- [ ] **Step 1: 编写组合顺序与图形替换的失败测试**

```python
from pathlib import Path
from scripts.build_pandoc import compose_book

def test_composed_book_has_ordered_chapters_without_raw_mermaid(tmp_path: Path) -> None:
    output = compose_book(Path("mkdocs.yml"), tmp_path)
    text = output.read_text(encoding="utf-8")
    assert text.index("什么是大语言模型") < text.index("技术选型")
    assert "```mermaid" not in text
```

- [ ] **Step 2: 确认测试失败**

Run: `.venv/bin/pytest tests/test_pandoc_pipeline.py -v`
Expected: import/function missing

- [ ] **Step 3: 实现组合与 Pandoc 调用**

组合器读取出版清单、调整标题层级、替换 Mermaid、保留代码语言，生成 `output/intermediate/book.md`。Pandoc 调用固定 EPUB3、TOC、section div、语法高亮、metadata 与 CSS；缺少 Pandoc 时输出明确安装命令并退出 2。

- [ ] **Step 4: 实现 Chrome Headless PDF**

Pandoc 先生成 `output/intermediate/print.html`；Chrome 使用 `--headless=new --disable-gpu --print-to-pdf-no-header --print-to-pdf=...` 输出 A4 PDF。脚本检查最终文件非空并记录 Pandoc/Chrome 版本。

- [ ] **Step 5: 验证组合测试**

Run: `.venv/bin/pytest tests/test_pandoc_pipeline.py -v`
Expected: all tests pass without requiring external binaries

- [ ] **Step 6: 提交**

```bash
git add templates/pandoc scripts/build_pandoc.py tests/test_pandoc_pipeline.py pyproject.toml
git commit -m "feat: add Pandoc EPUB and PDF pipeline"
```

### Task 6: 校验 EPUB、PDF 和图形产物

**Files:**
- Modify: `src/ai_agent_book/publication_audit.py`
- Modify: `scripts/audit_publication.py`
- Modify: `tests/test_publication_audit.py`

- [ ] **Step 1: 添加 EPUB manifest 与 PDF 基础契约的失败测试**

测试 EPUB 必须包含 nav、spine、SVG 与 PNG manifest 项且 XHTML 不含 Mermaid；PDF 必须可提取书名、目录、首章和末章标题，页数大于 20。

- [ ] **Step 2: 确认新增测试失败**

Run: `.venv/bin/pytest tests/test_publication_audit.py -v`
Expected: missing EPUB/PDF audit functions

- [ ] **Step 3: 实现 ZIP/XHTML/PDF 审计**

EPUB 使用 `zipfile` 与 XML 解析器；PDF 使用 `pypdf.PdfReader`。错误包含产物路径、资源名和契约代码。

- [ ] **Step 4: 执行全部构建和审计**

Run: `.venv/bin/python scripts/build_diagrams.py && .venv/bin/python scripts/build_html.py && .venv/bin/python scripts/build_pandoc.py all && .venv/bin/python scripts/audit_publication.py all output`
Expected: every command exits 0

- [ ] **Step 5: 视觉抽检 PDF/EPUB**

将 PDF 代表页渲染成 PNG，检查封面、目录、代码、表格、图和末页；使用至少两个 EPUB 阅读器检查导航、SVG 与 PNG 回退，并把人工结果记入状态文件。

- [ ] **Step 6: 提交**

```bash
git add src/ai_agent_book/publication_audit.py scripts/audit_publication.py tests/test_publication_audit.py
git commit -m "test: validate EPUB and PDF artifacts"
```

### Task 7: 文档、兼容迁移和最终回归

**Files:**
- Modify: `README.md`
- Modify: `PROJECT_STATUS.md`
- Modify: `scripts/build-pdf.sh`
- Modify: `scripts/build-epub.sh`
- Modify: `.gitignore`
- Modify: `tests/test_publications.py`

- [ ] **Step 1: 将旧脚本改为新管线兼容入口**

两个 shell 脚本分别调用 `.venv/bin/python scripts/build_pandoc.py pdf|epub`；旧 ReportLab/EbookLib 测试改为断言新入口和产物契约，不再接受 Mermaid 源码占位。

- [ ] **Step 2: 更新使用说明和真实状态**

README 写明 HTML、图形、PDF、EPUB 的安装与构建命令、产物路径、外部依赖和故障排查。状态文件分别记录自动验证与仍需人工阅读器验证的项目。

- [ ] **Step 3: 执行 Python 质量门禁**

Run: `.venv/bin/ruff check . && .venv/bin/mypy src scripts && .venv/bin/pytest`
Expected: all commands exit 0

- [ ] **Step 4: 执行出版质量门禁**

Run: `.venv/bin/python scripts/build_html.py && .venv/bin/python scripts/audit_publication.py html output/html`
Expected: strict build and audit exit 0

- [ ] **Step 5: 检查仓库差异和敏感信息**

Run: `git diff --check && ! rg -n 'sk-[A-Za-z0-9_-]{20,}|BEGIN (RSA|OPENSSH) PRIVATE KEY' --glob '!output/**' .`
Expected: no whitespace errors and no secrets

- [ ] **Step 6: 提交**

```bash
git add README.md PROJECT_STATUS.md scripts/build-pdf.sh scripts/build-epub.sh .gitignore tests/test_publications.py
git commit -m "docs: document the publication workflow"
```

## 最终验收

- [ ] `output/html/index.html` 可直接阅读，桌面三栏和移动折叠符合规格。
- [ ] 所有 Mermaid 均存在 SVG 与 2x PNG，且三个出版格式中不出现源码占位。
- [ ] PDF 由 Pandoc 打印 HTML + Chrome Headless 生成，EPUB 由 Pandoc EPUB3 生成。
- [ ] 目录、术语表、参考资料、索引和上下章导航可用。
- [ ] `pytest`、Ruff、mypy、MkDocs strict build 和出版审计均以最新运行结果通过。
- [ ] `PROJECT_STATUS.md` 不把未做的阅读器人工验证标记为完成。
