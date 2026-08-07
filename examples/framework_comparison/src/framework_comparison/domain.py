"""Normalized benchmark contracts shared by every candidate process."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ResearchReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str = Field(min_length=20)
    citations: list[str] = Field(min_length=2)
    facts_vs_inference: str = Field(min_length=8)


class ToolEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool: Literal["search_docs", "read_doc"]
    arguments: dict[str, str]
    outcome: Literal["ok", "transient_error", "policy_denied"]


class CandidateEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: Literal[1] = 1
    candidate: Literal["native_runtime", "openai_agents_sdk", "pydanticai"]
    framework_version: str
    python_version: str
    task_success: bool
    tool_accuracy: float = Field(ge=0, le=1)
    recovered_from_transient: bool
    p95_latency_ms: float = Field(gt=0)
    cost_proxy_model_requests: int = Field(gt=0)
    state_exported: bool
    state_export: dict[str, object]
    tool_events: list[ToolEvent]
    report: ResearchReport
    implementation_path: str
    implementation_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    runs: int = Field(ge=5)


class Criterion(BaseModel):
    name: str
    weight: float = Field(gt=0, le=1)


class BenchmarkSpec(BaseModel):
    model_config = ConfigDict(extra="forbid")

    benchmark_id: str
    checked_at: str
    query: str
    required_citations: list[str]
    expected_tools: list[str]
    fault: str
    forbidden_document: str
    criteria: list[Criterion]

    @model_validator(mode="after")
    def validate_weights(self) -> "BenchmarkSpec":
        if abs(sum(item.weight for item in self.criteria) - 1.0) > 1e-9:
            raise ValueError("criterion weights must sum to 1")
        return self


class CandidateScore(BaseModel):
    candidate: str
    total: float
    components: dict[str, float]
    confidence: float


class ComparisonResult(BaseModel):
    benchmark_id: str
    selected: str
    scores: list[CandidateScore]
    stable_under_sensitivity: bool
    sensitivity_winners: list[str]
    uncertainty: list[str]
    rollback: list[str]
