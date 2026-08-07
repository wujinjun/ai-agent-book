"""Project 4 durable FastAPI service entrypoint."""

import os
from pathlib import Path

from ai_agent_book.apps.knowledge_agent import VersionedKnowledgePipeline, attach_knowledge_routes
from ai_agent_book.project_service import ServiceSettings, create_project_app

database = Path(os.getenv("DATABASE_PATH", ".data/project-4.db"))
app = create_project_app(
    4,
    settings=ServiceSettings(database_path=database),
)
pipeline = VersionedKnowledgePipeline(
    Path(os.getenv("PIPELINE_DATABASE_PATH", ".data/project-4-pipeline.db"))
)
attach_knowledge_routes(
    app,
    pipeline,
    import_root=Path(os.getenv("IMPORT_ROOT", ".data/imports")),
)
