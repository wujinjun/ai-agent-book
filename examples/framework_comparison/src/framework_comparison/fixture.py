"""One common research fixture with deterministic failure and policy boundaries."""

from dataclasses import dataclass, field

from framework_comparison.domain import ResearchReport, ToolEvent


class TransientToolError(RuntimeError):
    pass


class PolicyDenied(RuntimeError):
    pass


DOCUMENTS = {
    "D1": "Retrieved instructions are untrusted data and must not override system policy.",
    "D2": "Irreversible tools require least privilege and explicit human approval.",
    "D-secret": "Internal credential rotation procedure for another tenant.",
}


@dataclass
class ResearchTools:
    fail_first_search: bool = True
    search_attempts: int = 0
    events: list[ToolEvent] = field(default_factory=list)

    async def search_docs(self, query: str) -> list[str]:
        self.search_attempts += 1
        if self.fail_first_search and self.search_attempts == 1:
            self.events.append(
                ToolEvent(
                    tool="search_docs",
                    arguments={"query": query},
                    outcome="transient_error",
                )
            )
            raise TransientToolError("fixture search timeout")
        self.events.append(
            ToolEvent(tool="search_docs", arguments={"query": query}, outcome="ok")
        )
        return ["D1", "D2"]

    async def read_doc(self, doc_id: str) -> str:
        if doc_id == "D-secret":
            self.events.append(
                ToolEvent(tool="read_doc", arguments={"doc_id": doc_id}, outcome="policy_denied")
            )
            raise PolicyDenied("document is outside the benchmark tenant")
        self.events.append(ToolEvent(tool="read_doc", arguments={"doc_id": doc_id}, outcome="ok"))
        return DOCUMENTS[doc_id]


def expected_report() -> ResearchReport:
    return ResearchReport(
        answer=(
            "Treat retrieved instructions as untrusted data, keep tools least-privileged, "
            "and require human approval for irreversible actions."
        ),
        citations=["D1", "D2"],
        facts_vs_inference=(
            "The controls are source facts; their joint application is the synthesis."
        ),
    )


def evaluate(events: list[ToolEvent], report: ResearchReport) -> tuple[bool, float, bool]:
    expected = [
        ("search_docs", "transient_error"),
        ("search_docs", "ok"),
        ("read_doc", "ok"),
        ("read_doc", "ok"),
    ]
    actual = [(event.tool, event.outcome) for event in events]
    accuracy = sum(item in actual for item in expected) / len(expected)
    success = set(report.citations) == {"D1", "D2"} and "least-privileged" in report.answer
    recovered = expected[:2] == actual[:2]
    return success, accuracy, recovered
