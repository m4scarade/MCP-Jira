from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.models.db import get_session
from app.models.entities import Epic, Project
from app.models.schemas import EpicCreate, EpicRead, EpicUpdate, Status

router = APIRouter(tags=["epics"])


@router.post(
    "/projects/{project_id}/epics",
    response_model=EpicRead,
    status_code=status.HTTP_201_CREATED,
)
def create_epic(
    project_id: UUID,
    payload: EpicCreate,
    session: Session = Depends(get_session),
) -> EpicRead:
    """Créer un epic dans un projet.

    - 404 si le projet n’existe pas
    - status initial = backlog
    """
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    epic = Epic(
        project_id=project_id,
        title=payload.title,
        status="backlog",
    )
    session.add(epic)
    session.commit()
    session.refresh(epic)
    return epic


@router.get("/epics/{epic_id}", response_model=EpicRead)
def get_epic(
    epic_id: UUID,
    session: Session = Depends(get_session),
) -> EpicRead:
    """Lire un epic par son id."""
    epic = session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )
    return epic


@router.put("/epics/{epic_id}", response_model=EpicRead)
def update_epic(
    epic_id: UUID,
    payload: EpicUpdate,
    session: Session = Depends(get_session),
) -> EpicRead:
    """Modifier un epic (titre, statut).

    TODO (plus tard) : appliquer les règles de workflow sur status.
    """
    epic = session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    if payload.title is not None:
        epic.title = payload.title

    if payload.status is not None:
        # Ici, Pydantic garantit déjà que le status est dans l’enum Status
        epic.status = payload.status

    session.add(epic)
    session.commit()
    session.refresh(epic)
    return epic


@router.get("/projects/{project_id}/epics", response_model=list[EpicRead])
def list_epics(
    project_id: UUID,
    status_filter: Optional[Status] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    session: Session = Depends(get_session),
) -> list[EpicRead]:
    """Lister les epics d’un projet, avec filtre statut et recherche.

    - 404 si le projet n’existe pas
    """
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    query = select(Epic).where(Epic.project_id == project_id)

    if status_filter is not None:
        query = query.where(Epic.status == status_filter)

    if search:
        # .contains fonctionne sur SQLite et Postgres, suffisant pour le TP
        query = query.where(Epic.title.contains(search))

    epics = session.exec(query).all()
    return epics