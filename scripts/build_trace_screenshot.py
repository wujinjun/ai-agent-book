#!/usr/bin/env python3
# ruff: noqa: E501
"""Run project 10 locally and render its normalized Trace evidence as PNG."""

from __future__ import annotations

import argparse
import html
import json
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from ai_agent_book.apps.enterprise_platform import EnterprisePlatform  # noqa: E402

CHROME_CANDIDATES = (
    Path("/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"),
    Path("/Applications/Chromium.app/Contents/MacOS/Chromium"),
    Path("/usr/bin/google-chrome"),
    Path("/usr/bin/chromium"),
)


def collect_trace_evidence(database: Path) -> dict[str, object]:
    """Execute the real offline platform path and return redacted evidence."""

    platform = EnterprisePlatform(database)
    platform.create_tenant("trace-demo", "Trace Demo")
    platform.create_user("trace-demo", "admin", role="admin")
    agent = platform.register_agent("trace-demo", "admin", "knowledge-assistant", "rag")
    session = platform.create_session("trace-demo", "admin", agent.agent_id)
    platform.add_document(
        "trace-demo",
        "leave-policy-v3",
        "员工申请年假时，应在工作流中提交并等待主管审批。",
    )
    submitted = platform.submit_run(
        "trace-demo",
        "admin",
        session.session_id,
        "年假申请需要经过什么步骤？",
    )
    completed = platform.process_next()
    if completed is None or completed.status != "succeeded":
        raise RuntimeError("项目 10 离线 Trace 示例未成功完成")
    traces = platform.list_traces("trace-demo", submitted.run_id)
    platform.engine.dispose()
    return {
        "source": "projects/10-enterprise-platform",
        "execution": "offline-real-runtime",
        "tenant": "trace-demo",
        "run_id": f"{submitted.run_id[:8]}…",
        "trace_id": f"{submitted.trace_id[:12]}…",
        "status": completed.status,
        "output": completed.output,
        "events": [
            {
                "sequence": index,
                "event": record.event,
                "details": record.details,
            }
            for index, record in enumerate(traces, start=1)
        ],
    }


def render_trace_html(evidence: dict[str, object]) -> str:
    """Render one self-contained, screenshot-friendly Trace viewer."""

    events = evidence["events"]
    if not isinstance(events, list):
        raise TypeError("events must be a list")
    rows: list[str] = []
    for event in events:
        if not isinstance(event, dict):
            raise TypeError("event must be a mapping")
        sequence = int(event["sequence"])
        name = html.escape(str(event["event"]))
        details = event.get("details", {})
        details_text = html.escape(
            json.dumps(details, ensure_ascii=False, sort_keys=True) if details else "{}"
        )
        rows.append(
            f"""
            <article class="event">
              <div class="rail"><span>{sequence:02d}</span></div>
              <div class="event-card">
                <div><strong>{name}</strong><small>enterprise-platform</small></div>
                <code>{details_text}</code>
                <b>OK</b>
              </div>
            </article>
            """
        )
    output = html.escape(str(evidence["output"]))
    run_id = html.escape(str(evidence["run_id"]))
    trace_id = html.escape(str(evidence["trace_id"]))
    return f"""<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><title>Agent Trace Evidence</title>
<style>
*{{box-sizing:border-box}} body{{margin:0;background:#eef3f8;color:#17233b;font-family:-apple-system,BlinkMacSystemFont,"Segoe UI","PingFang SC",sans-serif}}
.shell{{width:1480px;margin:36px auto;background:#fff;border:1px solid #d7e0ea;border-radius:22px;box-shadow:0 22px 60px #29415c24;overflow:hidden}}
header{{padding:28px 36px 24px;background:linear-gradient(125deg,#102a43,#174a68);color:#fff;display:flex;justify-content:space-between;align-items:end}}
h1{{font-size:26px;margin:0 0 8px}} header p{{margin:0;color:#cce3ee}} .badge{{background:#28a36a;color:#fff;padding:8px 14px;border-radius:999px;font-weight:700}}
.meta{{display:grid;grid-template-columns:1fr 1fr 1fr;gap:14px;padding:22px 36px;border-bottom:1px solid #e5ebf1}}
.meta div{{background:#f7f9fc;border:1px solid #e3e9f0;padding:14px 16px;border-radius:12px}} .meta small{{display:block;color:#69788d;margin-bottom:5px}} .meta code{{color:#0f5878}}
main{{display:grid;grid-template-columns:1.75fr 1fr;gap:32px;padding:28px 36px 34px}}
h2{{font-size:17px;margin:0 0 20px;color:#324963}} .event{{display:grid;grid-template-columns:54px 1fr;min-height:84px}}
.rail{{position:relative;text-align:center}} .rail:after{{content:"";position:absolute;width:2px;background:#b7cad8;top:31px;bottom:-3px;left:26px}} .event:last-child .rail:after{{display:none}}
.rail span{{position:relative;z-index:1;display:inline-grid;place-items:center;width:36px;height:36px;border-radius:50%;background:#0f769f;color:#fff;font-weight:700;font-size:13px}}
.event-card{{height:62px;border:1px solid #dce5ed;border-left:5px solid #1b8bb4;border-radius:10px;padding:11px 14px;display:grid;grid-template-columns:1.1fr 1.4fr 48px;gap:12px;align-items:center}}
.event-card strong{{display:block;font-size:15px}} .event-card small{{display:block;color:#718096;margin-top:4px}} .event-card code{{font-size:12px;color:#475569;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}} .event-card b{{font-size:12px;color:#168354;background:#e8f7ef;padding:5px 8px;border-radius:6px;text-align:center}}
.panel{{background:#f7fafc;border:1px solid #dce5ed;border-radius:14px;padding:20px}} .panel h3{{font-size:15px;margin:0 0 12px}} .answer{{background:#fff;border-left:4px solid #28a36a;padding:14px;line-height:1.7;border-radius:7px;color:#334155}}
.legend{{margin-top:18px;padding-top:16px;border-top:1px solid #dce5ed;color:#607086;font-size:13px;line-height:1.7}} footer{{padding:12px 36px 18px;color:#738196;font-size:12px;text-align:right}}
</style></head><body><div class="shell">
<header><div><h1>Agent Run Trace · 离线实测</h1><p>项目 10 企业级 Agent 平台｜租户隔离知识库请求</p></div><span class="badge">SUCCEEDED</span></header>
<section class="meta"><div><small>RUN ID（脱敏）</small><code>{run_id}</code></div><div><small>TRACE ID（脱敏）</small><code>{trace_id}</code></div><div><small>EXECUTION</small><code>offline-real-runtime</code></div></section>
<main><section><h2>事件因果链</h2>{"".join(rows)}</section><aside><h2>运行结果</h2><div class="panel"><h3>知识库回答</h3><div class="answer">{output}</div><div class="legend">截图由仓库脚本实际运行项目 10 后生成。仅对随机标识做截断，不包含真实用户数据、密钥或生产 Prompt。</div></div></aside></main>
<footer>AI Agent 从零到实战 · 可复现出版证据</footer></div></body></html>"""


def build_trace_screenshot(output: Path, evidence_path: Path) -> Path:
    chrome = next((path for path in CHROME_CANDIDATES if path.is_file()), None)
    if chrome is None:
        raise RuntimeError("未找到 Chrome/Chromium，无法生成 Trace 截图")
    output.parent.mkdir(parents=True, exist_ok=True)
    evidence_path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="agent-book-trace-") as directory:
        work = Path(directory)
        evidence = collect_trace_evidence(work / "platform.db")
        evidence_path.write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        page = work / "trace.html"
        page.write_text(render_trace_html(evidence), encoding="utf-8")
        completed = subprocess.run(
            [
                str(chrome),
                "--headless=new",
                "--hide-scrollbars",
                "--force-device-scale-factor=1",
                "--window-size=1600,800",
                f"--screenshot={output.resolve()}",
                page.resolve().as_uri(),
            ],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if completed.returncode != 0 or not output.is_file():
            raise RuntimeError(f"Trace 截图生成失败：{completed.stderr}")
    return output


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=ROOT / "docs/assets/trace-sample.png")
    parser.add_argument("--evidence", type=Path, default=ROOT / "notes/trace-sample.json")
    args = parser.parse_args()
    print(build_trace_screenshot(args.output, args.evidence))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
