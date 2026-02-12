from __future__ import annotations

import os
from typing import Generator

from sqlmodel import SQLModel, Session, create_engine


# Pour le dev local : tu pourras mettre ici ton URL Postgres locale
# Exemple : postgresql+psycopg://user:password@localhost:5432/llm_task_manager
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "sqlite:///./dev.db",  # fallback simple pour démarrer, on passera à Postgres ensuite
)

engine = create_engine(DATABASE_URL, echo=False)


def init_db() -> None:
    """Créer les tables au démarrage (dev).
    En prod, on utilisera des migrations Alembic.
    """
    SQLModel.metadata.create_all(engine)


def get_session() -> Generator[Session, None, None]:
    """Dépendance FastAPI pour obtenir une session DB."""
    with Session(engine) as session:
        yield session