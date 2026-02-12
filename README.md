# LLM Task Manager

**Jira pour LLMs** - REST + MCP Tools

## Quickstart
```bash
uv sync
uv run alembic upgrade head
uv run uvicorn app.main:app --reload
```

**Docs:** http://localhost:8000/docs

## Démo REST
```bash
curl -X POST http://localhost:8000/projects -d '{"name":"Test"}'
curl http://localhost:8000/projects/p1/stories
```

## Stack
FastAPI • SQLModel • Cloud Run • Cloud SQL PG • MCP

## TP
[ARCHITECTURE.md](./ARCHITECTURE.md) - TOGAF 5 domaines
```
