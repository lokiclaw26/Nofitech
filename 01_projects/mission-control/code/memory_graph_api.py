#!/usr/bin/env python3
"""
memory_graph_api.py — HTTP endpoint handlers for the Memory Graph.

MC-MEMORY-GRAPH-3A-BACKEND (2026-06-17). Stdlib-only.

Each handler is a small function that takes a BaseHTTPRequestHandler and
returns a (status_code, payload_dict) tuple. The HTTP layer in
serve.py / server.py converts that into a JSON response. The auth check
runs before any write.
"""
from __future__ import annotations

import json
import urllib.parse
from typing import Any

from security import is_authorized, auth_required_error, redact_secrets
from memory_graph_store import get_store


# Body limits (per spec). Keep tight; events should be small JSON objects.
_MAX_EVENT_BODY = 64 * 1024
_MAX_RESET_BODY = 4 * 1024


def _read_json_body(handler, max_bytes: int) -> tuple[dict | list | None, str | None]:
    """Read + parse the request body. Returns (parsed, error_msg)."""
    try:
        length = int(handler.headers.get("Content-Length") or "0")
    except (TypeError, ValueError):
        length = 0
    if length < 0 or length > max_bytes:
        return None, f"body must be 1..{max_bytes} bytes"
    raw = handler.rfile.read(length) if length > 0 else b""
    if not raw:
        return None, "empty body"
    try:
        return json.loads(raw.decode("utf-8")), None
    except (UnicodeDecodeError, json.JSONDecodeError) as e:
        return None, f"invalid JSON: {e}"


def get_graph(handler) -> tuple[int, dict]:
    """GET /api/memory-graph — return the full graph."""
    store = get_store()
    # Cheap repair: ensure dangling edges have placeholders.
    store.repair_graph()
    g = store.load_graph()
    return 200, {
        "nodes": g.get("nodes", []),
        "edges": g.get("edges", []),
        "metadata": g.get("metadata", {}),
        "last_updated": g.get("last_updated"),
        "node_count": g.get("node_count", 0),
        "edge_count": g.get("edge_count", 0),
    }


def post_events(handler) -> tuple[int, dict]:
    """POST /api/memory-graph/events — ingest one event or an array.

    Requires auth (per MC-MEMORY-GRAPH-3A-BACKEND §1).
    Body is redacted before ingestion.
    """
    if not is_authorized(handler):
        return 403, auth_required_error()

    parsed, err = _read_json_body(handler, _MAX_EVENT_BODY)
    if err:
        return 400, {"error": err}
    events = parsed if isinstance(parsed, list) else [parsed]
    if not events:
        return 400, {"error": "no events in payload"}

    store = get_store()
    results: list[dict] = []
    all_ok = True
    for ev in events:
        if not isinstance(ev, dict):
            all_ok = False
            results.append({"ok": False, "error": "event must be a JSON object"})
            continue
        # Redact FIRST, then ingest. Persisted data is always safe.
        redacted = redact_secrets(ev)
        try:
            r = store.ingest_event(redacted)
        except ValueError as e:
            all_ok = False
            results.append({"ok": False, "error": str(e), "type": ev.get("type")})
            continue
        results.append(r)
        if not r.get("ok"):
            all_ok = False
    return (200 if all_ok else 400), {
        "ok": all_ok,
        "results": results,
        "count": len(results),
    }


def post_reset(handler) -> tuple[int, dict]:
    """POST /api/memory-graph/reset — admin reset; requires auth."""
    if not is_authorized(handler):
        return 403, auth_required_error()
    # Body may be empty. Read for shape-validation only.
    try:
        length = int(handler.headers.get("Content-Length") or "0")
    except (TypeError, ValueError):
        length = 0
    if length < 0 or length > _MAX_RESET_BODY:
        return 400, {"error": f"body must be 1..{_MAX_RESET_BODY} bytes"}
    if length > 0:
        handler.rfile.read(length)  # discard; we don't accept {confirm:true}

    store = get_store()
    g = store.reset()
    return 200, {
        "ok": True,
        "reset_at": g.get("last_updated"),
        "node_count": g.get("node_count", 0),
        "edge_count": g.get("edge_count", 0),
    }


def get_events_recent(handler) -> tuple[int, dict]:
    """GET /api/memory-graph/events/recent?n=20"""
    p = urllib.parse.urlparse(handler.path)
    qs = urllib.parse.parse_qs(p.query)
    try:
        n = int((qs.get("n", [20])[0] or "20"))
    except (TypeError, ValueError):
        n = 20
    n = max(1, min(n, 200))
    store = get_store()
    return 200, {"events": store.recent_events(n), "count": n}


def get_stream_disabled(handler) -> tuple[int, dict]:
    """GET /api/memory-graph/stream — disabled (was blocking SSE).

    Returns 410 Gone per MC-MEMORY-GRAPH-3A spec §6.
    """
    return 410, {
        "error": "SSE stream endpoint disabled — poll /api/memory-graph instead",
        "use_polling": True,
        "polling_endpoint": "/api/memory-graph",
        "polling_interval_seconds": 5,
    }


def emit_kanban_memory_event(task_id: str, new_status: str,
                             project: str | None = None,
                             label: str | None = None) -> None:
    """Best-effort: emit a node.upsert for a kanban status change.

    Called by kanban_service when a task's kanban_status changes. If the
    memory store is not initialised or anything fails, swallow silently —
    the memory graph must never break a kanban op.
    """
    try:
        store = get_store()
        nid = f"task-{task_id}"
        node = {
            "id": nid,
            "kind": "task",
            "label": label or task_id,
            "summary": f"Kanban task {task_id} → {new_status}",
            "importance": 0.7,
            "confidence": 0.9,
            "status": str(new_status or "active"),
            "tags": ["kanban", "task"],
            "metadata": {},
            "source": "kanban-bridge",
        }
        if project:
            node["project"] = project
        store.ingest_event({"type": "node.upsert", "node": node,
                            "task_id": task_id, "actor": "kanban-bridge"})
    except Exception:
        pass
