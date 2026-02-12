from __future__ import annotations

import uuid
from typing import Optional
from uuid import UUID

from sqlmodel import Field, SQLModel


class Project(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(index=True, min_length=3, max_length=100)


class Epic(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id")
    title: str = Field(min_length=3, max_length=200)
    status: str = Field(default="backlog")  # on raffinera avec des enums Pydantic


class Story(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    epic_id: UUID = Field(foreign_key="epic.id")
    title: str = Field(min_length=3, max_length=200)
    description: Optional[str] = Field(default=None)
    story_points: Optional[int] = Field(default=None)
    priority: Optional[str] = Field(default=None)
    status: str = Field(default="backlog")
    assigned_to: Optional[str] = Field(default=None, max_length=100)


class Sprint(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id")
    name: str = Field(max_length=100)
    status: str = Field(default="planning")


class StorySprintHistory(SQLModel, table=True):
    story_id: UUID = Field(foreign_key="story.id", primary_key=True)
    sprint_id: UUID = Field(foreign_key="sprint.id", primary_key=True)
    # on ajoutera un timestamp plus tard si besoin


class Comment(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    story_id: Optional[UUID] = Field(default=None, foreign_key="story.id")
    epic_id: Optional[UUID] = Field(default=None, foreign_key="epic.id")
    text: str = Field(min_length=5)
    author: Optional[str] = Field(default=None, max_length=100)


class Document(SQLModel, table=True):
    id: UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    project_id: UUID = Field(foreign_key="project.id")
    type: str = Field(max_length=50)
    content: str