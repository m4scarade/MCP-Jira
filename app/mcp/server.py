from __future__ import annotations

import asyncio
from typing import Any, Optional
from uuid import UUID

from mcp import types
from mcp.server.lowlevel import Server
from mcp.server.stdio import stdio_server

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


server = Server("llm-task-manager")


def get_session() -> Session:
    return Session(engine)


# --------- Implémentations métier (réutilisées par call_tool) ---------


async def _create_project(name: str) -> dict:
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


async def _search_epics(project_id: str, search: Optional[str] = None) -> list[dict]:
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


async def _create_story(
    epic_id: str,
    title: str,
    description: str,
    story_points: int = 0,
    priority: str = "medium",
) -> dict:
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


async def _list_stories(
    project_id: str,
    status: Optional[str] = None,
    priority: Optional[str] = None,
    assigned_to: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
) -> dict:
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


async def _assign_story_to_sprint(
    sprint_id: str,
    story_id: str,
) -> dict:
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


async def _add_comment_to_story(
    story_id: str,
    text: str,
    author: Optional[str] = None,
) -> dict:
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


async def _create_document(
    project_id: str,
    type: str,
    content: str,
) -> dict:
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


# --------- Déclaration des tools MCP (schema + dispatch) ---------


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    """Déclare les tools disponibles pour le LLM."""
    return [
        types.Tool(
            name="create_project",
            title="Create Project",
            description="Crée un projet Jira-like minimal pour LLMs.",
            input_schema={
                "type": "object",
                "required": ["name"],
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Nom du projet (min 3 caractères).",
                        "minLength": 3,
                    }
                },
            },
        ),
        types.Tool(
            name="search_epics",
            title="Search Epics",
            description="Recherche des epics dans un projet par mot-clé dans le titre.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {
                        "type": "string",
                        "description": "ID du projet (UUID).",
                    },
                    "search": {
                        "type": "string",
                        "description": "Texte à rechercher dans le titre de l’epic.",
                    },
                },
            },
        ),
        types.Tool(
            name="create_story",
            title="Create Story",
            description="Crée une story dans un epic avec points Fibonacci et priorité.",
            input_schema={
                "type": "object",
                "required": ["epic_id", "title", "description"],
                "properties": {
                    "epic_id": {"type": "string", "description": "ID de l’epic."},
                    "title": {"type": "string", "minLength": 3},
                    "description": {"type": "string", "minLength": 10},
                    "story_points": {
                        "type": "integer",
                        "enum": [0, 1, 2, 3, 5, 8, 13],
                        "default": 0,
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                        "default": "medium",
                    },
                },
            },
        ),
        types.Tool(
            name="list_stories",
            title="List Stories",
            description="Liste les stories d’un projet avec filtres statut/priorité/assigné.",
            input_schema={
                "type": "object",
                "required": ["project_id"],
                "properties": {
                    "project_id": {"type": "string"},
                    "status": {
                        "type": "string",
                        "enum": ["backlog", "todo", "in_progress", "in_review", "done"],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["low", "medium", "high", "critical"],
                    },
                    "assigned_to": {"type": "string"},
                    "search": {"type": "string"},
                    "limit": {"type": "integer", "default": 20},
                },
            },
        ),
        types.Tool(
            name="assign_story_to_sprint",
            title="Assign Story to Sprint",
            description="Assigne une story à un sprint (1 seul sprint actif par story).",
            input_schema={
                "type": "object",
                "required": ["sprint_id", "story_id"],
                "properties": {
                    "sprint_id": {"type": "string"},
                    "story_id": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="add_comment_to_story",
            title="Add Comment to Story",
            description="Ajoute un commentaire à une story (>=10 caractères).",
            input_schema={
                "type": "object",
                "required": ["story_id", "text"],
                "properties": {
                    "story_id": {"type": "string"},
                    "text": {"type": "string", "minLength": 10},
                    "author": {"type": "string"},
                },
            },
        ),
        types.Tool(
            name="create_document",
            title="Create Project Document",
            description="Crée un document (problem, vision, tdr, retrospective) pour un projet.",
            input_schema={
                "type": "object",
                "required": ["project_id", "type", "content"],
                "properties": {
                    "project_id": {"type": "string"},
                    "type": {
                        "type": "string",
                        "enum": ["problem", "vision", "tdr", "retrospective"],
                    },
                    "content": {"type": "string"},
                },
            },
        ),
    ]


@server.call_tool()
async def call_tool(
    name: str,
    arguments: dict[str, Any],
) -> list[types.ContentBlock]:
    """Dispatcher central des tools MCP."""
    try:
        if name == "create_project":
            result = await _create_project(name=arguments["name"])
        elif name == "search_epics":
            result = await _search_epics(
                project_id=arguments["project_id"],
                search=arguments.get("search"),
            )
        elif name == "create_story":
            result = await _create_story(
                epic_id=arguments["epic_id"],
                title=arguments["title"],
                description=arguments["description"],
                story_points=arguments.get("story_points", 0),
                priority=arguments.get("priority", "medium"),
            )
        elif name == "list_stories":
            result = await _list_stories(
                project_id=arguments["project_id"],
                status=arguments.get("status"),
                priority=arguments.get("priority"),
                assigned_to=arguments.get("assigned_to"),
                search=arguments.get("search"),
                limit=arguments.get("limit", 20),
            )
        elif name == "assign_story_to_sprint":
            result = await _assign_story_to_sprint(
                sprint_id=arguments["sprint_id"],
                story_id=arguments["story_id"],
            )
        elif name == "add_comment_to_story":
            result = await _add_comment_to_story(
                story_id=arguments["story_id"],
                text=arguments["text"],
                author=arguments.get("author"),
            )
        elif name == "create_document":
            result = await _create_document(
                project_id=arguments["project_id"],
                type=arguments["type"],
                content=arguments["content"],
            )
        else:
            raise ValueError(f"Unknown tool: {name}")
    except KeyError as e:
        raise ValueError(f"Missing required argument: {e.args[0]}") from e

    # On renvoie un bloc JSON structuré
    return [types.JsonContent(type="json", json=result)]
    

# --------- BOOTSTRAP ---------


async def main() -> None:
    # S’assurer que les tables existent (utile en dev)
    init_db()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


if __name__ == "__main__":
    asyncio.run(main())