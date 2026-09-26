from __future__ import annotations

import json
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

KINDS = ("knowledge", "experience", "decision", "workflow", "preference", "project-state")


def now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def slug(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "-", value.strip().lower()).strip("-")
    return value[:80] or "memory"


class MemoryStore:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()
        self.memory = self.root / "memory"
        self.projects = self.root / "projects"
        self.workflows = self.root / "workflows"
        self.sessions = self.root / "sessions"
        self.indexes = self.root / "indexes"
        self.logs = self.root / "logs"
        self.history = self.root / "history"
        self.config_path = self.root / "config.json"

    def init(self) -> None:
        for kind in KINDS:
            (self.memory / kind).mkdir(parents=True, exist_ok=True)
        for p in (self.projects, self.workflows, self.sessions, self.indexes, self.logs, self.history):
            p.mkdir(parents=True, exist_ok=True)
        if not self.config_path.exists():
            self._write_json(self.config_path, {
                "version": 1,
                "name": "omemory",
                "storage": "file-first",
                "host": "127.0.0.1",
                "port": 3778,
                "mcp_path": "/mcp",
                "created_at": now(),
            })

    def _write_json(self, path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        os.replace(tmp, path)

    def _read_json(self, path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    def create(self, kind: str, title: str, content: str, *, project: str | None = None,
               source: dict[str, Any] | None = None, confidence: float = 1.0,
               tags: list[str] | None = None) -> dict[str, Any]:
        self.init()
        if kind not in KINDS:
            raise ValueError(f"Unknown kind: {kind}")
        mid = f"{kind}-{uuid.uuid4().hex[:12]}"
        ts = now()
        data = {
            "id": mid,
            "type": kind,
            "title": title.strip(),
            "content": content,
            "project": project,
            "confidence": max(0.0, min(1.0, float(confidence))),
            "status": "active",
            "tags": tags or [],
            "source": source or {"type": "manual"},
            "created_at": ts,
            "updated_at": ts,
        }
        path = self.memory / kind / f"{slug(title)}-{mid[-12:]}.json"
        self._write_json(path, data)
        self._write_json(self.history / mid / f"{ts.replace(":", "-")}-{uuid.uuid4().hex[:6]}.json", {"action": "created", "at": ts, "record": data})
        return data

    def _iter_files(self):
        self.init()
        yield from self.memory.rglob("*.json")
        yield from self.workflows.rglob("*.json")
        yield from self.projects.rglob("*.json")
        yield from self.sessions.rglob("*.json")

    def list(self, kind: str | None = None, project: str | None = None) -> list[dict[str, Any]]:
        out = []
        for path in self._iter_files():
            try:
                item = self._read_json(path)
            except (OSError, json.JSONDecodeError):
                continue
            if kind and item.get("type") != kind:
                continue
            if project and item.get("project") != project:
                continue
            item["_path"] = str(path.relative_to(self.root))
            out.append(item)
        return sorted(out, key=lambda x: x.get("updated_at", ""), reverse=True)

    def get(self, memory_id: str) -> dict[str, Any] | None:
        for item in self.list():
            if item.get("id") == memory_id:
                return item
        return None

    def _path_for_id(self, memory_id: str) -> Path | None:
        for path in self._iter_files():
            try:
                item = self._read_json(path)
            except Exception:
                continue
            if item.get("id") == memory_id:
                return path
        return None

    def update(self, memory_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        path = self._path_for_id(memory_id)
        if not path:
            raise KeyError(memory_id)
        data = self._read_json(path)
        for key in ("title", "content", "project", "confidence", "status", "tags", "source"):
            if key in patch:
                data[key] = patch[key]
        ts = now()
        data["updated_at"] = ts
        self._write_json(path, data)
        self._write_json(self.history / memory_id / f"{ts.replace(":", "-")}-{uuid.uuid4().hex[:6]}.json", {"action": "updated", "at": ts, "record": data})
        return data

    def history_for(self, memory_id: str) -> list[dict[str, Any]]:
        folder = self.history / memory_id
        if not folder.exists():
            return []
        out = []
        for path in sorted(folder.glob("*.json")):
            try:
                out.append(self._read_json(path))
            except Exception:
                pass
        return out

    def delete(self, memory_id: str) -> bool:
        path = self._path_for_id(memory_id)
        if not path:
            return False
        path.unlink()
        return True

    def search(self, query: str, limit: int = 20, kind: str | None = None,
               project: str | None = None) -> list[dict[str, Any]]:
        terms = [t for t in re.findall(r"[\w-]+", query.lower()) if len(t) > 1]
        results = []
        for item in self.list(kind, project):
            hay = " ".join(str(item.get(k, "")) for k in ("title", "content", "tags", "project", "source")).lower()
            score = sum(hay.count(t) for t in terms)
            if score:
                copy = dict(item)
                copy["score"] = score
                results.append(copy)
        return sorted(results, key=lambda x: (x["score"], x.get("updated_at", "")), reverse=True)[:limit]

    def stats(self) -> dict[str, Any]:
        items = self.list()
        counts = {k: 0 for k in KINDS}
        projects = set()
        for i in items:
            counts[i.get("type", "")] = counts.get(i.get("type", ""), 0) + 1
            if i.get("project"):
                projects.add(i["project"])
        return {"root": str(self.root), "total": len(items), "by_type": counts, "projects": sorted(projects)}

    def doctor(self) -> dict[str, Any]:
        self.init()
        broken, duplicates = [], []
        seen = {}
        for path in self._iter_files():
            try:
                item = self._read_json(path)
                if not item.get("id") or not item.get("type") or not item.get("content"):
                    broken.append(str(path.relative_to(self.root)))
                key = (item.get("type"), item.get("title", "").strip().lower(), item.get("project"))
                if key in seen:
                    duplicates.append([seen[key], str(path.relative_to(self.root))])
                else:
                    seen[key] = str(path.relative_to(self.root))
            except Exception as exc:
                broken.append(f"{path.relative_to(self.root)}: {exc}")
        return {"ok": not broken, "broken": broken, "possible_duplicates": duplicates, "stats": self.stats()}
