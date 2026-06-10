#!/usr/bin/env python3
"""
NofiTech Mission Control — task & event manager (stdlib only).

Helper CLI for the 3-agent company (NOFI, Thor, Forge, Argus) to
create, update, and query task files, and to append structured events
to the JSONL log. Mission Control (serve.py) reads both sources live.

Conventions
-----------
* Task files live at:  01_projects/<project>/tasks/<id>.md
* Events log lives at: 00_company_os/events.jsonl  (JSON-Lines, append-only)
* Repo root is inferred from this script's location:
      00_company_os/mc_event.py  →  repo root is parent.parent

CLI usage
---------
    # Create a new task
    python3 mc_event.py create-task \\
        --project mission-control \\
        --title "Verify automatic wiring" \\
        --created-by nofi \\
        --assigned-to forge \\
        --priority normal \\
        --description "Stage 14 test" \\
        --acceptance "Task appears in dashboard"

    # Assign it (sets status=assigned, appends task_assigned)
    python3 mc_event.py assign \\
        --task 01_projects/mission-control/tasks/MC-LIVE-TEST-001.md \\
        --assigned-to forge \\
        --actor thor

    # Move to in_progress (appends work_started)
    python3 mc_event.py status \\
        --task 01_projects/mission-control/tasks/MC-LIVE-TEST-001.md \\
        --status in_progress \\
        --actor forge

    # Move to complete (appends task_completed; thor is the canonical closer)
    python3 mc_event.py status \\
        --task 01_projects/mission-control/tasks/MC-LIVE-TEST-001.md \\
        --status complete \\
        --actor thor

    # Append a free-form event
    python3 mc_event.py event \\
        --actor forge \\
        --event-type forge_reported \\
        --project mission-control \\
        --task-id MC-LIVE-TEST-001 \\
        --title "Stage 14 wiring implemented" \\
        --message "Helper, schema, and serve.py edits done."

    # List tasks (real only by default; --include-demo to see Stage 6 demos)
    python3 mc_event.py list-tasks
    python3 mc_event.py list-tasks --project mission-control --include-demo

Python API
----------
    from mc_event import create_task, assign_task, set_status, append_event, list_tasks
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# ---------- paths ----------

HERE = Path(__file__).resolve().parent                  # 00_company_os/
COMPANY_ROOT = HERE.parent                              # ~/NofiTech-Ind/
EVENTS_PATH = HERE / "events.jsonl"                     # 00_company_os/events.jsonl

# Status enum (kept in sync with task-schema.md and event-schema.md)
ALLOWED_STATUSES = {
    "triage", "assigned", "in_progress", "verification",
    "complete", "failed", "blocked", "cancelled",
}
ALLOWED_EVENT_TYPES = {
    "task_created", "task_assigned", "task_completed", "task_failed", "task_cancelled",
    "work_started", "work_updated", "forge_reported",
    "argus_started", "argus_passed", "argus_failed",
    "stage_advanced", "system_event",
}
ALLOWED_ACTORS = {"nofi", "thor", "forge", "argus"}
ALLOWED_PRIORITIES = {"low", "normal", "high", "urgent"}


# ---------- low-level helpers ----------

def _now_iso() -> str:
    """ISO-8601 UTC, second precision, +00:00 offset."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")


def _slugify(text: str, max_len: int = 40) -> str:
    """Filesystem-safe slug. Lowercase, alnum + dash, collapsed."""
    if not text:
        return "task"
    t = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    t = re.sub(r"-+", "-", t)
    if len(t) > max_len:
        t = t[:max_len].rstrip("-")
    return t or "task"


def _parse_frontmatter(text: str) -> Tuple[Dict[str, str], str]:
    """Return (meta, body). Empty meta if no frontmatter."""
    if not text or not text.startswith("---\n"):
        return {}, text or ""
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fm = text[4:end]
    body = text[end + 5:]
    meta: Dict[str, str] = {}
    for line in fm.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def _dump_frontmatter(meta: Dict[str, Any], body: str) -> str:
    """Render a Markdown file with YAML-ish frontmatter (no external deps)."""
    lines = ["---"]
    for k, v in meta.items():
        if v is None:
            v = ""
        s = str(v)
        # Quote if value contains characters that confuse YAML / our parser
        needs_quote = any(c in s for c in [":", "#", "\n", '"', "'"]) or s.strip() != s
        if needs_quote:
            s = '"' + s.replace("\\", "\\\\").replace('"', '\\"') + '"'
        lines.append(f"{k}: {s}")
    lines.append("---")
    if body and not body.startswith("\n"):
        lines.append("")
    if body:
        lines.append(body)
    return "\n".join(lines) + "\n"


# ---------- events ----------

def append_event(actor: str, event_type: str, project: str = "",
                 task_id: str = "", title: str = "", message: str = "",
                 status: str = "", source_file: str = "") -> Dict[str, Any]:
    """Append a single JSON-Lines event to events.jsonl. Returns the event dict."""
    if event_type not in ALLOWED_EVENT_TYPES:
        raise ValueError(f"event_type {event_type!r} not in {sorted(ALLOWED_EVENT_TYPES)}")
    if actor not in ALLOWED_ACTORS:
        raise ValueError(f"actor {actor!r} not in {sorted(ALLOWED_ACTORS)}")
    evt = {
        "ts": _now_iso(),
        "actor": actor,
        "event_type": event_type,
        "project": project,
        "task_id": task_id,
        "title": title,
        "message": message,
        "status": status,
        "source_file": source_file,
        "schema": "nofitech-event/v1",
    }
    line = json.dumps(evt, ensure_ascii=False)
    # Atomic append: open, write, flush, close
    with EVENTS_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")
    return evt


def read_events(limit: int = 50) -> List[Dict[str, Any]]:
    """Read the last `limit` events (most recent first). Returns [] if file missing."""
    if not EVENTS_PATH.is_file():
        return []
    out: List[Dict[str, Any]] = []
    try:
        with EVENTS_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return out
    return out[-limit:][::-1]


# ---------- task ids ----------

def _project_prefix(project: str) -> str:
    """Derive a short prefix for auto-generated task ids.

    Rules, in order:
      1. If the project name is a single token, use its first 2-3 upper
         letters: 'forge' → 'FOR', 'argus' → 'ARG'.
      2. If it's multi-token, take the first letter of each token, uppercased,
         then pad with the next letters of the first token until 2-3 chars:
         'mission-control' → 'MC'.
      3. Fall back to first 2 chars of the project name.
    """
    if not project:
        return "TSK"
    parts = [p for p in re.split(r"[^A-Za-z0-9]+", project) if p]
    if not parts:
        return project[:2].upper() or "TSK"
    if len(parts) == 1:
        p = parts[0]
        return (p[:3] if len(p) >= 3 else p[:2]).upper() or "TSK"
    # multi-token: initials, padded to at least 2 chars
    initials = "".join(p[0] for p in parts)[:3].upper()
    if len(initials) < 2:
        initials = (initials + parts[0][: 2 - len(initials)]).upper()
    return initials or "TSK"


def _next_task_id(project: str) -> str:
    """Generate the next task id for a project: <PREFIX>-LIVE-001, etc.

    We deliberately do NOT count Stage 6 demo files (MC-001..MC-007) as
    occupying numbers — they were authored before this scheme existed and
    live under `data_source: local-demo`. The first real task for
    mission-control is therefore MC-LIVE-001.
    """
    prefix = _project_prefix(project)
    tasks_dir = COMPANY_ROOT / "01_projects" / project / "tasks"
    max_n = 0
    if tasks_dir.is_dir():
        for f in tasks_dir.glob(f"{prefix}-LIVE-*.md"):
            m = re.match(rf"{re.escape(prefix)}-LIVE-(\d+)-?", f.stem)
            if m:
                n = int(m.group(1))
                if n > max_n:
                    max_n = n
    n = max_n + 1
    return f"{prefix}-LIVE-{n:03d}"


def _task_id_from_explicit(explicit: str, project: str) -> str:
    """If the caller gave a non-default task id, use it. Otherwise auto-gen."""
    if explicit and not explicit.startswith("AUTO-"):
        return explicit
    return _next_task_id(project)


# ---------- task I/O ----------

def _write_task_file(path: Path, meta: Dict[str, Any], body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(_dump_frontmatter(meta, body), encoding="utf-8")


def _read_task_file(path: Path) -> Tuple[Dict[str, str], str]:
    p = _resolve_task_path(path)
    if not p.is_file():
        raise FileNotFoundError(f"task file not found: {p}")
    return _parse_frontmatter(p.read_text(encoding="utf-8"))


def _resolve_task_path(path: str | Path) -> Path:
    """Resolve a task path. If relative, try as-is first, then relative to
    the repo root (so `01_projects/...` works regardless of cwd)."""
    p = Path(path)
    if p.is_file():
        return p
    if not p.is_absolute():
        candidate = COMPANY_ROOT / p
        if candidate.is_file():
            return candidate
    return p  # let callers raise with the original error


def create_task(project: str, title: str, created_by: str, assigned_to: str,
                priority: str = "normal", description: str = "",
                acceptance: str = "", task_id: str = "") -> Path:
    """Create a new task file and append a `task_created` event.

    Returns the path of the created file.
    """
    if not project:
        raise ValueError("project is required")
    if not title:
        raise ValueError("title is required")
    if created_by not in ALLOWED_ACTORS:
        raise ValueError(f"created_by {created_by!r} not in {sorted(ALLOWED_ACTORS)}")
    if assigned_to not in ALLOWED_ACTORS:
        raise ValueError(f"assigned_to {assigned_to!r} not in {sorted(ALLOWED_ACTORS)}")
    if priority not in ALLOWED_PRIORITIES:
        raise ValueError(f"priority {priority!r} not in {sorted(ALLOWED_PRIORITIES)}")

    tid = _task_id_from_explicit(task_id, project)
    now = _now_iso()
    rel_path = f"01_projects/{project}/tasks/{tid}.md"
    abs_path = COMPANY_ROOT / rel_path
    if abs_path.is_file():
        raise FileExistsError(f"task file already exists: {rel_path}")

    meta = {
        "id": tid,
        "title": title,
        "project": project,
        "created_by": created_by,
        "assigned_to": assigned_to,
        "status": "triage",
        "priority": priority,
        "created_at": now,
        "updated_at": now,
        "current_stage": "triage",
        "blocker": "",
        "data_source": "real",
        "description": description,
        "acceptance": acceptance,
    }
    body = (
        f"\n## Brief\n{description or 'No description.'}\n\n"
        f"## Acceptance\n{acceptance or 'No acceptance criteria stated.'}\n"
    )
    _write_task_file(abs_path, meta, body)
    append_event(
        actor=created_by,
        event_type="task_created",
        project=project,
        task_id=tid,
        title=title,
        message=f"Task created: {tid}",
        status="triage",
        source_file=rel_path,
    )
    print(f"[forge] task created: {rel_path}  (id={tid}, status=triage)")
    return abs_path


def update_task(task_path: str | Path, **fields: Any) -> Dict[str, str]:
    """Update frontmatter fields on an existing task. Bumps updated_at.

    Appends a `work_updated` event listing the changed fields.
    Returns the new frontmatter dict.
    """
    p = _resolve_task_path(task_path)
    if not p.is_file():
        raise FileNotFoundError(f"task file not found: {p}")
    meta, body = _parse_frontmatter(p.read_text(encoding="utf-8"))
    changed = []
    for k, v in fields.items():
        if meta.get(k) != ("" if v is None else str(v)):
            changed.append(k)
        meta[k] = "" if v is None else str(v)
    meta["updated_at"] = _now_iso()
    _write_task_file(p, meta, body)
    rel = str(p.relative_to(COMPANY_ROOT)) if p.is_absolute() else str(p)
    append_event(
        actor=meta.get("assigned_to") or "forge",
        event_type="work_updated",
        project=meta.get("project") or "",
        task_id=meta.get("id") or p.stem,
        title=f"Updated: {', '.join(changed) or 'no-op'}",
        message="; ".join(changed),
        status=meta.get("status") or "",
        source_file=rel,
    )
    print(f"[forge] task updated: {rel}  (changed: {', '.join(changed) or 'none'})")
    return meta


def assign_task(task_path: str | Path, assigned_to: str, actor: str = "thor") -> Dict[str, str]:
    """Assign a task. Sets assigned_to and status='assigned'."""
    if actor not in ALLOWED_ACTORS:
        raise ValueError(f"actor {actor!r} not in {sorted(ALLOWED_ACTORS)}")
    if assigned_to not in ALLOWED_ACTORS:
        raise ValueError(f"assigned_to {assigned_to!r} not in {sorted(ALLOWED_ACTORS)}")
    p = _resolve_task_path(task_path)
    meta, body = _read_task_file(p)
    meta["assigned_to"] = assigned_to
    meta["status"] = "assigned"
    meta["updated_at"] = _now_iso()
    _write_task_file(p, meta, body)
    rel = str(p.relative_to(COMPANY_ROOT)) if p.is_absolute() else str(p)
    append_event(
        actor=actor,
        event_type="task_assigned",
        project=meta.get("project") or "",
        task_id=meta.get("id") or p.stem,
        title=f"{meta.get('id') or p.stem} assigned to {assigned_to}",
        message=f"Assigned by {actor}",
        status="assigned",
        source_file=rel,
    )
    print(f"[forge] task assigned: {rel}  → {assigned_to}")
    return meta


def set_status(task_path: str | Path, status: str, actor: str = "thor", message: str = "") -> Dict[str, str]:
    """Set status on a task and append the matching event."""
    if status not in ALLOWED_STATUSES:
        raise ValueError(f"status {status!r} not in {sorted(ALLOWED_STATUSES)}")
    if actor not in ALLOWED_ACTORS:
        raise ValueError(f"actor {actor!r} not in {sorted(ALLOWED_ACTORS)}")
    p = _resolve_task_path(task_path)
    meta, body = _read_task_file(p)
    old = meta.get("status")
    meta["status"] = status
    meta["updated_at"] = _now_iso()
    # Map status → event_type (canonical pipeline)
    evt_map = {
        "assigned":     "task_assigned",
        "in_progress":  "work_started" if old in (None, "", "triage", "assigned") else "work_updated",
        "verification": "forge_reported",
        "complete":     "task_completed",
        "failed":       "task_failed",
        "blocked":      "work_updated",
        "cancelled":    "task_cancelled",
        "triage":       "work_updated",
    }
    evt = evt_map.get(status, "work_updated")
    # If old status was already in_progress and we're just touching it, use work_updated
    if status == "in_progress" and old == "in_progress":
        evt = "work_updated"
    _write_task_file(p, meta, body)
    rel = str(p.relative_to(COMPANY_ROOT)) if p.is_absolute() else str(p)
    append_event(
        actor=actor,
        event_type=evt,
        project=meta.get("project") or "",
        task_id=meta.get("id") or p.stem,
        title=f"Status: {old} → {status}",
        message=message or f"Status changed from {old} to {status}",
        status=status,
        source_file=rel,
    )
    print(f"[forge] status changed: {rel}  {old} → {status}  (event: {evt})")
    return meta


def list_tasks(project: Optional[str] = None, include_demo: bool = False,
               status: Optional[str] = None) -> List[Dict[str, str]]:
    """List parsed task frontmatters across projects."""
    out: List[Dict[str, str]] = []
    proj_roots = [COMPANY_ROOT / "01_projects"]
    for proj_root in proj_roots:
        if not proj_root.is_dir():
            continue
        for proj_dir in sorted(proj_root.iterdir()):
            if not proj_dir.is_dir() or proj_dir.name.startswith("."):
                continue
            if project and proj_dir.name != project:
                continue
            tasks_dir = proj_dir / "tasks"
            if not tasks_dir.is_dir():
                continue
            for tf in sorted(tasks_dir.glob("*.md")):
                try:
                    meta, _ = _read_task_file(tf)
                except Exception:
                    continue
                ds = (meta.get("data_source") or "").strip()
                if ds == "local-demo" and not include_demo:
                    continue
                if status and (meta.get("status") or "").lower() != status.lower():
                    continue
                meta["__path__"] = str(tf.relative_to(COMPANY_ROOT))
                out.append(meta)
    out.sort(key=lambda m: m.get("updated_at") or m.get("created_at") or "", reverse=True)
    return out


# ---------- CLI ----------

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="mc_event",
        description="NofiTech Mission Control task & event helper (stdlib only).",
    )
    sub = p.add_subparsers(dest="cmd", required=True)

    s_create = sub.add_parser("create-task", help="Create a new task file + event")
    s_create.add_argument("--project", required=True)
    s_create.add_argument("--title", required=True)
    s_create.add_argument("--created-by", required=True, choices=sorted(ALLOWED_ACTORS))
    s_create.add_argument("--assigned-to", required=True, choices=sorted(ALLOWED_ACTORS))
    s_create.add_argument("--priority", default="normal", choices=sorted(ALLOWED_PRIORITIES))
    s_create.add_argument("--description", default="")
    s_create.add_argument("--acceptance", default="")
    s_create.add_argument("--task-id", default="", help="Override auto id (e.g. MC-LIVE-TEST-001)")

    s_update = sub.add_parser("update", help="Update arbitrary frontmatter fields")
    s_update.add_argument("--task", required=True, help="Path to task .md file")
    s_update.add_argument("--set", action="append", default=[],
                          help="key=value pair (can be repeated)")

    s_assign = sub.add_parser("assign", help="Assign a task to an agent")
    s_assign.add_argument("--task", required=True)
    s_assign.add_argument("--assigned-to", required=True, choices=sorted(ALLOWED_ACTORS))
    s_assign.add_argument("--actor", default="thor", choices=sorted(ALLOWED_ACTORS))

    s_status = sub.add_parser("status", help="Set task status (with matching event)")
    s_status.add_argument("--task", required=True)
    s_status.add_argument("--status", required=True, choices=sorted(ALLOWED_STATUSES))
    s_status.add_argument("--actor", default="thor", choices=sorted(ALLOWED_ACTORS))
    s_status.add_argument("--message", default="")

    s_event = sub.add_parser("event", help="Append a free-form event")
    s_event.add_argument("--actor", required=True, choices=sorted(ALLOWED_ACTORS))
    s_event.add_argument("--event-type", required=True, choices=sorted(ALLOWED_EVENT_TYPES))
    s_event.add_argument("--project", default="")
    s_event.add_argument("--task-id", default="")
    s_event.add_argument("--title", default="")
    s_event.add_argument("--message", default="")
    s_event.add_argument("--status", default="")
    s_event.add_argument("--source-file", default="")

    s_list = sub.add_parser("list-tasks", help="List tasks")
    s_list.add_argument("--project", default=None)
    s_list.add_argument("--include-demo", action="store_true")
    s_list.add_argument("--status", default=None)

    return p


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)

    if args.cmd == "create-task":
        create_task(
            project=args.project,
            title=args.title,
            created_by=args.created_by,
            assigned_to=args.assigned_to,
            priority=args.priority,
            description=args.description,
            acceptance=args.acceptance,
            task_id=args.task_id,
        )
    elif args.cmd == "update":
        fields: Dict[str, str] = {}
        for kv in args.set:
            if "=" in kv:
                k, _, v = kv.partition("=")
                fields[k.strip()] = v
        if not fields:
            print("[forge] no --set key=value pairs given; nothing to do", file=sys.stderr)
            return 2
        update_task(args.task, **fields)
    elif args.cmd == "assign":
        assign_task(args.task, args.assigned_to, actor=args.actor)
    elif args.cmd == "status":
        set_status(args.task, args.status, actor=args.actor, message=args.message)
    elif args.cmd == "event":
        evt = append_event(
            actor=args.actor,
            event_type=args.event_type,
            project=args.project,
            task_id=args.task_id,
            title=args.title,
            message=args.message,
            status=args.status,
            source_file=args.source_file,
        )
        print(f"[forge] event appended: {evt['event_type']} ts={evt['ts']}")
    elif args.cmd == "list-tasks":
        rows = list_tasks(project=args.project, include_demo=args.include_demo, status=args.status)
        if not rows:
            print("[forge] no tasks matched", file=sys.stderr)
            return 0
        for r in rows:
            print(f"{r.get('id','?'):<24} {r.get('status','?'):<12} {r.get('assigned_to','?'):<8} {r.get('project','?')}  {r.get('title','')}")
    else:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
