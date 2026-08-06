from pathlib import Path

from prompt_registry.domain import PromptSpec
from prompt_registry.providers import DeterministicPromptModel
from prompt_registry.registry import FilePromptRegistry


def test_versions_are_immutable_and_rendered_with_validated_variables(tmp_path: Path) -> None:
    registry = FilePromptRegistry(tmp_path)
    spec = PromptSpec.create("support", "1.0.0", "分类工单：{ticket}", ("ticket",))
    registry.publish(spec)

    loaded = registry.load("support", "1.0.0")
    rendered = loaded.render({"ticket": "无法登录"})

    assert loaded.content_hash == spec.content_hash
    assert "<input name=\"ticket\">无法登录</input>" in rendered


def test_rollout_is_stable_and_rollback_restores_previous_version(tmp_path: Path) -> None:
    registry = FilePromptRegistry(tmp_path)
    for version in ("1.0.0", "1.1.0"):
        registry.publish(PromptSpec.create("support", version, "{ticket}", ("ticket",)))
    registry.activate("support", "1.0.0", traffic_percent=100)
    registry.activate("support", "1.1.0", traffic_percent=25)

    selections = [registry.select("support", f"user-{index}") for index in range(100)]

    assert selections == [registry.select("support", f"user-{index}") for index in range(100)]
    assert {selection.version for selection in selections} == {"1.0.0", "1.1.0"}
    registry.rollback("support")
    assert registry.select("support", "any-user").version == "1.0.0"


def test_regression_fake_returns_same_structured_result_for_equivalent_versions(
    tmp_path: Path,
) -> None:
    registry = FilePromptRegistry(tmp_path)
    first = PromptSpec.create("support", "1.0.0", "分类：{ticket}", ("ticket",))
    second = PromptSpec.create("support", "1.1.0", "请分类：{ticket}", ("ticket",))
    registry.publish(first)
    registry.publish(second)
    model = DeterministicPromptModel()

    outputs = [model.run(spec.render({"ticket": "退款失败"})) for spec in (first, second)]

    assert outputs == [{"category": "billing", "confidence": 1.0}] * 2
