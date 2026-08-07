"""Application-owned result types kept separate from the SDK runtime."""

from typing import Literal

from pydantic import BaseModel, ConfigDict


class SupportReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    summary: str
    risk: Literal["low", "medium", "high"]
