# ADR-038: Research workflow runtime spike

- Status: Accepted for this bounded vertical slice
- Decision: `native_runtime`
- Benchmark: `research-security-v1`
- Installed evidence: native_runtime=stdlib, openai_agents_sdk=0.18.3, pydanticai=2.25.0
- Sensitivity: stable; winners=native_runtime

## Weighted evidence

  - native_runtime: 5.0000
  - openai_agents_sdk: 4.9000
  - pydanticai: 4.9000

## Uncertainty

  - P95 measures local deterministic runtime overhead, not provider network latency.
  - Scripted models isolate control semantics and do not compare model answer quality.
  - The slice does not prove long-duration checkpoint or human-interrupt behavior.

## Rollback

  1. Keep domain ResearchReport and tool contracts framework-neutral.
  2. Stop admitting new runs to the selected adapter.
  3. Export normalized state and allow in-flight runs to drain on their original adapter.
  4. Switch new runs to the previous adapter and replay the golden benchmark.

## Review triggers

- long-running checkpoint or human approval becomes a hard requirement;
- P95 or cost proxy crosses the project budget;
- a pinned framework introduces a breaking change, license change, or security advisory.
