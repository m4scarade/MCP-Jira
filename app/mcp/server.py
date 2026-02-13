from __future__ import annotations

from typing import Optional
from uuid import UUID

from fastmcp import FastMCP
from sqlmodel import Session, select

from app.models.db import engine, init_db
from app.models.entities import (
    Project,
    Epic,
    Story,
    Sprint,
    StorySprintHistory,
    Comment,
    Document,
)
from app.models.schemas import (
    ProjectCreate,
    ProjectRead,
    EpicRead,
    StoryCreate,
    StoryRead,
    StoriesListResponse,
    Priority,
    Status,
    DocType,
)
from app.services.sprints import ensure_story_not_in_other_active_sprint


def get_session() -> Session:
    return Session(engine)


# Initialiser la base au démarrage du module (équivalent à l'ancien init_db() dans main)
init_db()


mcp = FastMCP("llm-task-manager")


@mcp.tool
def create_project(name: str) -> dict:
    """Crée un projet Jira-like minimal pour LLMs."""
    payload = ProjectCreate(name=name)

    with get_session() as session:
        existing = session.exec(
            select(Project).where(Project.name == payload.name)
        ).first()
        if existing:
            raise ValueError("Project name already exists")

        project = Project(name=payload.name)
        session.add(project)
        session.commit()
        session.refresh(project)

        return ProjectRead(id=project.id, name=project.name).model_dump()


@mcp.tool
def search_epics(project_id: str, search: Optional[str] = None) -> list[dict]:
    """Recherche des epics dans un projet par mot-clé dans le titre."""
    proj_uuid = UUID(project_id)

    with get_session() as session:
        project = session.get(Project, proj_uuid)
        if project is None:
            raise ValueError("Project not found")

        query = select(Epic).where(Epic.project_id == proj_uuid)
        if search:
            query = query.where(Epic.title.contains(search))

        epics = session.exec(query).all()
        return [EpicRead.model_validate(e, from_attributes=True).model_dump() for e in epics]


@mcp.tool
def create_story(
    epic_id: str,
    title: str,
    description: str,
    story_points: int = 0,
    priority: str = "medium",
) -> dict:
    """Crée une story dans un epic avec points Fibonacci et priorité."""
    payload = StoryCreate(
        epic_id=UUID(epic_id),
        title=title,
        description=description,
        story_points=story_points,
        priority=priority,
    )

    with get_session() as session:
        epic = session.get(Epic, payload.epic_id)
        if epic is None:
            raise ValueError("Epic not found")

        story = Story(
            epic_id=payload.epic_id,
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

        return StoryRead.model_validate(story, from_attributes=True).model_dump()


@mcp.tool
def list_stories(
    project_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
) -> dict:
    """Liste les stories d’un projet avec filtres statut/priorité/assigné."""
    proj_uuid = UUID(project_id)

    status_filter: Optional[Status] = None
    if status is not None:
        status_filter = Status(status)  # type: ignore[arg-type]

    priority_filter: Optional[Priority] = None
    if priority is not None:
        priority_filter = Priority(priority)  # type: ignore[arg-type]

    with get_session() as session:
        project = session.get(Project, proj_uuid)
        if project is None:
            raise ValueError("Project not found")

        query = (
            select(Story)
            .join(Epic, Epic.id == Story.epic_id)
            .where(Epic.project_id == proj_uuid)
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

        all_stories = session.exec(query).all()
        total = len(all_stories)
        stories_page = all_stories[:limit]

        stories_read = [
            StoryRead.model_validate(s, from_attributes=True).model_dump()
            for s in stories_page
        ]

        return StoriesListResponse(stories=stories_read, total=total).model_dump()


@mcp.tool
def assign_story_to_sprint(
    sprint_id: str,
    story_id: str,
) -> dict:
    """Assigne une story à un sprint (1 seul sprint actif par story)."""
    sprint_uuid = UUID(sprint_id)
    story_uuid = UUID(story_id)

    with get_session() as session:
        sprint = session.get(Sprint, sprint_uuid)
        if sprint is None:
            raise ValueError("Sprint not found")

        story = session.get(Story, story_uuid)
        if story is None:
            raise ValueError("Story not found")

        ensure_story_not_in_other_active_sprint(session, story_uuid, sprint)

        existing = session.get(StorySprintHistory, (story_uuid, sprint_uuid))
        if existing:
            raise ValueError("Story already in this sprint")

        link = StorySprintHistory(story_id=story_uuid, sprint_id=sprint_uuid)
        session.add(link)
        session.commit()

        return {"story_id": str(story_uuid), "sprint_id": str(sprint_uuid)}


@mcp.tool
def add_comment_to_story(
    story_id: str,
    text: str,
    author: Optional[str] = None,
) -> dict:
    """Ajoute un commentaire à une story (>=10 caractères)."""
    story_uuid = UUID(story_id)

    with get_session() as session:
        story = session.get(Story, story_uuid)
        if story is None:
            raise ValueError("Story not found")

        if len(text) < 10:
            raise ValueError("Comment text must be at least 10 characters")

        comment = Comment(
            story_id=story_uuid,
            epic_id=None,
            text=text,
            author=author,
        )
        session.add(comment)
        session.commit()
        session.refresh(comment)

        return {
            "id": str(comment.id),
            "story_id": str(comment.story_id),
            "epic_id": comment.epic_id and str(comment.epic_id),
            "text": comment.text,
            "author": comment.author,
        }


@mcp.tool
def create_document(
    project_id: str,
    type: str,
    content: str,
) -> dict:
    """Crée un document (problem, vision, tdr, retrospective) pour un projet."""
    proj_uuid = UUID(project_id)
    doc_type = DocType(type)

    with get_session() as session:
        project = session.get(Project, proj_uuid)
        if project is None:
            raise ValueError("Project not found")

        doc = Document(
            project_id=proj_uuid,
            type=doc_type,
            content=content,
        )
        session.add(doc)
        session.commit()
        session.refresh(doc)

        return {
            "id": str(doc.id),
            "project_id": str(doc.project_id),
            "type": doc.type,
            "content": doc.content,
        }


if __name__ == "__main__":
    # Transport stdio par défaut (compatible MCP)
    mcp.run()