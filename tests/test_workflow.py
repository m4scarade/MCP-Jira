from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.services.stories import validate_status_transition


def test_valid_status_transition_next_step():
    # backlog -> todo autorisé
    validate_status_transition("backlog", "todo")


def test_valid_status_transition_same_status():
    validate_status_transition("in_progress", "in_progress")


def test_invalid_status_transition_skip_step():
    # backlog -> in_progress doit lever HTTP 400
    with pytest.raises(HTTPException) as exc:
        validate_status_transition("backlog", "in_progress")
    assert exc.value.status_code == 400