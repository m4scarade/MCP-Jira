from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlmodel import Session, select

from app.models.db import get_session
from app.models.entities import Epic, Project, Story
from app.models.schemas import (
    Priority,
    Status,
    StoryCreate,
    StoryRead,
    StoryUpdate,
    StoriesListResponse,
)
from app.services.stories import validate_status_transition

router = APIRouter(tags=["stories"])


@router.post(
    "/epics/{epic_id}/stories",
    response_model=StoryRead,
    status_code=status.HTTP_201_CREATED,
)
def create_story(
    epic_id: UUID,
    payload: StoryCreate,
    session: Session = Depends(get_session),
) -> StoryRead:
    """Créer une story dans un epic.

    - points : Fibonacci (géré par Pydantic StoryPoints)
    - status initial : backlog
    """
    epic = session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    story = Story(
        epic_id=epic_id,
        title=payload.title,
        description=payload.description,
        story_points=payload.story_points,
        priority=payload.priority,
        status="backlog",
        assigned_to=None,
    )
    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.get("/stories/{story_id}", response_model=StoryRead)
def get_story(
    story_id: UUID,
    session: Session = Depends(get_session),
) -> StoryRead:
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )
    return story


@router.put("/stories/{story_id}", response_model=StoryRead)
def update_story(
    story_id: UUID,
    payload: StoryUpdate,
    session: Session = Depends(get_session),
) -> StoryRead:
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    # Gestion du workflow (pas de saut d’étapes)
    if payload.status is not None:
        validate_status_transition(story.status, payload.status)
        story.status = payload.status

    if payload.title is not None:
        story.title = payload.title
    if payload.description is not None:
        story.description = payload.description
    if payload.story_points is not None:
        story.story_points = payload.story_points
    if payload.priority is not None:
        story.priority = payload.priority
    if payload.assigned_to is not None:
        story.assigned_to = payload.assigned_to

    session.add(story)
    session.commit()
    session.refresh(story)
    return story


@router.get("/projects/{project_id}/stories", response_model=StoriesListResponse)
def list_stories(
    project_id: UUID,
    status_filter: Optional[Status] = Query(None, alias="status"),
    priority_filter: Optional[Priority] = Query(None, alias="priority"),
    assigned_to: Optional[str] = Query(None),
    sprint_id: Optional[UUID] = Query(None),
    search: Optional[str] = Query(None),
    offset: int = 0,
    limit: int = 50,
    session: Session = Depends(get_session),
) -> StoriesListResponse:
    """Lister les stories d’un projet, avec filtres et pagination."""
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    # Jointure via Epic -> Story
    query = (
        select(Story)
        .join(Epic, Epic.id == Story.epic_id)
        .where(Epic.project_id == project_id)
    )

    if status_filter is not None:
        query = query.where(Story.status == status_filter)

    if priority_filter is not None:
        query = query.where(Story.priority == priority_filter)

    if assigned_to is not None:
        query = query.where(Story.assigned_to == assigned_to)

    if search:
        query = query.where(
            Story.title.contains(search) | Story.description.contains(search)
        )


    result = session.exec(query)
    all_stories = result.all()
    total = len(all_stories)

    # Pagination côté Python (suffisant pour le TP)
    stories_page = all_stories[offset : offset + limit]

    # Conversion vers les modèles Pydantic de sortie
    stories_read = [StoryRead.model_validate(s, from_attributes=True) for s in stories_page]
    
    return StoriesListResponse(stories=stories_read, total=total)