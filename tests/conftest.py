from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, Session, create_engine
from sqlalchemy.pool import StaticPool  # <-- ajoute ça

from app.main import create_app
from app.models.db import get_session


@pytest.fixture
def engine():
    # Base de test en mémoire, réutilisée sur tous les threads
    engine = create_engine(
        "sqlite://",
        echo=False,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    return engine

@pytest.fixture
def session(engine):
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(session):
    app = create_app()

    # Override de la dépendance DB pour les tests
    def _get_session_override():
        yield session

    app.dependency_overrides[get_session] = _get_session_override

    with TestClient(app) as c:
        yield c