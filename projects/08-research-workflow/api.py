"""Project 8 durable FastAPI service entrypoint."""

import os
from pathlib import Path

from ai_agent_book.apps.langgraph_research import (
    DurableResearchService,
    SourcePolicy,
    attach_durable_research_routes,
)
from ai_agent_book.project_service import ServiceSettings, create_project_app

database = Path(os.getenv("DATABASE_PATH", ".data/project-8.db"))
app = create_project_app(
    8,
    settings=ServiceSettings(database_path=database),
)
domains = frozenset(
    domain.strip()
    for domain in os.getenv("RESEARCH_ALLOWED_DOMAINS", "example.test").split(",")
    if domain.strip()
)
research = DurableResearchService(
    Path(os.getenv("RESEARCH_DATABASE_PATH", ".data/project-8-research.db")),
    source_policy=SourcePolicy(allowed_domains=domains),
)
attach_durable_research_routes(app, research)
