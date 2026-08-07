"""Project 3 durable FastAPI service entrypoint."""

import os
from pathlib import Path

from ai_agent_book.project_service import ServiceSettings, create_project_app

app = create_project_app(
    3,
    settings=ServiceSettings(database_path=Path(os.getenv("DATABASE_PATH", ".data/project-3.db"))),
)
