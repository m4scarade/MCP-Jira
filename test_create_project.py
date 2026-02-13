"""Script pour simuler l'appel de l'outil MCP create_project."""
import asyncio
import json
import sys

sys.path.insert(0, ".")
from app.mcp.server import _create_project


def _make_json_serializable(obj):
    """Convertit les UUID et autres types non-JSON en types sérialisables."""
    from uuid import UUID
    if isinstance(obj, UUID):
        return str(obj)
    if isinstance(obj, dict):
        return {k: _make_json_serializable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_json_serializable(v) for v in obj]
    return obj


async def main():
    try:
        result = await _create_project("Test MCP Cursor")
        result = _make_json_serializable(result)
        print("=== RÉPONSE BRUTE DE create_project ===")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print("ERREUR:", type(e).__name__, str(e), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
