---
name: owner-memory
description: Manage and use the local Owner Memory system (`omemory`) for persistent project knowledge, experiences, decisions, workflows, preferences, and project state. Use when an agent needs to recall prior work, save durable knowledge, search memory, inspect or repair memory, continue a project across sessions, or connect to the local REST/MCP service.
license: MIT
compatibility: Python 3.10+ and the local `omemory` CLI/server when agent access is available.
---

# Owner Memory

Use `omemory` as a file-first continuity layer. The `.omemory/` files are the source of truth; indexes are disposable caches.

## Quick start

```bash
omemory init
omemory start
```

Default endpoints:

- Web UI: `http://127.0.0.1:3778/`
- REST API base: `http://127.0.0.1:3778/api`
- API docs: `http://127.0.0.1:3778/docs`
- Health: `http://127.0.0.1:3778/health`
- MCP Streamable HTTP: `http://127.0.0.1:3778/mcp`

Use a project-local `.omemory/` by default. Do not mix global personal memory with project memory unless explicitly configured.

## Agent startup / resume workflow

When beginning or resuming meaningful work:

1. Detect whether the current project has `.omemory/`.
2. If available, inspect `project-state`, decisions, workflows, and relevant knowledge before making assumptions.
3. Search narrowly for the current task rather than loading the whole store.
4. Verify mutable claims against current project files, tests, configuration, or commands.
5. Continue using remembered workflows only after checking that they still match the current project.

## Saving workflow

After meaningful work, save durable information that will reduce future work:

1. Search first to avoid duplicates.
2. Classify it as `knowledge`, `experience`, `decision`, `workflow`, `preference`, or `project-state`.
3. Include provenance when the information came from a file, command, test, user decision, or external source.
4. Set confidence honestly; uncertainty must not become false certainty.
5. Save the smallest useful record.
6. Never save secrets, credentials, tokens, or sensitive values by default.

Do not turn every chat message into memory. Save durable facts, decisions, repeatable procedures, useful failures/fixes, and meaningful state changes.

## Memory truth model

Memory is evidence, not authority:

`memory → evidence/provenance → confidence → current verification`

If current project evidence conflicts with an old memory, update or mark the old memory stale. Do not silently prefer the older memory.

## CLI

```bash
omemory status
omemory search "payment provider"
omemory search "deployment" --kind workflow
omemory remember "Project uses sandbox payments" --title "Payment environment" --kind knowledge
omemory doctor
```

Use `--root PATH` or `OMEMORY_HOME` for a custom store.

## REST API

All REST routes share the base URL `http://127.0.0.1:3778/api`.

```http
GET    /stats
GET    /memories?q=payment&limit=20
POST   /memories
GET    /memories/{id}
PUT    /memories/{id}
DELETE /memories/{id}
GET    /memories/{id}/history
GET    /doctor
```

The Web UI and MCP operate on the same files through the same storage layer.

## MCP

The local MCP endpoint is:

```text
http://127.0.0.1:3778/mcp
```

Tools:

- `memory_search`
- `memory_get`
- `memory_save`
- `memory_update`
- `memory_delete`
- `memory_status`

Use MCP for agent access; use REST/Web UI for human access. Neither creates a second source of truth.

## Web UI

Open `http://127.0.0.1:3778/` after starting the server. The dashboard must let a human search, inspect, create, edit, delete, filter, and inspect revision history.

## Efficiency

- Search narrowly before loading memory.
- Prefer project-scoped memory.
- Load only memories relevant to the current task.
- Do not repeatedly dump the entire memory tree into model context.
- Keep skill instructions lean and read `references/` only when implementation detail is needed.
