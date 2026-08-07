"""Framework-neutral request, output and error contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SupportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tenant_id: str = Field(min_length=2, max_length=32, pattern=r"^[a-z0-9-]+$")
    actor_id: str = Field(min_length=2, max_length=64)
    ticket_id: str = Field(pattern=r"^T-[0-9]+$")
    question: str = Field(min_length=3, max_length=500)


class TicketFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str
    tenant_id: str
    status: Literal["open", "resolved"]
    title: str


class SupportReport(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ticket_id: str = Field(pattern=r"^T-[0-9]+$")
    status: Literal["open", "resolved"]
    summary: str = Field(min_length=8, max_length=300)
    risk: int = Field(ge=0, le=10)


class ErrorBody(BaseModel):
    code: str
    message: str


class PolicyDenied(RuntimeError):
    """The authenticated principal cannot access the requested resource."""


class DependencyUnavailable(RuntimeError):
    """A required domain dependency is temporarily unavailable."""


class InvalidAgentResult(RuntimeError):
    """The model could not satisfy the bounded output contract."""
