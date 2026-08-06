# Textbook P1 Core Content Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把决定学习效果和工程判断的核心章节从浓缩讲义扩充为包含独立原理、最小实验、工程案例、失败诊断和练习答案的教材章节。

**Architecture:** P1 只扩充 Markdown 正文和内联可运行代码，不提前创建 P2 的独立示例目录。内容按四批推进，每批先增加针对性内容契约，再编辑章节、重建索引和出版产物；章节是否达标由结构、实质主题、代码执行和人工抽检共同判断，不以字数单独判定。

**Tech Stack:** Markdown、Mermaid、Python 3.12、pytest、Pydantic、现有出版管线。

---

## 批次与目标

| 批次 | 章节 | 重点 |
|---|---|---|
| A | 第2、5、8、9、10章 | Token、检索、工具循环、Runtime、规划 |
| B | 第11—15章 | MCP、RAG、Memory |
| C | 第17、20、29、30章 | 原生 Runtime、LangGraph、评估、安全 |
| D | 第36、38章 | 企业架构、框架选型 |

核心章节目标为 8,000—12,000 字符。低于 8,000 字符不自动判失败，但必须由内容矩阵记录原因，并满足所有结构和实验要求。

### Task 1: Add a core-chapter depth contract

**Files:**
- Create: `notes/core-chapter-depth.yml`
- Modify: `tests/test_docs_contract.py`

- [x] **Step 1: Write the failing depth-matrix test**

Add a test that loads `notes/core-chapter-depth.yml` and requires exactly these chapter numbers:

```python
{2, 5, 8, 9, 10, 11, 12, 13, 14, 15, 17, 20, 29, 30, 36, 38}
```

Each entry must define `path`, `target_chars`, `required_sections`, `required_terms`, `code_languages` and `acceptance_experiment`. The test verifies the path exists and `target_chars` is between 8,000 and 12,000.

- [x] **Step 2: Run the test and confirm RED**

```bash
env PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_docs_contract.py::test_core_chapter_depth_matrix_is_complete -q
```

Expected: failure because `notes/core-chapter-depth.yml` does not exist.

- [x] **Step 3: Create the depth matrix**

Record these exact acceptance experiments:

```text
2  上下文预算器对固定指令、历史、检索和输出保留量做拒绝决策
5  同一查询比较关键词、向量和 RRF 混合排序
8  Tool Loop 覆盖未知工具、超时、幂等与审批
9  Runtime 在成功、无进展、预算耗尽和恢复之间转换
10 有规划与无规划方案对比成功、成本和延迟
11 MCP 当前无状态发现、调用与关闭，并对照旧版初始化迁移时序
12 文件路径越界、stdio 日志和结构化错误测试
13 RAG 从解析到引用的可追踪基线
14 基线、Hybrid、Rerank 的逐项消融
15 记忆写入、冲突、过期、删除和跨租户拒绝
17 原生 Runtime 的模型网关、状态和重试边界
20 LangGraph Checkpoint、中断恢复和副作用幂等
29 黄金集、工具准确率、Judge 校准与回归阈值
30 间接注入、数据外泄和过度代理的威胁测试
36 模块化单体到服务拆分的触发条件与数据流
38 同一垂直切片的框架评分和可逆 ADR
```

- [x] **Step 4: Add the content-enforcement test**

For every entry, assert the chapter contains every configured section and term, contains every configured code language, and reaches `target_chars` after its batch is marked `complete: true`. Entries begin with `complete: false`, so the matrix can land before prose changes without weakening completed-batch checks.

- [x] **Step 5: Run and commit the matrix contract**

```bash
env PYTHONPATH=src .venv/bin/python -m pytest tests/test_docs_contract.py -q
git add notes/core-chapter-depth.yml tests/test_docs_contract.py
git commit -m "test: define core chapter depth contract"
```

### Task 2: Expand batch A — context, retrieval and runtime core

**Files:**
- Modify: `docs/part-01-foundations/ch02-token-and-context.md`
- Modify: `docs/part-01-foundations/ch05-embedding.md`
- Modify: `docs/part-02-agent-core/ch08-tool-calling.md`
- Modify: `docs/part-02-agent-core/ch09-agent-runtime.md`
- Modify: `docs/part-02-agent-core/ch10-planning-reflection.md`
- Modify: `notes/core-chapter-depth.yml`
- Test: `tests/test_docs_contract.py`

- [x] **Step 1: Extend chapter 2**

Add distinct sections for tokenizer mechanics, multilingual/token-boundary experiments, context-budget equations, truncation failure analysis, sliding-window/summary/retrieval comparison, a typed Python budgeter, debugging evidence and exercise answers. The budgeter rejects a request when fixed instructions plus reserved output already exceed the model window.

- [x] **Step 2: Extend chapter 5**

Add sparse/dense/hybrid retrieval comparison, cosine edge cases, dimension and model migration, chunk-quality examples, deterministic RRF Python code, Recall/MRR evaluation and a failure case where high semantic similarity returns the wrong authority source.

- [x] **Step 3: Extend chapter 8**

Add a complete inline asynchronous Tool Loop with Pydantic arguments, registry lookup, timeout, structured observation, maximum steps and approval state. Add tables for error classification, retryability and idempotency. Include a timeout-after-write reconciliation case.

- [x] **Step 4: Extend chapter 9**

Add explicit Runtime interfaces, state transitions, termination precedence, no-progress detection, checkpoint contents, recovery semantics and a deterministic Fake Model sequence. Distinguish workflow, router and autonomous loop using the same example request.

- [x] **Step 5: Extend chapter 10**

Add task DAG construction, plan validation, dynamic replanning, Reviewer independence, stopping rules and a quantitative comparison template for no-plan, plan-and-execute and reviewer variants.

- [x] **Step 6: Mark batch A complete and run its contract**

Set `complete: true` for chapters 2, 5, 8, 9 and 10, then run:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest tests/test_docs_contract.py -q
```

- [x] **Step 7: Execute inline acceptance experiments**

Use pytest temporary files to execute the budgeter, RRF and Tool Loop examples; assert budget rejection, stable RRF order and bounded Tool Loop termination. Do not create P2 example directories in this task.

- [x] **Step 8: Commit batch A**

```bash
git add docs/part-01-foundations/ch02-token-and-context.md \
  docs/part-01-foundations/ch05-embedding.md \
  docs/part-02-agent-core/ch08-tool-calling.md \
  docs/part-02-agent-core/ch09-agent-runtime.md \
  docs/part-02-agent-core/ch10-planning-reflection.md \
  notes/core-chapter-depth.yml tests/test_docs_contract.py
git commit -m "docs: deepen context retrieval and runtime chapters"
```

### Task 3: Expand batch B — MCP, RAG and Memory

**Files:**
- Modify: `docs/part-03-rag-and-memory/ch11-mcp.md`
- Modify: `docs/part-03-rag-and-memory/ch12-mcp-server.md`
- Modify: `docs/part-03-rag-and-memory/ch13-rag.md`
- Modify: `docs/part-03-rag-and-memory/ch14-advanced-rag.md`
- Modify: `docs/part-03-rag-and-memory/ch15-memory.md`
- Modify: `notes/core-chapter-depth.yml`

- [ ] **Step 1: Extend chapters 11 and 12**

Add lifecycle request/response examples, capability negotiation, Tool/Resource/Prompt selection, stdio framing, Streamable HTTP trust boundaries, filesystem sandboxing, structured protocol errors and shutdown cleanup. Keep the project labeled as a protocol teaching subset until P3 adds the official SDK.

- [ ] **Step 2: Extend chapter 13**

Add ingestion quality gates, structure-aware chunking, authority metadata, retrieval trace, citation construction, refusal on insufficient evidence and separate retrieval/generation metrics.

- [ ] **Step 3: Extend chapter 14**

Add one baseline dataset and show how Parent-Child, Multi-Query, Hybrid, Reranking and compression change its metrics. Include latency/cost columns and reject strategies without measurable net benefit.

- [ ] **Step 4: Extend chapter 15**

Add memory schemas, write gates, provenance, conflict resolution, TTL, user correction, deletion propagation, retrieval scoring and cross-tenant security tests. Explicitly compare conversation history, RAG corpus, long-term memory and audit log.

- [ ] **Step 5: Mark batch B complete, regenerate the index and verify**

```bash
.venv/bin/python scripts/build_index.py
env PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_docs_contract.py tests/test_publication_metadata.py -q
```

- [ ] **Step 6: Commit batch B**

```bash
git add docs/part-03-rag-and-memory notes/core-chapter-depth.yml docs/book-index.md
git commit -m "docs: deepen MCP RAG and memory chapters"
```

### Task 4: Expand batch C — frameworks, evaluation and security

**Files:**
- Modify: `docs/part-04-frameworks/ch17-native-api.md`
- Modify: `docs/part-04-frameworks/ch20-langgraph.md`
- Modify: `docs/part-05-engineering/ch29-evaluation.md`
- Modify: `docs/part-05-engineering/ch30-security.md`
- Modify: `notes/core-chapter-depth.yml`

- [ ] **Step 1: Extend chapter 17**

Derive a lightweight Runtime from typed ports: `ModelGateway`, `ToolRegistry`, `StateStore`, `Policy`, `Tracer` and `TerminationPolicy`. Include retry ownership and a comparison with framework-managed loops.

- [ ] **Step 2: Extend chapter 20**

Add reducers, persistence identity, checkpoint lifecycle, interrupt/resume payload validation, time-travel limitations, retry policies and external side-effect idempotency using the installed LangGraph version.

- [ ] **Step 3: Extend chapter 29**

Add a versioned golden dataset schema, unit/integration/E2E separation, Task Success and Tool Accuracy examples, retrieval metrics, Judge rubric, inter-rater calibration, confidence intervals and release thresholds.

- [ ] **Step 4: Extend chapter 30**

Add a concrete threat model with assets, actors, trust boundaries and abuse cases. Include direct/indirect injection, exfiltration, SSRF-style tool abuse, excessive agency, sandbox escape assumptions, approval binding and audit evidence.

- [ ] **Step 5: Mark batch C complete and verify installed-version claims**

Only chapter 20 may use `installed_and_tested` for framework-specific behavior in this batch. Run the LangGraph project tests and all content contracts.

- [ ] **Step 6: Commit batch C**

```bash
git add docs/part-04-frameworks/ch17-native-api.md \
  docs/part-04-frameworks/ch20-langgraph.md \
  docs/part-05-engineering/ch29-evaluation.md \
  docs/part-05-engineering/ch30-security.md \
  notes/core-chapter-depth.yml
git commit -m "docs: deepen runtime evaluation and security chapters"
```

### Task 5: Expand batch D — architecture and selection

**Files:**
- Modify: `docs/part-07-advanced/ch36-architecture.md`
- Modify: `docs/part-07-advanced/ch38-selection-guide.md`
- Modify: `notes/core-chapter-depth.yml`

- [ ] **Step 1: Extend chapter 36**

Add a complete enterprise case beginning as a modular monolith. Define module boundaries, ownership, synchronous and event flows, outbox, workflow engine, model gateway, tool registry, memory, evaluation and observability services. State measurable triggers for service extraction and reject premature microservices.

- [ ] **Step 2: Extend chapter 38**

Use one research-workflow vertical slice for native API, OpenAI Agents SDK, PydanticAI and LangGraph decision analysis. Record required capabilities, weighted criteria, uncertainty, spike evidence, lock-in controls and rollback choice. Framework API code remains P3 work unless installed.

- [ ] **Step 3: Mark batch D complete and run the depth contract**

Expected: all 16 configured core chapters satisfy their completed checks.

- [ ] **Step 4: Commit batch D**

```bash
git add docs/part-07-advanced/ch36-architecture.md \
  docs/part-07-advanced/ch38-selection-guide.md \
  notes/core-chapter-depth.yml
git commit -m "docs: deepen architecture and selection chapters"
```

### Task 6: Editorial and publication acceptance for P1

**Files:**
- Modify: `notes/completion-matrix.md`
- Modify: `PROJECT_STATUS.md`
- Modify: `docs/QUALITY_ROADMAP.md`
- Modify: `docs/book-index.md`

- [ ] **Step 1: Review all 16 chapters for duplicated template prose**

Search repeated sentences and identical transitions. Keep the common learning contract but replace quota-driven prose with topic-specific explanations.

- [ ] **Step 2: Verify diagrams by semantic purpose**

For each changed diagram, require stable id, title, alt text, a lead-in sentence and a following interpretation paragraph. Do not add diagrams merely to increase count.

- [ ] **Step 3: Update completion evidence**

Record actual character count, acceptance experiment and remaining gap for every P1 chapter. Check P1 roadmap items only after all 16 core entries use `complete: true`.

- [ ] **Step 4: Regenerate derived pages and diagrams**

```bash
.venv/bin/python scripts/build_index.py
.venv/bin/python scripts/build_diagrams.py --mmdc node_modules/.bin/mmdc
```

- [ ] **Step 5: Run the complete gate**

```bash
.venv/bin/ruff check .
.venv/bin/mypy src/ai_agent_book scripts projects/10-enterprise-platform/api.py
env PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' tests projects/*/tests -q
.venv/bin/python scripts/build_html.py
.venv/bin/python scripts/build_pandoc.py all
env PYTHONPATH=src .venv/bin/python scripts/audit_publication.py all output
```

Expected: all commands succeed with no missing navigation pages, stale metadata or publication issues.

- [ ] **Step 6: Commit P1 acceptance**

```bash
git add docs notes PROJECT_STATUS.md tests assets
git commit -m "docs: complete core chapter depth review"
```

- [ ] **Step 7: Create the P2 implementation plan**

Create `docs/superpowers/plans/2026-08-06-textbook-p2-examples.md` with one independently testable task per missing example directory and explicit dependency isolation.
