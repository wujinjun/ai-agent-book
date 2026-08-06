# Textbook P0 Consistency Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立可信的教材完成度基线，消除失效代码目录、错误项目路径和状态报告过度声明。

**Architecture:** 使用 Markdown 完成矩阵作为人工可读事实源，使用现有 pytest 门禁验证章节数量、项目数量、本地路径和状态声明。正文对未实现示例采用明确的“内联代码已交付、独立工程排入 P2”表述，不创建空目录冒充完成。

**Tech Stack:** Markdown、Python 3.12、pytest、pathlib、正则表达式、Git。

---

### Task 1: Commit the approved design and roadmap

**Files:**
- Create: `docs/superpowers/specs/2026-08-06-textbook-completion-design.md`
- Create: `docs/QUALITY_ROADMAP.md`
- Create: `docs/superpowers/plans/2026-08-06-textbook-p0-consistency.md`

- [ ] **Step 1: Validate the documents contain every stage**

Run:

```bash
for phase in P0 P1 P2 P3 P4 P5 P6 P7 P8 P9; do
  rg -q "## ${phase}" docs/QUALITY_ROADMAP.md
done
```

Expected: exit code 0.

- [ ] **Step 2: Scan the design and roadmap for ambiguous placeholders**

Run:

```bash
rg -n 'T[B]D|待[定]|以后再[说]|适当完[善]' \
  docs/QUALITY_ROADMAP.md \
  docs/superpowers/specs/2026-08-06-textbook-completion-design.md \
  docs/superpowers/plans/2026-08-06-textbook-p0-consistency.md
```

Expected: no matches.

- [ ] **Step 3: Commit the approved planning documents**

```bash
git add docs/QUALITY_ROADMAP.md \
  docs/superpowers/specs/2026-08-06-textbook-completion-design.md \
  docs/superpowers/plans/2026-08-06-textbook-p0-consistency.md
git commit -m "docs: plan textbook quality completion"
```

### Task 2: Add a failing local-code-reference contract

**Files:**
- Modify: `tests/test_docs_contract.py`
- Modify: `docs/part-01-foundations/ch02-token-and-context.md`
- Modify: `docs/part-01-foundations/ch03-transformer-attention.md`
- Modify: `docs/part-01-foundations/ch04-generation.md`
- Modify: `docs/part-01-foundations/ch05-embedding.md`
- Modify: `docs/part-02-agent-core/ch06-prompt-engineering.md`
- Modify: `docs/part-02-agent-core/ch07-structured-output.md`
- Modify: `docs/part-02-agent-core/ch09-agent-runtime.md`
- Modify: `docs/part-02-agent-core/ch10-planning-reflection.md`
- Modify: `docs/part-03-rag-and-memory/ch15-memory.md`
- Modify: `docs/part-04-frameworks/ch18-openai-agents-sdk.md`
- Modify: `docs/part-04-frameworks/ch19-pydanticai.md`
- Modify: `docs/part-04-frameworks/ch21-langchain-llamaindex.md`
- Modify: `docs/part-07-advanced/ch36-architecture.md`
- Modify: `docs/part-07-advanced/ch37-demo-to-product.md`
- Modify: `docs/part-07-advanced/ch38-selection-guide.md`

- [ ] **Step 1: Write the failing path test**

Append to `tests/test_docs_contract.py`:

```python
def test_chapter_code_paths_exist() -> None:
    missing: list[str] = []
    pattern = re.compile(r"`((?:examples|projects|src)/[^` ]+)`")
    for chapter in sorted((ROOT / "docs").glob("part-*/ch*.md")):
        for target in pattern.findall(chapter.read_text(encoding="utf-8")):
            normalized = target.removesuffix("/")
            if not (ROOT / normalized).exists():
                missing.append(f"{chapter.relative_to(ROOT)} -> {target}")
    assert missing == []
```

- [ ] **Step 2: Run the test and confirm the known failures**

Run:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_docs_contract.py::test_chapter_code_paths_exist -q
```

Expected: failure listing the 11 absent example directories and four historical project directory names.

- [ ] **Step 3: Correct real project directory names**

Use these mappings:

```text
projects/08-langgraph-research-agent/    -> projects/08-research-workflow/
projects/08-langgraph-research-workflow/ -> projects/08-research-workflow/
projects/04-enterprise-knowledge-agent/  -> projects/04-knowledge-agent/
projects/10-enterprise-agent-platform/   -> projects/10-enterprise-platform/
```

- [ ] **Step 4: Replace absent example links with honest delivery notes**

For chapters 2—7, 9, 15, 18, 19 and 21, retain the inline runnable snippet and state that the independent example is queued in P2 of `docs/QUALITY_ROADMAP.md`. Do not leave a backticked path to a directory that does not exist.

- [ ] **Step 5: Run the focused test**

Run:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_docs_contract.py::test_chapter_code_paths_exist -q
```

Expected: 1 passed.

- [ ] **Step 6: Commit the reference corrections**

```bash
git add tests/test_docs_contract.py docs/part-*
git commit -m "docs: align chapter code references with repository"
```

### Task 3: Create the chapter and project completion matrix

**Files:**
- Create: `notes/completion-matrix.md`
- Modify: `tests/test_docs_contract.py`

- [ ] **Step 1: Write the failing matrix contract**

Add a test that extracts rows beginning with `| 第` and `| 项目`, then asserts exactly 38 chapter rows and 10 project rows. It must also assert that the matrix defines the state vocabularies `publishable_draft`, `inline_only`, `installed_and_tested`, `vertical_slice` and `production_reference`.

- [ ] **Step 2: Run the matrix contract**

Run:

```bash
env PYTHONPATH=src .venv/bin/python -m pytest \
  tests/test_docs_contract.py::test_completion_matrix_covers_book_and_projects -q
```

Expected: failure because `notes/completion-matrix.md` does not exist.

- [ ] **Step 3: Write all 38 chapter rows**

For each chapter record:正文状态、代码状态、版本状态、出版状态、主要缺口、目标阶段。 Framework chapters that were not installed must use `official_docs_checked`, not `installed_and_tested`.

- [ ] **Step 4: Write all 10 project rows**

Projects 1—9 start at `vertical_slice`; project 10 may use `service_template`. Do not use `production_reference` until P4 acceptance provides the full evidence defined by the design.

- [ ] **Step 5: Run the focused test**

Expected: 1 passed.

- [ ] **Step 6: Commit the matrix**

```bash
git add notes/completion-matrix.md tests/test_docs_contract.py
git commit -m "docs: add honest textbook completion matrix"
```

### Task 4: Rewrite project status around evidence levels

**Files:**
- Modify: `PROJECT_STATUS.md`
- Modify: `README.md`
- Modify: `notes/version-check.md`
- Modify: `tests/test_docs_contract.py`

- [ ] **Step 1: Write a failing status contract**

The test must require these sections in `PROJECT_STATUS.md`: `当前定位`、`正文完成度`、`代码完成度`、`项目成熟度`、`版本核查边界`、`出版完成度` and `尚未完成`. It must require links to `docs/QUALITY_ROADMAP.md` and `notes/completion-matrix.md`.

- [ ] **Step 2: Run the status contract**

Expected: failure listing the missing sections.

- [ ] **Step 3: Rewrite PROJECT_STATUS.md**

Preserve verified evidence such as 107 local tests and multi-format publication, but change the overall label to“可系统学习的出版预览版”. Explicitly record the 11 independent examples, framework installation checks, project production hardening, enterprise training assets, editorial references and commercial licensing as unfinished work.

- [ ] **Step 4: Align README.md**

Replace any statement implying every requested code artifact is complete. Add a visible link to the quality roadmap and completion matrix near the version statement.

- [ ] **Step 5: Update version-check audit metadata**

Keep the actual official-document check date of 2026-07-11. Add a separate repository status audit date of 2026-08-06 so a status edit cannot be mistaken for a fresh API verification.

- [ ] **Step 6: Run the focused and full documentation contracts**

```bash
env PYTHONPATH=src .venv/bin/python -m pytest tests/test_docs_contract.py -q
```

Expected: all tests in the file pass.

- [ ] **Step 7: Commit the status correction**

```bash
git add PROJECT_STATUS.md README.md notes/version-check.md tests/test_docs_contract.py
git commit -m "docs: report textbook maturity by evidence level"
```

### Task 5: Verify P0 and update the roadmap

**Files:**
- Modify: `docs/QUALITY_ROADMAP.md`

- [ ] **Step 1: Run path and residual-language scans**

```bash
rg -n '对应代码目录计划为|当前未实现|待随第二篇示例批次实现' docs/part-* -g 'ch*.md'
```

Expected: no matches.

- [ ] **Step 2: Run the full Python gate**

```bash
.venv/bin/ruff check .
.venv/bin/mypy src/ai_agent_book scripts projects/10-enterprise-platform/api.py
env PYTHONPATH=src .venv/bin/python -m pytest -o addopts='' tests projects/*/tests -q
```

Expected: Ruff and mypy succeed; all tests pass.

- [ ] **Step 3: Build and audit HTML**

```bash
.venv/bin/python scripts/build_html.py
env PYTHONPATH=src .venv/bin/python scripts/audit_publication.py html output
```

Expected: strict MkDocs build and HTML audit succeed.

- [ ] **Step 4: Mark only verified P0 items complete**

Check the eight P0 boxes in `docs/QUALITY_ROADMAP.md`. Leave P1—P9 unchecked.

- [ ] **Step 5: Commit P0 completion**

```bash
git add docs/QUALITY_ROADMAP.md
git commit -m "docs: complete textbook P0 consistency audit"
```

- [ ] **Step 6: Record the next plan**

Create `docs/superpowers/plans/2026-08-06-textbook-p1-core-content.md` only after reviewing P0 evidence and current chapter depth. The P1 plan must name exact chapters, target sections, reference sources and content-specific acceptance tests.
