from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.models.db import get_session
from app.models.entities import Project, Sprint, Story, StorySprintHistory
from app.models.schemas import SprintAssignResponse, SprintCreate, SprintRead
from app.services.sprints import (
    ensure_no_open_stories_in_sprint,
    ensure_story_not_in_other_active_sprint,
)

router = APIRouter(tags=["sprints"])


@router.post(
    "/projects/{project_id}/sprints",
    response_model=SprintRead,
    status_code=status.HTTP_201_CREATED,
)
def create_sprint(
    project_id: UUID,
    payload: SprintCreate,
    session: Session = Depends(get_session),
) -> SprintRead:
    project = session.get(Project, project_id)
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found",
        )

    sprint = Sprint(project_id=project_id, name=payload.name, status="planning")
    session.add(sprint)
    session.commit()
    session.refresh(sprint)
    return sprint


@router.put("/sprints/{sprint_id}/start", response_model=SprintRead)
def start_sprint(
    sprint_id: UUID,
    session: Session = Depends(get_session),
) -> SprintRead:
    sprint = session.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found",
        )
    if sprint.status == "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Sprint already active",
        )
    if sprint.status == "closed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot start a closed sprint",
        )

    sprint.status = "active"
    session.add(sprint)
    session.commit()
    session.refresh(sprint)
    return sprint


@router.put("/sprints/{sprint_id}/close", response_model=SprintRead)
def close_sprint(
    sprint_id: UUID,
    session: Session = Depends(get_session),
) -> SprintRead:
    sprint = session.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found",
        )

    ensure_no_open_stories_in_sprint(session, sprint_id)

    sprint.status = "closed"
    session.add(sprint)
    session.commit()
    session.refresh(sprint)
    return sprint


@router.put(
    "/sprints/{sprint_id}/stories/{story_id}",
    response_model=SprintAssignResponse,
)
def assign_story_to_sprint(
    sprint_id: UUID,
    story_id: UUID,
    session: Session = Depends(get_session),
) -> SprintAssignResponse:
    sprint = session.get(Sprint, sprint_id)
    if sprint is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Sprint not found",
        )

    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    ensure_story_not_in_other_active_sprint(session, story_id, sprint)

    existing = session.get(
        StorySprintHistory,
        (story_id, sprint_id),
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Story already in this sprint",
        )

    link = StorySprintHistory(story_id=story_id, sprint_id=sprint_id)
    session.add(link)
    session.commit()

    return SprintAssignResponse(story_id=story_id, sprint_id=sprint_id)


@router.delete("/sprints/{sprint_id}/stories/{story_id}")
def remove_story_from_sprint(
    sprint_id: UUID,
    story_id: UUID,
    session: Session = Depends(get_session),
) -> dict[str, str]:
    link = session.get(StorySprintHistory, (story_id, sprint_id))
    if link is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not in sprint",
        )

    session.delete(link)
    session.commit()
    return {"message": "removed"}