from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .storage import MemoryStore

DEFAULT_PORT = 3778


def root_from_args(value: str | None) -> Path:
    if value:
        return Path(value).expanduser().resolve()
    env = os.environ.get("OMEMORY_HOME")
    if env:
        return Path(env).expanduser().resolve()
    return (Path.cwd() / ".omemory").resolve()


def main() -> None:
    parser = argparse.ArgumentParser(prog="omemory", description="Owner Memory — local-first persistent memory for agents")
    parser.add_argument("--root", help="memory directory; defaults to ./.omemory")
    sub = parser.add_subparsers(dest="cmd")
    sub.add_parser("init")
    sub.add_parser("status")
    sub.add_parser("doctor")
    start = sub.add_parser("start")
    start.add_argument("--host", default="127.0.0.1")
    start.add_argument("--port", type=int, default=DEFAULT_PORT)
    search = sub.add_parser("search")
    search.add_argument("query", nargs="+")
    search.add_argument("--limit", type=int, default=20)
    search.add_argument("--kind")
    search.add_argument("--project")
    remember = sub.add_parser("remember")
    remember.add_argument("content")
    remember.add_argument("--title", default="Remembered note")
    remember.add_argument("--kind", default="knowledge", choices=["knowledge", "experience", "decision", "workflow", "preference", "project-state"])
    remember.add_argument("--project")
    remember.add_argument("--confidence", type=float, default=1.0)
    args = parser.parse_args()
    store = MemoryStore(root_from_args(args.root))

    if args.cmd in (None, "init"):
        store.init()
        print(f"Owner Memory initialized: {store.root}")
        print("Web UI/API/MCP: http://127.0.0.1:3778")
        if args.cmd is None:
            print("Run: omemory start")
        return
    if args.cmd == "status":
        print(json.dumps(store.stats(), indent=2, ensure_ascii=False)); return
    if args.cmd == "doctor":
        print(json.dumps(store.doctor(), indent=2, ensure_ascii=False)); return
    if args.cmd == "search":
        results = store.search(" ".join(args.query), args.limit, args.kind, args.project)
        for item in results:
            print(f"[{item['score']}] {item['id']} — {item['title']} ({item['type']})")
            print(f"  {item['content'][:240].replace(chr(10), ' ')}")
        return
    if args.cmd == "remember":
        item = store.create(args.kind, args.title, args.content, project=args.project, confidence=args.confidence)
        print(item["id"]); return
    if args.cmd == "start":
        import uvicorn
        from .server import make_app
        store.init()
        print(f"Owner Memory running at http://{args.host}:{args.port}")
        print(f"Dashboard/API: http://{args.host}:{args.port}")
        print(f"MCP:          http://{args.host}:{args.port}/mcp")
        uvicorn.run(make_app(store.root), host=args.host, port=args.port, log_level="info")
        return
    parser.print_help()


if __name__ == "__main__":
    main()
