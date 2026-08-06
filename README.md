# AI Agent 从零到实战：原理、工程与项目（2026版）

这是一套面向软件工程师的中文技术教材工程。它不把 Agent 等同于某个框架，也不把能调用一次模型的脚本包装成生产系统；全书从 LLM 的生成机制出发，依次讨论结构化输出、工具调用、MCP、RAG、Memory、工作流、多 Agent，以及测试、部署、可观测性和安全治理。

> 当前版本为 **0.2.0 / 多格式出版预览版**。第 1—38 章、十个教学型项目和新版 HTML/PDF/EPUB 出版管线均已建立，但独立示例、框架实测、生产强化、培训材料和商业出版编辑仍在进行。真实进度见 [`PROJECT_STATUS.md`](PROJECT_STATUS.md)，逐项状态见 [`notes/completion-matrix.md`](notes/completion-matrix.md)，后续路线见 [`docs/QUALITY_ROADMAP.md`](docs/QUALITY_ROADMAP.md)。

## 适合与不适合的读者

本书适合有后端、嵌入式、架构或 CI/CD 经验，能阅读 Python，但尚未系统学习 LLM 与 Agent 的工程师。它也适合需要评估 Agent 技术选型的架构师和技术负责人。

如果你只想复制几段 Prompt、寻找“万能框架”，或期待不理解数据与权限边界就直接上线自治 Agent，本书并不合适。读者应愿意运行代码、阅读日志、设计失败路径并完成练习。

## 学习目标

完成课程后，读者应能解释模型、产品、框架与工程系统的区别；独立实现工具调用循环和 RAG 链路；根据确定性、状态持久化与协作需求选择原生 API、OpenAI Agents SDK、PydanticAI 或 LangGraph；并为 Agent 建立测试、评估、部署、监控、权限和成本控制。

## 技术栈

教材默认 Python 3.12，使用 Pydantic、httpx、FastAPI、PostgreSQL、Redis、pgvector、Docker、pytest、Ruff、mypy 与 MkDocs Material。出版工具使用 Mermaid CLI 11.4.2、Pandoc 3.x 与 Chrome Headless。框架章节覆盖原生 API、OpenAI Agents SDK、PydanticAI、LangGraph、LangChain、LlamaIndex、CrewAI、AutoGen 与 Semantic Kernel，但不会将其中任何一个描述为唯一答案。

## 完整目录

1. 第一篇：LLM 与 AI Agent 基础（第 1—5 章）
2. 第二篇：Prompt、工具与 Agent 核心机制（第 6—10 章）
3. 第三篇：MCP、RAG 与 Memory（第 11—16 章）
4. 第四篇：Agent 框架（第 17—22 章）
5. 第五篇：Agent 工程化（第 23—31 章）
6. 第六篇：十个完整项目实战
7. 第七篇：高级主题与技术选型（第 32—38 章）

逐章主题见[教材首页](docs/index.md)。

## 推荐学习路线

- 想快速做出可靠原型：先学第 1、2、4、6—9、17、23—24、29—30 章，再完成项目 1—2。
- 想建设企业知识库：在上述基础上学习第 5、13—16、25、28—31 章，再完成项目 4。
- 想设计复杂工作流：继续学习第 10、20、22、27、32、36—38 章，再完成项目 8—10。

完整的 8 周、12 周和 24 周安排见[学习指南](docs/learning-guide.md)。

## 8 周与 12 周计划概览

8 周路线以每周 8—10 小时完成两个可展示项目为目标；12 周路线增加 MCP、RAG、LangGraph、评估与部署，最终完成一个带引用、权限与追踪的工程项目。每周检查标准和产出在学习指南中列出。

## 安装环境

```bash
cd ai-agent-book
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev,docs]'
cp .env.example .env
```

核心测试使用本地 Mock，不需要 API Key。只有明确标记的在线示例才读取供应商密钥。

## 运行代码与测试

```bash
python -m pytest
python -m examples.tool_runtime.main
ruff check .
mypy src
```

每个独立示例包含自己的 README、环境示例与测试入口。预期输出不是固定文案时，README 会说明应观察的状态和字段。

## 启动文档网站

```bash
npm ci
python scripts/build_index.py
python scripts/build_diagrams.py --mmdc node_modules/.bin/mmdc
python scripts/build_html.py
python -m http.server 8000 --directory output/html
```

浏览器访问 `http://127.0.0.1:8000`。新版 HTML 是三栏开发者文档布局；Mermaid 在构建时预渲染为 SVG 与 2x PNG，因此离线阅读不依赖 Mermaid JavaScript 或外部 CDN。开发时仍可使用 `mkdocs serve` 快速预览原稿，但正式产物必须运行上述脚本。

## 生成 PDF 与 EPUB

先安装 Node.js 22、Pandoc 3.x 和 Google Chrome/Chromium。macOS 可运行：

```bash
brew install pandoc
npm ci
```

然后生成图形与出版产物：

```bash
python scripts/build_diagrams.py --mmdc node_modules/.bin/mmdc
python scripts/build_index.py
./scripts/build-pdf.sh
./scripts/build-epub.sh
PYTHONPATH=src python scripts/audit_publication.py all output
```

产物写入：

- `output/html/`：可离线部署的 MkDocs HTML；
- `output/intermediate/print.html`：Pandoc 生成的独立打印 HTML；
- `output/pdf/ai-agent-book-2026.pdf`：Pandoc 打印 HTML 经 Chrome 输出的 A4 PDF；
- `output/epub/ai-agent-book-2026.epub`：带 SVG 首选图和 PNG 回退的 EPUB3。

如果图形未变化，构建器会按内容哈希复用缓存。缺少 Mermaid CLI、Pandoc、Chrome 或字体时，脚本会明确退出，不会退回旧 ReportLab 文本版或把 Mermaid 源码放进 EPUB。

## 贡献与版本说明

贡献规则见 [`CONTRIBUTING.md`](CONTRIBUTING.md)，版本变化见 [`CHANGELOG.md`](CHANGELOG.md)，版本敏感接口见 [`notes/version-check.md`](notes/version-check.md)。2026 版表示教材维护目标年份，不表示所有外部 API 在全年保持不变；每个敏感章节必须记录独立核对日期。
