"""Provider protocol and offline deterministic fixtures."""

from dataclasses import dataclass, field
from typing import Protocol


class ExtractionProvider(Protocol):
    def propose(
        self, text: str, *, attempt: int, repair_hints: tuple[str, ...]
    ) -> dict[str, object]: ...


class DeterministicIncidentProvider:
    def propose(
        self, text: str, *, attempt: int, repair_hints: tuple[str, ...]
    ) -> dict[str, object]:
        del attempt, repair_hints
        severity = "high" if "严重" in text or "timeout" in text.lower() else "medium"
        service = "payment" if "支付" in text else "api"
        title = text.split("标题：", maxsplit=1)[-1] if "标题：" in text else text[:40]
        return {"title": title, "severity": severity, "affected_service": service}


@dataclass
class ScriptedProvider:
    responses: tuple[dict[str, object], ...]
    calls: int = field(default=0, init=False)

    def propose(
        self, text: str, *, attempt: int, repair_hints: tuple[str, ...]
    ) -> dict[str, object]:
        del text, repair_hints
        self.calls += 1
        return self.responses[min(attempt, len(self.responses) - 1)]
