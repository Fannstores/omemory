from __future__ import annotations

import contextlib
import json
from pathlib import Path
from typing import Any

from starlette.applications import Starlette
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import HTMLResponse, JSONResponse, PlainTextResponse
from starlette.routing import Mount, Route

from .storage import MemoryStore

try:
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None

WEB = Path(__file__).with_name("web")


def build_mcp(store: MemoryStore):
    if FastMCP is None:
        return None
    mcp = FastMCP("Owner Memory", stateless_http=True)

    @mcp.tool()
    def memory_search(query: str, limit: int = 10, kind: str | None = None, project: str | None = None) -> dict[str, Any]:
        """Search relevant persistent Owner Memory entries."""
        return {"results": store.search(query, limit, kind, project)}

    @mcp.tool()
    def memory_get(memory_id: str) -> dict[str, Any]:
        """Read one memory entry by ID."""
        item = store.get(memory_id)
        return item or {"error": "not_found", "id": memory_id}

    @mcp.tool()
    def memory_save(kind: str, title: str, content: str, project: str | None = None,
                    confidence: float = 1.0, tags: list[str] | None = None) -> dict[str, Any]:
        """Persist a memory entry to the local file store."""
        return store.create(kind, title, content, project=project, confidence=confidence, tags=tags)

    @mcp.tool()
    def memory_update(memory_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        """Update an existing memory entry."""
        return store.update(memory_id, patch)

    @mcp.tool()
    def memory_delete(memory_id: str) -> dict[str, Any]:
        """Delete one memory entry."""
        return {"deleted": store.delete(memory_id), "id": memory_id}

    @mcp.tool()
    def memory_status() -> dict[str, Any]:
        """Return Owner Memory storage status and counts."""
        return store.stats()

    return mcp


def make_app(root: str | Path) -> Starlette:
    store = MemoryStore(root)
    store.init()
    mcp = build_mcp(store)

    async def index(_: Request):
        return HTMLResponse((WEB / "index.html").read_text(encoding="utf-8"))

    async def health(_: Request):
        return JSONResponse({"status": "ok", "service": "omemory", "version": "0.1.0"})

    async def stats(_: Request):
        return JSONResponse(store.stats())

    async def memories(request: Request):
        if request.method == "GET":
            q = request.query_params.get("q")
            kind = request.query_params.get("kind")
            project = request.query_params.get("project")
            limit = int(request.query_params.get("limit", "100"))
            return JSONResponse({"items": store.search(q, limit, kind, project) if q else store.list(kind, project)[:limit]})
        payload = await request.json()
        return JSONResponse(store.create(**payload), status_code=201)

    async def memory_history(request: Request):
        return JSONResponse({"items": store.history_for(request.path_params["memory_id"])})

    async def memory_detail(request: Request):
        mid = request.path_params["memory_id"]
        if request.method == "GET":
            item = store.get(mid)
            return JSONResponse(item) if item else JSONResponse({"error": "not_found"}, status_code=404)
        if request.method == "PUT":
            try:
                return JSONResponse(store.update(mid, await request.json()))
            except KeyError:
                return JSONResponse({"error": "not_found"}, status_code=404)
        if request.method == "DELETE":
            return JSONResponse({"deleted": store.delete(mid)})

    async def doctor(_: Request):
        return JSONResponse(store.doctor())

    routes = [
        Route("/", index),
        Route("/health", health),
        Route("/api/stats", stats),
        Route("/api/memories", memories, methods=["GET", "POST"]),
        Route("/api/memories/{memory_id}", memory_detail, methods=["GET", "PUT", "DELETE"]),
        Route("/api/memories/{memory_id}/history", memory_history, methods=["GET"]),
        Route("/api/doctor", doctor),
    ]
    if mcp:
        mcp_app = mcp.streamable_http_app()
        @contextlib.asynccontextmanager
        async def lifespan(_: Starlette):
            async with mcp.session_manager.run():
                yield
        app = Starlette(routes=routes + [Mount("/mcp", app=mcp_app)], lifespan=lifespan)
    else:
        app = Starlette(routes=routes)
    app = CORSMiddleware(app, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
    return app
