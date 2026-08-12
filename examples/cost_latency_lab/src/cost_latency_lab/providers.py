"""Ports and deterministic fixtures for the cost and latency lab."""

from typing import Protocol

from cost_latency_lab.domain import TaskTrace


class TraceProvider(Protocol):
    def load(self) -> tuple[TaskTrace, ...]: ...


class OfflineTraceProvider:
    """Synthetic timestamps and costs; it never sleeps or calls a service."""

    def load(self) -> tuple[TaskTrace, ...]:
        from cost_latency_lab.domain import Span

        return (
            TaskTrace(
                task_id="task-ok",
                success=True,
                spans=(
                    Span("queue", 0, 20, 0),
                    Span("model", 20, 120, 600),
                    Span("weather", 120, 180, 40, logical_call_id="weather"),
                    Span("fx", 120, 155, 30, logical_call_id="fx"),
                    Span("review", 180, 220, 200),
                ),
            ),
            TaskTrace(
                task_id="task-retry",
                success=True,
                spans=(
                    Span("model", 0, 100, 500, logical_call_id="generate", attempt=1),
                    Span("model", 100, 215, 520, logical_call_id="generate", attempt=2),
                    Span("review", 215, 250, 180),
                ),
            ),
            TaskTrace(
                task_id="task-failed",
                success=False,
                spans=(Span("model", 0, 90, 480),),
            ),
        )

