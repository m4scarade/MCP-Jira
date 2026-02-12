# LLM Task Manager (mcp-jira)

Projet minimal type "Jira" pour LLMs — REST API avec FastAPI, modèles SQLModel et outils MCP.

Ce dépôt fournit une API pour gérer des projets, epics, stories, sprints, commentaires et documents.

---

## Prérequis

- macOS (ou Linux)
- Python 3.12+
- zsh (instructions compatibles)
- Git

Remarque : le projet utilise SQLite par défaut en développement. Pour la production, configurez une base PostgreSQL et la variable d'environnement `DATABASE_URL`.

---

## Installation (locale)

1. Cloner le dépôt :

   git clone <url-du-repo>
   cd MCP-Jira

2. Créer et activer un environnement virtuel (zsh) :

   python -m venv .venv
   source .venv/bin/activate

3. Mettre pip à jour et installer le projet :

   python -m pip install --upgrade pip
   pip install -e .

La commande `pip install -e .` installe les dépendances listées dans `pyproject.toml`.

---

## Configuration de la base de données

Par défaut, l'application utilise SQLite : `sqlite:///./dev.db`.

Pour utiliser PostgreSQL, exportez la variable d'environnement `DATABASE_URL` avant de lancer l'application, par exemple :

  export DATABASE_URL="postgresql+psycopg://user:password@localhost:5432/llm_task_manager"

Note : en production, utilisez des migrations (Alembic) et une configuration sécurisée.

---

## Commandes utiles

- Initialiser la base (création des tables en dev) :

  # Les tables sont créées automatiquement au démarrage via init_db().
  # Pour forcer la création depuis un shell Python :
  python -c "from app.models.db import init_db; init_db()"

- Lancer l'API en mode développement avec live-reload :

  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

- Lancer les tests :

  pytest

- Construire et exécuter en Docker (exemple simple) :

  docker build -t mcp-jira .
  docker run -p 8000:8000 -e DATABASE_URL="$DATABASE_URL" mcp-jira

---

## Documentation et endpoints

Une documentation interactive Swagger est disponible après démarrage :

  http://localhost:8000/docs

Principaux endpoints (exemples) :

- Tester l'api :

  curl http://localhost:8000/health

- Créer un projet :

  curl -X POST http://localhost:8000/projects -H "Content-Type: application/json" -d '{"name":"Mon projet"}'

- Lister les projets :

  curl http://localhost:8000/projects

- Créer un epic :

  curl -X POST http://localhost:8000/projects/<project_id>/epics -H "Content-Type: application/json" -d '{"project_id":"<project_id>","title":"Nouvel Epic"}'

- Créer une story :

  curl -X POST http://localhost:8000/epics/<epic_id>/stories -H "Content-Type: application/json" -d '{"epic_id":"<epic_id>","title":"Story 1","description":"Description suffisante...","story_points":3,"priority":"medium"}'

- Mettre à jour le statut d'une story :

  curl -X PUT http://localhost:8000/stories/<story_id> -H "Content-Type: application/json" -d '{"status":"todo"}'

- Lister les stories d'un projet :

  curl http://localhost:8000/projects/<project_id>/stories

(Remplacez `<project_id>`, `<epic_id>`, `<story_id>` par des UUIDs retournés par l'API.)

---

## MCP Tools (LLM)

Le projet contient des outils MCP exposés via `app.mcp.server`. Pour exécuter le serveur MCP (outil LLM) en local :

  python -m app.mcp.server

Cela nécessite la dépendance `mcp` installée (fournie via `pyproject.toml`). Le serveur MCP expose des tools utilisables par un assistant LLM (voir `app/mcp/server.py`).

---

## Tests

Les tests utilisent une base SQLite en mémoire. Pour exécuter l'ensemble des tests :

  pytest -q

Le fichier `tests/conftest.py` montre comment la dépendance DB est overridée pour les tests.

---

## Bonnes pratiques

- Ne pas committer de fichiers de base de données locaux (ex: `dev.db`) — ajoutez-les à `.gitignore` si nécessaire.
- Utiliser une variable d'environnement sécurisée pour `DATABASE_URL` en production.
- Ajouter des migrations Alembic pour la gestion du schéma en production.

---

## Références

- Architecture du projet : `ARCHITECTURE.md`
- Docs API : `http://localhost:8000/docs` (après démarrage)
