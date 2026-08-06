# Textbook P2 Independent Examples Implementation Plan

> **Execution rule:** implement one example at a time with test-first commits. Do not install mutually conflicting framework stacks into the root environment; use each example's own Python 3.12 virtual environment when dependencies differ.

**Goal:** deliver the 11 independent example projects tracked in `docs/QUALITY_ROADMAP.md`, each runnable without a paid API through deterministic Fixture/Fake adapters and linked bidirectionally with its chapter.

**Architecture:** every example owns a small domain layer, provider protocol, offline adapter, optional online adapter, CLI entry point and direct tests. Root tests validate the shared repository contract; example tests validate behavior. Framework-specific examples use isolated `pyproject.toml` files and lock their tested versions.

**Common contract:**

```text
examples/<name>/
├── README.md
├── pyproject.toml
├── .env.example
├── src/<package>/
│   ├── __init__.py
│   ├── domain.py
│   ├── providers.py
│   └── main.py
└── tests/
    ├── test_happy_path.py
    └── test_failures.py
```

Each README must include purpose, architecture diagram, installation, offline run, optional online run, expected output, tests, failure injection, security boundary, chapter link and extension ideas. No example may contain a real key or silently require network access.

---

## Task 1: Add the independent-example repository contract

**Files:** `tests/test_example_catalog.py`, `notes/example-matrix.yml`, `mkdocs.yml`

- [x] Write a failing test requiring exactly 11 catalog entries and the common files above.
- [x] Require every entry to declare chapter, package, Python version, offline command, test command, dependency group and completion state.
- [x] Add `notes/example-matrix.yml` with all entries `complete: false`.
- [x] Add an Examples index page to MkDocs navigation without linking nonexistent project pages.
- [x] Run the focused test and commit `test: define independent example contract`.

## Task 2: Build `examples/token_counter/`

**Chapter:** 2. **Dependencies:** root-compatible; optional provider tokenizer extra.

- [x] Test budget partitioning, multilingual fixtures, fixed-context rejection and output reservation.
- [x] Implement injectable `Tokenizer`, deterministic whitespace/byte Fake and context budget report.
- [x] Add optional target-model tokenizer adapter only after installing and verifying its exact version.（当前未安装版本敏感依赖，保留明确的 Adapter 端口。）
- [x] Link chapter 2 and mark only this catalog entry complete.
- [x] Run isolated tests and commit `feat: add token counter example`.

## Task 3: Build `examples/attention_demo/`

**Chapter:** 3. **Dependencies:** isolated numerical environment; prefer NumPy, optional plotting extra.

- [ ] Test tensor shapes, softmax row sums, masking and deterministic expected attention weights.
- [ ] Implement scaled dot-product attention and multi-head shape transformation without a deep-learning framework.
- [ ] Generate a small SVG/PNG heatmap from fixed data and explain that it is not model interpretability proof.
- [ ] Link chapter 3, run tests and commit `feat: add attention mechanics example`.

## Task 4: Build `examples/sampling_lab/`

**Chapter:** 4. **Dependencies:** root-compatible.

- [ ] Test temperature validation, top-k/top-p filtering, seeded sampling and stop/max-token termination.
- [ ] Implement a deterministic toy vocabulary distribution; do not pretend it is an LLM.
- [ ] Produce a CSV/Markdown comparison of repeated runs and empirical frequencies.
- [ ] Link chapter 4, run tests and commit `feat: add sampling laboratory`.

## Task 5: Build `examples/local_semantic_search/`

**Chapter:** 5. **Dependencies:** isolated retrieval environment; offline hashed-vector Fake, optional real embedding extra.

- [ ] Test sparse, dense, RRF Hybrid Search, dimension mismatch, ACL and Recall/MRR.
- [ ] Implement versioned documents, Chunk metadata, provider protocol and local index.
- [ ] Add a fixed Chinese/English query set and reproducible evaluation report.
- [ ] Link chapter 5, run tests and commit `feat: add local semantic search example`.

## Task 6: Build `examples/prompt_registry/`

**Chapter:** 6. **Dependencies:** root-compatible.

- [ ] Test immutable versions, variable validation, unsafe interpolation, rollout and rollback.
- [ ] Implement file-backed Prompt specs, content hashes and an offline renderer.
- [ ] Add a regression runner that compares structured Fake outputs across Prompt versions.
- [ ] Link chapter 6, run tests and commit `feat: add prompt registry example`.

## Task 7: Build `examples/structured_extractor/`

**Chapter:** 7. **Dependencies:** root-compatible Pydantic; optional online provider extra.

- [ ] Test valid extraction, missing field, wrong type, partial input, bounded repair and sensitive-data rejection.
- [ ] Implement Pydantic result types, provider protocol, deterministic Fake and stable error taxonomy.
- [ ] Prove retries are bounded and validation errors are not leaked verbatim to untrusted callers.
- [ ] Link chapter 7, run tests and commit `feat: add structured extraction example`.

## Task 8: Build `examples/minimal_agent/`

**Chapter:** 9/17. **Dependencies:** root-compatible and reuse `ai_agent_book.tool_runtime` only through public types.

- [ ] Test direct answer, tool observation, unknown tool, timeout, no progress, cancellation, budget and Checkpoint recovery.
- [ ] Implement `ModelGateway`, `ToolRegistry`, `StateStore`, `Policy`, `Tracer` and `TerminationPolicy` ports with Fake adapters.
- [ ] Add a crash/restart fixture and prove confirmed side effects are not replayed.
- [ ] Link chapters 9 and 17, run tests and commit `feat: add minimal recoverable agent example`.

## Task 9: Build `examples/long_term_memory/`

**Chapter:** 15. **Dependencies:** root-compatible SQLite; optional vector extra isolated.

- [ ] Test write gate, provenance, explicit/inferred conflict, TTL, correction, deletion propagation and cross-tenant denial.
- [ ] Implement versioned Memory records, Fake clock, SQLite store, retrieval filters and tombstone worker.
- [ ] Add user inspect/export/delete CLI flows and ensure audit events omit deleted values.
- [ ] Link chapter 15, run tests and commit `feat: add governed memory example`.

## Task 10: Build `examples/openai_agents_sdk/`

**Chapter:** 18. **Dependencies:** dedicated Python 3.12 environment with a pinned OpenAI Agents SDK.

- [ ] Inspect the installed SDK and official OpenAI documentation before writing API code.
- [ ] Test tools, structured output, handoff/agent-as-tool choice, guardrail, session and tracing with supported Fake/test facilities.
- [ ] Provide an offline-default command; online smoke tests are opt-in and budget-limited.
- [ ] Record exact installed version and check date in `notes/version-check.md`.
- [ ] Link chapter 18, run isolated tests and commit `feat: add tested OpenAI Agents SDK example`.

## Task 11: Build `examples/pydanticai_service/`

**Chapter:** 19. **Dependencies:** dedicated Python 3.12 environment with pinned PydanticAI and FastAPI.

- [ ] Inspect the installed package and official documentation before implementing.
- [ ] Test dependency injection, Tool validation, result validation, bounded retry and service error mapping with the official test model/facility available in that version.
- [ ] Add a FastAPI endpoint and offline integration tests without a paid API.
- [ ] Record exact version/check date, link chapter 19 and commit `feat: add tested PydanticAI service example`.

## Task 12: Build `examples/framework_comparison/`

**Chapter:** 38. **Dependencies:** orchestration only; candidate implementations run in their own environments.

- [ ] Define one research-workflow fixture, golden set, fault cases and weighted criteria before implementing candidates.
- [ ] Compare the native Runtime with the two closest framework candidates; do not require all frameworks merely to fill a table.
- [ ] Collect Task Success, Tool Accuracy, recovery, P95, cost proxy, state export and implementation evidence.
- [ ] Generate a reversible ADR with uncertainty, sensitivity analysis and rollback.
- [ ] Link chapter 38, run comparison tests and commit `feat: add framework comparison spike`.

## Task 13: P2 repository acceptance

- [ ] Mark all 11 catalog entries complete only after their isolated tests pass.
- [ ] Add root orchestration script that creates/reuses isolated environments without combining incompatible locks.
- [ ] Run Ruff/mypy/root tests plus every example's direct test command.
- [ ] Run all examples offline and compare documented expected output.
- [ ] Rebuild index, diagrams, HTML, PDF and EPUB; run publication audit.
- [ ] Update `notes/completion-matrix.md`, `PROJECT_STATUS.md`, `docs/QUALITY_ROADMAP.md` and version records.
- [ ] Commit `feat: complete independent textbook examples` and create the P3 framework-verification plan.

## Acceptance

P2 is complete only when all 11 directories exist, each has an isolated reproducible install, offline execution and direct tests, all chapter links resolve, no online account is required for default CI, and version-sensitive examples record installed versions and official-document check dates. A README-only or placeholder directory does not satisfy the contract.
