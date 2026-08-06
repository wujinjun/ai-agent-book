from pathlib import Path

import pytest

from prompt_registry.domain import PromptSpec
from prompt_registry.registry import FilePromptRegistry


def test_publish_cannot_overwrite_an_existing_version(tmp_path: Path) -> None:
    registry = FilePromptRegistry(tmp_path)
    spec = PromptSpec.create("support", "1.0.0", "{ticket}", ("ticket",))
    registry.publish(spec)

    with pytest.raises(FileExistsError):
        registry.publish(spec)


def test_missing_extra_and_unsafe_fields_are_rejected() -> None:
    spec = PromptSpec.create("support", "1", "{ticket}", ("ticket",))
    with pytest.raises(ValueError, match="变量"):
        spec.render({})
    with pytest.raises(ValueError, match="变量"):
        spec.render({"ticket": "x", "secret": "y"})
    with pytest.raises(ValueError, match="不安全"):
        PromptSpec.create("bad", "1", "{ticket.__class__}", ("ticket",))


def test_unpublished_version_cannot_be_activated(tmp_path: Path) -> None:
    registry = FilePromptRegistry(tmp_path)
    with pytest.raises(FileNotFoundError):
        registry.activate("support", "missing", traffic_percent=10)
