"""Project 6 durable FastAPI service entrypoint."""

import os
from pathlib import Path

from ai_agent_book.project_service import ServiceSettings, create_project_app

app = create_project_app(
    6,
    settings=ServiceSettings(database_path=Path(os.getenv("DATABASE_PATH", ".data/project-6.db"))),
)
