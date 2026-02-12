from __future__ import annotations

from uuid import UUID

from fastapi import HTTPException, status
from sqlmodel import Session, select

from app.models.entities import Sprint, Story, StorySprintHistory
from app.models.schemas import Status

OPEN_STATUSES: set[Status] = {"in_progress", "in_review"}


def ensure_no_open_stories_in_sprint(session: Session, sprint_id: UUID) -> None:
    """Vérifie qu’aucune story du sprint n’est encore en cours/review."""
    query = (
        select(Story)
        .join(StorySprintHistory, StorySprintHistory.story_id == Story.id)
        .where(
            StorySprintHistory.sprint_id == sprint_id,
            Story.status.in_(OPEN_STATUSES),
        )
    )
    any_open = session.exec(query).first()
    if any_open:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot close sprint with stories still in progress or in review",
        )


def ensure_story_not_in_other_active_sprint(
    session: Session,
    story_id: UUID,
    target_sprint: Sprint,
) -> None:
    """Règle métier : une story ne peut appartenir qu’à un seul sprint actif à la fois."""
    query = (
        select(Sprint)
        .join(StorySprintHistory, StorySprintHistory.sprint_id == Sprint.id)
        .where(
            StorySprintHistory.story_id == story_id,
            Sprint.status == "active",
        )
    )
    existing_active = session.exec(query).first()
    if existing_active and existing_active.id != target_sprint.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Story already assigned to active sprint {existing_active.id}",
        )