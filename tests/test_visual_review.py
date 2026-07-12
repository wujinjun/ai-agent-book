from pathlib import Path

from ai_agent_book.visual_review import (
    audit_markdown_visuals,
    audit_review_ledger,
)


def test_semantic_diagram_with_intro_and_explanation_passes() -> None:
    source = """# Runtime

下图说明请求如何穿过运行循环，以及失败何时进入重试。

```mermaid
%% id: agent-runtime-state-loop
%% title: Agent Runtime 状态循环
%% alt: 请求从接收进入规划和工具执行，失败后有限重试，成功后结束
stateDiagram-v2
    [*] --> Planning
    Planning --> Done
```

从初始态沿箭头阅读；工程上必须给失败重试设置次数和总时限。
"""

    assert audit_markdown_visuals(Path("docs/runtime.md"), source) == []


def test_visual_audit_reports_missing_metadata_and_context() -> None:
    source = """# Runtime

```mermaid
flowchart LR
    A --> B
```

## 下一节
"""

    issues = audit_markdown_visuals(Path("docs/runtime.md"), source)

    assert {issue.code for issue in issues} == {
        "missing-alt",
        "missing-explanation",
        "missing-id",
        "missing-introduction",
        "missing-title",
    }


def test_ledger_checks_minimum_diagrams_and_requirement_disposition(tmp_path: Path) -> None:
    document = tmp_path / "docs/chapter.md"
    document.parent.mkdir()
    document.write_text(
        """# Chapter

下图解释输入如何经过处理阶段并形成最终输出。

```mermaid
%% id: one-flow
%% title: 单一流程
%% alt: 输入经过处理后形成输出并到达成功终态
flowchart LR
    A --> B
```

沿箭头从左向右阅读，图中只有一个处理阶段和一个成功终态。
""",
        encoding="utf-8",
    )
    ledger = tmp_path / "notes/visual-review.yml"
    ledger.parent.mkdir()
    ledger.write_text(
        """version: 1
files:
  docs/chapter.md:
    group: sample
    minimum_diagrams: 2
    requirements:
      - id: one-flow
        section: Chapter
        relation: flow
        disposition: diagram
      - id: missing-decision
        section: Chapter
        relation: decision
        disposition: not-applicable
        reason: ""
""",
        encoding="utf-8",
    )

    issues = audit_review_ledger(tmp_path, ledger, group="sample")

    assert {issue.code for issue in issues} == {
        "diagram-count",
        "missing-reason",
    }
