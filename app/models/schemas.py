from __future__ import annotations

from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# --- Types métiers partagés (conforme à ARCHITECTURE.md) ---

StoryPoints = Literal[0, 1, 2, 3, 5, 8, 13]
Priority = Literal["low", "medium", "high", "critical"]
Status = Literal["backlog", "todo", "in_progress", "in_review", "done"]


# --- Project ---

class ProjectBase(BaseModel):
    name: str = Field(min_length=3, max_length=100)


class ProjectCreate(ProjectBase):
    """Payload de création de projet."""


class ProjectRead(ProjectBase):
    id: UUID


# --- Epic ---

class EpicBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)


class EpicCreate(EpicBase):
    """Création d’un epic dans un projet donné."""
    project_id: UUID


class EpicUpdate(BaseModel):
    """Mise à jour partielle d’un epic."""
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    status: Optional[Status] = None


class EpicRead(EpicBase):
    id: UUID
    project_id: UUID
    status: Status



# --- Story ---

class StoryBase(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    description: str = Field(min_length=10, max_length=5000)
    story_points: StoryPoints
    priority: Priority


class StoryCreate(StoryBase):
    """Création d’une story dans un epic."""
    epic_id: UUID


class StoryUpdate(BaseModel):
    """Mise à jour d’une story."""
    title: Optional[str] = Field(default=None, min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, min_length=10, max_length=5000)
    story_points: Optional[StoryPoints] = None
    priority: Optional[Priority] = None
    status: Optional[Status] = None
    assigned_to: Optional[str] = Field(default=None, max_length=100)


class StoryRead(BaseModel):
    id: UUID
    epic_id: UUID
    title: str
    description: str
    story_points: StoryPoints
    priority: Priority
    status: Status
    assigned_to: Optional[str]


class StoriesListResponse(BaseModel):
    stories: list[StoryRead]
    total: int



# --- Sprint ---

SprintStatus = Literal["planning", "active", "closed"]


class SprintBase(BaseModel):
    name: str = Field(min_length=3, max_length=100)


class SprintCreate(SprintBase):
    project_id: UUID


class SprintRead(SprintBase):
    id: UUID
    project_id: UUID
    status: SprintStatus


class SprintAssignResponse(BaseModel):
    story_id: UUID
    sprint_id: UUID


# --- Comment ---

class CommentBase(BaseModel):
    text: str = Field(min_length=10, max_length=1000)
    author: Optional[str] = Field(default=None, max_length=100)


class CommentRead(CommentBase):
    id: UUID
    story_id: Optional[UUID]
    epic_id: Optional[UUID]


# --- Document ---

DocType = Literal["problem", "vision", "tdr", "retrospective"]


class DocumentBase(BaseModel):
    type: DocType
    content: str


class DocumentCreate(DocumentBase):
    project_id: UUID


class DocumentUpdate(BaseModel):
    content: str


class DocumentRead(DocumentBase):
    id: UUID
    project_id: UUID