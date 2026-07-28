# GitHub Publication Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the HTML textbook through GitHub Pages and attach PDF/EPUB artifacts to versioned GitHub Releases.

**Architecture:** A single build job produces and audits all formats, uploads a reusable artifact, and feeds two least-privilege deployment jobs. The Pages job runs for `main`; the Release job runs only for `v*` tags.

**Tech Stack:** GitHub Actions, Python 3.12, Node.js 22, MkDocs Material, Mermaid CLI, Pandoc, Chrome Headless, GitHub Pages, GitHub CLI.

---

### Task 1: Publication workflow contract

**Files:**
- Create: `tests/test_github_publication.py`
- Create: `.github/workflows/publish.yml`

- [ ] **Step 1: Write the failing workflow contract test**

```python
from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]


def test_publish_workflow_deploys_pages_and_versioned_downloads() -> None:
    workflow_path = ROOT / ".github/workflows/publish.yml"
    assert workflow_path.is_file()
    workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
    source = workflow_path.read_text(encoding="utf-8")

    assert "main" in workflow[True]["push"]["branches"]
    assert "v*" in workflow[True]["push"]["tags"]
    assert "actions/deploy-pages@v4" in source
    assert "output/html/downloads" in source
    assert "ai-agent-book-2026.pdf" in source
    assert "ai-agent-book-2026.epub" in source
    assert 'gh release create "$GITHUB_REF_NAME"' in source
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -o addopts='' tests/test_github_publication.py -q
```

Expected: failure because `.github/workflows/publish.yml` does not exist.

- [ ] **Step 3: Add the minimal publication workflow**

The workflow must:

1. Trigger on `main`, `v*`, and manual dispatch.
2. Build indices, diagrams, HTML, PDF, EPUB.
3. Run `scripts/audit_publication.py all output`.
4. Copy PDF/EPUB into `output/html/downloads/`.
5. Upload `output/` as a build artifact.
6. Deploy `output/html` with official Pages actions on `main`.
7. Create a release with Runner `gh` on a `v*` tag.

- [ ] **Step 4: Run the contract test and verify GREEN**

Run:

```bash
PYTHONPATH=src .venv/bin/pytest -o addopts='' tests/test_github_publication.py -q
```

Expected: `1 passed`.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/publish.yml tests/test_github_publication.py
git commit -m "ci: publish book site and downloads"
```

### Task 2: Verify and publish

**Files:**
- Modify: none

- [ ] **Step 1: Run local quality gates**

```bash
.venv/bin/ruff check .
.venv/bin/mypy src/ai_agent_book scripts projects/10-enterprise-platform/api.py
PYTHONPATH=src .venv/bin/pytest -o addopts='' tests projects/*/tests -q
```

Expected: all commands exit zero.

- [ ] **Step 2: Verify workflow YAML and Git state**

```bash
.venv/bin/python -c "import pathlib,yaml; yaml.safe_load(pathlib.Path('.github/workflows/publish.yml').read_text())"
git diff --check
git status --short
```

Expected: valid YAML and a clean worktree after commits.

- [ ] **Step 3: Push the forward-only main update**

```bash
git merge-base --is-ancestor origin/main HEAD
git push origin HEAD:main
```

Expected: `main` advances without force.

- [ ] **Step 4: Create and push the first publication tag**

```bash
git tag -a v2026.7.0 -m "AI Agent 从零到实战（2026版）"
git push origin v2026.7.0
```

Expected: GitHub Actions receives both the main and tag events; the tag workflow creates the Release with PDF and EPUB.

- [ ] **Step 5: Verify remote references**

```bash
git ls-remote --heads --tags origin main v2026.7.0
```

Expected: `main` and dereferenced `v2026.7.0^{}` resolve to the publication commit.

