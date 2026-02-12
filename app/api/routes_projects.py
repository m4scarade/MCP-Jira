from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.models.db import get_session
from app.models.entities import Project
from app.models.schemas import ProjectCreate, ProjectRead

router = APIRouter(prefix="/projects", tags=["projects"])


@router.post("", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_project(
    payload: ProjectCreate,
    session: Session = Depends(get_session),
) -> ProjectRead:
    """Créer un projet.

    Règles :
    - name longueur >= 3 (géré par Pydantic)
    - 409 si doublon de nom
    """
    existing = session.exec(
        select(Project).where(Project.name == payload.name)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Project name already exists",
        )

    project = Project(name=payload.name)
    session.add(project)
    session.commit()
    session.refresh(project)
    return project


@router.get("", response_model=list[ProjectRead])
def list_projects(
    session: Session = Depends(get_session),
) -> list[ProjectRead]:
    """Lister tous les projets."""
    projects = session.exec(select(Project)).all()
    return projects