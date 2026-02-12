from __future__ import annotations

from fastapi.testclient import TestClient


def test_full_crud_flow(client: TestClient):
    # 1) Créer un projet
    resp = client.post("/projects", json={"name": "Proj Test"})
    assert resp.status_code == 201
    project = resp.json()
    project_id = project["id"]

    # 2) Créer un epic
    resp = client.post(
        f"/projects/{project_id}/epics",
        json={
            "project_id": project_id,
            "title": "Epic Test",
        },
    )
    assert resp.status_code == 201
    epic = resp.json()
    epic_id = epic["id"]

    # 3) Créer une story
    resp = client.post(
        f"/epics/{epic_id}/stories",
        json={
            "epic_id": epic_id,
            "title": "Story Test",
            "description": "Description suffisante pour le test",
            "story_points": 3,
            "priority": "medium",
        },
    )
    assert resp.status_code == 201
    story = resp.json()
    story_id = story["id"]
    assert story["status"] == "backlog"

    # 4) Mettre la story en todo
    resp = client.put(
        f"/stories/{story_id}",
        json={"status": "todo"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "todo"

    # 5) Lister les stories du projet
    resp = client.get(f"/projects/{project_id}/stories")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["stories"][0]["id"] == story_id