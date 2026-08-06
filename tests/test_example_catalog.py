from pathlib import Path

import yaml


ROOT = Path(__file__).parents[1]
CATALOG = ROOT / "notes/example-matrix.yml"

EXPECTED_EXAMPLES = {
    "token_counter",
    "attention_demo",
    "sampling_lab",
    "local_semantic_search",
    "prompt_registry",
    "structured_extractor",
    "minimal_agent",
    "long_term_memory",
    "openai_agents_sdk",
    "pydanticai_service",
    "framework_comparison",
}
REQUIRED_FIELDS = {
    "name",
    "chapter",
    "package",
    "python",
    "offline_command",
    "test_command",
    "dependency_group",
    "complete",
}


def load_catalog() -> list[dict[str, object]]:
    assert CATALOG.is_file()
    document = yaml.safe_load(CATALOG.read_text(encoding="utf-8"))
    assert document["schema_version"] == 1
    return document["examples"]


def test_catalog_declares_exactly_the_planned_examples() -> None:
    examples = load_catalog()
    assert len(examples) == 11
    assert {entry["name"] for entry in examples} == EXPECTED_EXAMPLES

    for entry in examples:
        assert REQUIRED_FIELDS <= entry.keys()
        assert isinstance(entry["chapter"], (int, list))
        assert entry["python"] == ">=3.12,<3.13"
        assert str(entry["offline_command"]).strip()
        assert str(entry["test_command"]).strip()
        assert entry["dependency_group"] in {"root", "isolated", "framework"}
        assert isinstance(entry["complete"], bool)


def test_completed_examples_satisfy_the_repository_contract() -> None:
    failures: list[str] = []
    for entry in load_catalog():
        if not entry["complete"]:
            continue

        root = ROOT / "examples" / str(entry["name"])
        package = root / "src" / str(entry["package"])
        required = (
            root / "README.md",
            root / "pyproject.toml",
            root / ".env.example",
            package / "__init__.py",
            package / "domain.py",
            package / "providers.py",
            package / "main.py",
            root / "tests" / "test_happy_path.py",
            root / "tests" / "test_failures.py",
        )
        missing = [str(path.relative_to(ROOT)) for path in required if not path.is_file()]
        if missing:
            failures.append(f"{entry['name']}: {', '.join(missing)}")

    assert failures == []


def test_examples_index_is_in_the_documentation_navigation() -> None:
    index = ROOT / "docs/examples/index.md"
    assert index.is_file()
    source = index.read_text(encoding="utf-8")
    assert "# 独立示例工程" in source

    config = (ROOT / "mkdocs.yml").read_text(encoding="utf-8")
    assert "独立示例: examples/index.md" in config
