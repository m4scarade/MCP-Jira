from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.models.schemas import StoryCreate, StoryPoints, Priority, Status


def test_story_points_valid():
    story = StoryCreate(
        epic_id="00000000-0000-0000-0000-000000000000",
        title="Valid story",
        description="Long enough description",
        story_points=3,
        priority="high",
    )
    assert story.story_points in StoryPoints.__args__  # type: ignore[attr-defined]


def test_story_points_invalid():
    with pytest.raises(ValidationError):
        StoryCreate(
            epic_id="00000000-0000-0000-0000-000000000000",
            title="Bad story",
            description="Long enough description",
            story_points=4,  # invalide
            priority="high",
        )