from pathlib import Path

from scripts.build_trace_screenshot import collect_trace_evidence, render_trace_html


def test_trace_screenshot_uses_real_redacted_platform_evidence(tmp_path: Path) -> None:
    evidence = collect_trace_evidence(tmp_path / "platform.db")
    page = render_trace_html(evidence)

    assert evidence["execution"] == "offline-real-runtime"
    assert evidence["status"] == "succeeded"
    assert [event["event"] for event in evidence["events"]] == [
        "run.queued",
        "run.started",
        "run.succeeded",
    ]
    assert str(evidence["run_id"]).endswith("…")
    assert "Agent Run Trace · 离线实测" in page
    assert "Authorization" not in page
