from __future__ import annotations

from fastapi import FastAPI
from app.api import (
    routes_projects,
    routes_epics,
    routes_stories,
    routes_sprints,
    routes_comments,
    routes_documents,
)
from app.models.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="LLM Task Manager")

    @app.on_event("startup")
    def on_startup() -> None:
        init_db()

    @app.get("/health")
    def healthcheck() -> dict[str, str]:
        return {"status": "ok"}

    # Routers REST
    app.include_router(routes_projects.router)
    app.include_router(routes_epics.router)
    app.include_router(routes_stories.router)
    app.include_router(routes_sprints.router)
    app.include_router(routes_comments.router)
    app.include_router(routes_documents.router)
    

    return app


app = create_app()