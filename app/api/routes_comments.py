from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select

from app.models.db import get_session
from app.models.entities import Comment, Epic, Story
from app.models.schemas import CommentBase, CommentRead

router = APIRouter(tags=["comments"])


@router.post(
    "/stories/{story_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_comment_to_story(
    story_id: UUID,
    payload: CommentBase,
    session: Session = Depends(get_session),
) -> CommentRead:
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    comment = Comment(
        story_id=story_id,
        epic_id=None,
        text=payload.text,
        author=payload.author,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.post(
    "/epics/{epic_id}/comments",
    response_model=CommentRead,
    status_code=status.HTTP_201_CREATED,
)
def add_comment_to_epic(
    epic_id: UUID,
    payload: CommentBase,
    session: Session = Depends(get_session),
) -> CommentRead:
    epic = session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    comment = Comment(
        story_id=None,
        epic_id=epic_id,
        text=payload.text,
        author=payload.author,
    )
    session.add(comment)
    session.commit()
    session.refresh(comment)
    return comment


@router.get("/stories/{story_id}/comments", response_model=list[CommentRead])
def list_story_comments(
    story_id: UUID,
    session: Session = Depends(get_session),
) -> list[CommentRead]:
    story = session.get(Story, story_id)
    if story is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Story not found",
        )

    comments = session.exec(
        select(Comment).where(Comment.story_id == story_id)
    ).all()
    return comments


@router.get("/epics/{epic_id}/comments", response_model=list[CommentRead])
def list_epic_comments(
    epic_id: UUID,
    session: Session = Depends(get_session),
) -> list[CommentRead]:
    epic = session.get(Epic, epic_id)
    if epic is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Epic not found",
        )

    comments = session.exec(
        select(Comment).where(Comment.epic_id == epic_id)
    ).all()
    return comments