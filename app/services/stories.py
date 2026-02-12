from __future__ import annotations

from typing import Dict

from fastapi import HTTPException, status

from app.models.schemas import Status

# Ordre des statuts défini dans ARCHITECTURE.md
WORKFLOW_ORDER: list[Status] = [
    "backlog",
    "todo",
    "in_progress",
    "in_review",
    "done",
]

STATUS_INDEX: Dict[Status, int] = {s: i for i, s in enumerate(WORKFLOW_ORDER)}


def validate_status_transition(current: Status, new: Status) -> None:
    """Interdire les sauts d’étapes dans le workflow.

    Autorise :
    - rester au même statut
    - passer à l’étape suivante (backlog -> todo, todo -> in_progress, ...)
    """
    if current == new:
        return

    cur_idx = STATUS_INDEX[current]
    new_idx = STATUS_INDEX[new]

    if new_idx > cur_idx + 1:
        # Saut d’étape -> 400
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status transition from {current} to {new} (workflow step cannot be skipped)",
        )