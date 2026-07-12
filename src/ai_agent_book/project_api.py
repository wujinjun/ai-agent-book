"""十个教材项目共享的可部署 FastAPI 外壳。"""

from dataclasses import asdict
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from ai_agent_book.project_catalog import PROJECTS, run_project


class RunRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=20_000)


class RunResponse(BaseModel):
    project_id: int
    status: str
    output: str
    data: dict[str, Any]
    trace: list[str]


app = FastAPI(title="AI Agent Book Projects", version="0.1.0")


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/projects")
async def list_projects() -> list[dict[str, Any]]:
    return [asdict(project) for project in PROJECTS.values()]


@app.post("/projects/{project_id}/run", response_model=RunResponse)
async def execute_project(project_id: int, request: RunRequest) -> dict[str, Any]:
    if project_id not in PROJECTS:
        raise HTTPException(status_code=404, detail="project not found")
    result = run_project(project_id, request.prompt)
    payload = asdict(result)
    payload["trace"] = list(result.trace)
    return payload
