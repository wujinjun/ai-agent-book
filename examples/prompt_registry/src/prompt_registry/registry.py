"""File-backed immutable versions and deterministic rollout state."""

import hashlib
import json
from pathlib import Path

from prompt_registry.domain import PromptSpec


class FilePromptRegistry:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.root.mkdir(parents=True, exist_ok=True)

    def _version_path(self, name: str, version: str) -> Path:
        if not name.isidentifier() or "/" in version or ".." in version:
            raise ValueError("非法 Prompt 名称或版本")
        return self.root / name / f"{version}.json"

    def publish(self, spec: PromptSpec) -> None:
        path = self._version_path(spec.name, spec.version)
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("x", encoding="utf-8") as handle:
            json.dump(spec.to_dict(), handle, ensure_ascii=False, indent=2)

    def load(self, name: str, version: str) -> PromptSpec:
        path = self._version_path(name, version)
        if not path.is_file():
            raise FileNotFoundError(path)
        value: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        return PromptSpec.from_dict(value)

    def _deployment_path(self, name: str) -> Path:
        return self.root / name / "deployment.json"

    def _read_deployment(self, name: str) -> dict[str, object]:
        path = self._deployment_path(name)
        return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}

    def activate(self, name: str, version: str, *, traffic_percent: int) -> None:
        self.load(name, version)
        if not 0 <= traffic_percent <= 100:
            raise ValueError("traffic_percent 必须位于 0..100")
        deployment = self._read_deployment(name)
        current = deployment.get("current", deployment)
        if traffic_percent == 100 or not current:
            updated = {"stable": version, "candidate": None, "traffic_percent": 0}
        else:
            assert isinstance(current, dict)
            updated = {
                "stable": current["stable"],
                "candidate": version,
                "traffic_percent": traffic_percent,
            }
        payload = {"current": updated, "previous": current or None}
        self._deployment_path(name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )

    def select(self, name: str, subject_id: str) -> PromptSpec:
        deployment = self._read_deployment(name)["current"]
        assert isinstance(deployment, dict)
        candidate = deployment.get("candidate")
        bucket = int.from_bytes(
            hashlib.sha256(f"{name}:{subject_id}".encode()).digest()[:4], "big"
        ) % 100
        version = (
            candidate
            if candidate is not None and bucket < int(deployment["traffic_percent"])
            else deployment["stable"]
        )
        return self.load(name, str(version))

    def rollback(self, name: str) -> None:
        deployment = self._read_deployment(name)
        previous = deployment.get("previous")
        if not isinstance(previous, dict) or not previous:
            raise ValueError("没有可回滚的部署状态")
        payload = {"current": previous, "previous": deployment["current"]}
        self._deployment_path(name).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
