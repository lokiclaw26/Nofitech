#!/usr/bin/env python3
"""
kanban_parser.py — parse NofiTech project task files into a kanban board dict.

MC-KANBAN-1 (2026-06-16): Hermes Agent Kanban tab in Mission Control.
3-agent team: Thor (CEO/Orchestrator), Forge (Builder/Engineer), Argus (QA/Tester).

Source of truth: 01_projects/*/tasks/*.md — same files the existing
/api/data/tasks endpoint reads. We do NOT use the external `hermes kanban`
CLI or ~/.hermes/kanban.db (those may not exist on this machine).

Status mapping (project file status → kanban status):
  triage       → triage
  in_progress  → running
  complete /
  done         → done
  blocked      → blocked
  pending /
  approved     → ready
  archived     → archived   (default hidden)
  todo         → todo
"""
from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

# Allowed kanban column ids (also used by the PATCH endpoint to validate input)
ALLOWED_STATUSES = ("triage", "todo", "ready", "running", "blocked", "done", "archived")

# Map project-file status strings → kanban status
STATUS_MAP = {
    "triage": "triage",
    "in_progress": "running",
    "in-progress": "running",
    "complete": "done",
    "done": "done",
    "blocked": "blocked",
    "pending": "ready",
    "approved": "ready",
    "archived": "archived",
    "todo": "todo",
    "assigned": "ready",   # legacy
    "open": "todo",        # legacy
    "verification": "running",  # in-verification == running
    "failed": "blocked",   # fail visually reads as blocked
}

# 3-agent team (locked charter v3.0, 2026-06-10)
AGENTS = [
    {"id": "thor",  "name": "Thor",  "emoji": "⚡", "role": "CEO / Orchestrator",
     "color": "var(--thor-color)"},
    {"id": "forge", "name": "Forge", "emoji": "🔨", "role": "Builder / Engineer",
     "color": "var(--forge-color)"},
    {"id": "argus", "name": "Argus", "emoji": "👁️", "role": "QA / Tester",
     "color": "var(--argus-color)"},
]
AGENT_IDS = [a["id"] for a in AGENTS]


# ---- frontmatter parsing (stdlib only) ----
def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Return (meta_dict, body_str). Tolerant of missing / malformed frontmatter.
    Values are stripped of surrounding quotes. Lists (YAML-flow or bracketed) are
    split on commas. Single-item lists are returned as a list of one."""
    if not text or not text.startswith("---\n"):
        return {}, text or ""
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fm = text[4:end]
    body = text[end + 5:]
    meta: dict = {}
    for line in fm.splitlines():
        if ":" not in line:
            continue
        k, _, v = line.partition(":")
        k = k.strip()
        v = v.strip()
        # strip surrounding quotes
        if len(v) >= 2 and v[0] == v[-1] and v[0] in ('"', "'"):
            v = v[1:-1]
        # list forms: [a, b, c]  or  a, b, c
        if v.startswith("[") and v.endswith("]"):
            inner = v[1:-1].strip()
            v = [x.strip().strip('"').strip("'") for x in inner.split(",") if x.strip()] if inner else []
        elif "," in v and not re.search(r"[A-Z]:", v):
            # heuristic: comma-separated only if it looks like a list, not e.g. an ISO date
            # ISO dates have a single T and no comma — this is safe
            parts = [x.strip().strip('"').strip("'") for x in v.split(",") if x.strip()]
            if len(parts) > 1:
                v = parts
        meta[k] = v
    return meta, body


def _read_text(path: Path) -> str | None:
    try:
        if not path.is_file():
            return None
        if path.stat().st_size > 256 * 1024:
            return None
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


# ---- primary task scan ----
def _iter_task_files(company_root: Path) -> list[Path]:
    """Return all *.md files under 01_projects/*/tasks/ and 00_company_os/*/tasks/
    that have frontmatter containing a `task_id:` line (filter empty placeholders)."""
    out: list[Path] = []
    roots = [company_root / "01_projects"]
    roots.append(company_root / "00_company_os")
    for root in roots:
        if not root.is_dir():
            continue
        for td in root.glob("*/tasks"):
            if not td.is_dir():
                continue
            for tf in sorted(td.glob("*.md")):
                txt = _read_text(tf)
                if not txt:
                    continue
                if "task_id:" in txt[:1000]:  # frontmatter is near the top
                    out.append(tf)
    return out


def _normalize_status(raw: str) -> str:
    return STATUS_MAP.get((raw or "").strip().lower(), "triage")


def _normalize_assignee(raw) -> str | None:
    """Frontmatter `assigned_to` may be a string ("forge"), a list (["forge", "argus"]),
    or comma-separated. Kanban needs a single primary assignee per card; we use
    the first agent in the list that matches the 3-agent team, else None."""
    if raw is None:
        return None
    if isinstance(raw, list):
        items = [str(x).strip().lower() for x in raw]
    else:
        s = str(raw).strip()
        if s.startswith("[") and s.endswith("]"):
            s = s[1:-1]
        items = [x.strip().strip('"').strip("'").lower() for x in s.split(",") if x.strip()]
    for item in items:
        if item in AGENT_IDS:
            return item
    return None


def _card_from_task_file(tf: Path, company_root: Path) -> dict | None:
    txt = _read_text(tf)
    if not txt:
        return None
    meta, body = parse_frontmatter(txt)
    task_id = (meta.get("task_id") or tf.stem).strip()
    if not task_id:
        return None
    status_raw = (meta.get("status") or "").strip().lower()
    status = _normalize_status(status_raw)
    priority = (meta.get("priority") or "normal").strip().lower()
    created = (meta.get("created") or meta.get("created_at") or "").strip() or None
    assignee = _normalize_assignee(meta.get("assigned_to"))
    current_assignment = (meta.get("current_assignment") or "").strip() or None
    title = (meta.get("title") or tf.stem).strip()
    approval_status = (meta.get("approval_status") or "").strip().lower() or None
    project = (meta.get("project") or tf.parent.parent.name).strip()
    body_first_line = ""
    for line in (body or "").splitlines():
        s = line.strip()
        if s and not s.startswith("#"):
            body_first_line = s[:120]
            break
    return {
        "task_id": task_id,
        "title": title,
        "status": status,
        "status_raw": status_raw or "triage",
        "priority": priority,
        "created": created,
        "assignee": assignee,
        "current_assignment": current_assignment,
        "approval_status": approval_status,
        "project": project,
        "preview": body_first_line,
        "body": (body or "").strip(),
        "path": str(tf.relative_to(company_root)),
    }


# ---- public board builder ----
def build_board(company_root: Path, include_archived: bool = False) -> dict:
    """Build the full kanban board dict. Filters archived unless include_archived
    is True. Always returns all 6 columns (some may be empty)."""
    columns = ["triage", "todo", "ready", "running", "blocked", "done", "archived"]
    cols = {c: [] for c in columns}

    # Per-status counts (BEFORE archived filter — caller decides visibility)
    all_cards: list[dict] = []
    for tf in _iter_task_files(company_root):
        card = _card_from_task_file(tf, company_root)
        if card is None:
            continue
        all_cards.append(card)
        if card["status"] in cols:
            cols[card["status"]].append(card)

    # Counts
    by_status = {c: len(cols[c]) for c in columns}
    by_assignee = {a: 0 for a in AGENT_IDS}
    for c in all_cards:
        if c["assignee"] in by_assignee:
            by_assignee[c["assignee"]] += 1

    # Sort cards inside each column by created desc (most recent first)
    def _created_key(card: dict) -> str:
        return card.get("created") or ""
    for c in columns:
        cols[c].sort(key=_created_key, reverse=True)

    # Build the visible columns list (excludes archived unless asked)
    visible_statuses = list(columns)
    if not include_archived:
        visible_statuses = [c for c in visible_statuses if c != "archived"]

    column_meta = {
        "triage":  {"id": "triage",  "label": "Triage"},
        "todo":    {"id": "todo",    "label": "Todo"},
        "ready":   {"id": "ready",   "label": "Ready"},
        "running": {"id": "running", "label": "Running"},
        "blocked": {"id": "blocked", "label": "Blocked"},
        "done":    {"id": "done",    "label": "Done"},
        "archived":{"id": "archived","label": "Archived"},
    }
    out_columns = []
    for c in visible_statuses:
        col = {
            "id": c,
            "label": column_meta[c]["label"],
            "count": by_status[c],
            "tasks": cols[c],
        }
        if c == "running":
            lanes = []
            for a in AGENTS:
                lane_tasks = [card for card in cols["running"] if card.get("assignee") == a["id"]]
                lanes.append({
                    "assignee": a["id"],
                    "name": a["name"],
                    "emoji": a["emoji"],
                    "count": len(lane_tasks),
                    "tasks": lane_tasks,
                })
            # also catch any running tasks that don't match the 3-agent team
            assigned_ids = set(AGENT_IDS)
            orphan = [card for card in cols["running"] if card.get("assignee") not in assigned_ids]
            if orphan:
                lanes.append({
                    "assignee": "unassigned",
                    "name": "Unassigned",
                    "emoji": "❓",
                    "count": len(orphan),
                    "tasks": orphan,
                })
            col["lanes"] = lanes
        out_columns.append(col)

    return {
        "columns": out_columns,
        "agents": AGENTS,
        "summary": {
            "total": len(all_cards),
            "visible": sum(by_status[c] for c in visible_statuses),
            "by_status": by_status,
            "by_assignee": by_assignee,
        },
        "include_archived": include_archived,
    }


# ---- file mutation (PATCH) ----
def _split_frontmatter(text: str) -> tuple[list[str], list[str], str]:
    """Return (header_lines, body_lines, trailing) where header_lines is the
    list of lines INSIDE the frontmatter (no --- markers), body_lines is the
    post-frontmatter body, and trailing is whatever comes after the body.

    If there is no frontmatter, return ([], text.splitlines(), '')."""
    if not text or not text.startswith("---\n"):
        return [], text.splitlines() if text else [], ""
    end = text.find("\n---\n", 4)
    if end < 0:
        # malformed — treat whole file as body
        return [], text.splitlines(), ""
    fm = text[4:end]
    body = text[end + 5:]
    return fm.splitlines(), body.splitlines(), ""


def update_task_status(task_id: str, new_status: str, company_root: Path) -> tuple[bool, str, Path | None]:
    """Update the frontmatter `status` field of the task file matching `task_id`.
    Preserves the rest of the frontmatter + body. Returns (ok, reason, file_path).

    Rejects:
      - unknown status (returns ok=False, reason='unknown status')
      - unknown task_id (returns ok=False, reason='task not found')
    """
    if new_status not in ALLOWED_STATUSES:
        return False, f"unknown status: {new_status!r}", None
    target: Path | None = None
    for tf in _iter_task_files(company_root):
        if tf.stem == task_id or tf.name == f"{task_id}.md":
            target = tf
            break
        # also try matching by frontmatter task_id (in case filename != task_id)
        txt = _read_text(tf)
        if not txt:
            continue
        meta, _ = parse_frontmatter(txt)
        if (meta.get("task_id") or "").strip() == task_id:
            target = tf
            break
    if target is None:
        return False, f"task_id not found: {task_id!r}", None
    txt = target.read_text(encoding="utf-8")
    header, body, _ = _split_frontmatter(txt)
    if not header:
        # no frontmatter — inject a minimal one
        new_fm = [
            f"task_id: {task_id}",
            f"status: {new_status}",
        ]
        out = "---\n" + "\n".join(new_fm) + "\n---\n" + "\n".join(body) + ("\n" if body and not body[-1] else "")
        if not out.endswith("\n"):
            out += "\n"
        target.write_text(out, encoding="utf-8")
        return True, "ok (frontmatter was missing — injected)", target
    # Update / insert the status line
    new_header = []
    status_replaced = False
    for line in header:
        # Match `status: ...` at the start of the line (preserve any trailing comment)
        m = re.match(r'^(\s*status\s*:\s*)(.*?)(\s*(?:#.*)?)$', line)
        if m:
            new_header.append(f"{m.group(1)}{new_status}{m.group(3)}")
            status_replaced = True
        else:
            new_header.append(line)
    if not status_replaced:
        new_header.append(f"status: {new_status}")
    out = "---\n" + "\n".join(new_header) + "\n---\n" + "\n".join(body)
    if not out.endswith("\n"):
        out += "\n"
    target.write_text(out, encoding="utf-8")
    return True, "ok", target


# ---- file creation (POST) ----
def create_task_file(task_id: str, title: str, assignee: str, priority: str,
                     company_root: Path) -> tuple[bool, str, Path | None]:
    """Create a new task file at 01_projects/mission-control/tasks/<task_id>.md
    with the standard frontmatter. Returns (ok, reason, path)."""
    if assignee not in AGENT_IDS:
        return False, f"unknown assignee: {assignee!r}", None
    safe_id = re.sub(r"[^A-Za-z0-9_.\-]", "-", task_id).strip("-") or f"MC-{int(__import__('time').time())}"
    project_tasks = company_root / "01_projects" / "mission-control" / "tasks"
    project_tasks.mkdir(parents=True, exist_ok=True)
    target = project_tasks / f"{safe_id}.md"
    if target.exists():
        return False, f"file already exists: {target}", None
    from datetime import datetime, timezone
    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S+00:00")
    fm_lines = [
        f"task_id: {safe_id}",
        f"title: {title}",
        "project: mission-control",
        "status: triage",
        f"priority: {priority or 'normal'}",
        f"created: {now_iso}",
        "created_by: thor",
        f"assigned_to: [{assignee}]",
        f"current_assignment: {safe_id}",
        "approval_required: true",
        "approval_status: pending",
    ]
    body = f"\n# {title}\n\n(Body TBD — created via Mission Control Kanban UI on {now_iso}.)\n"
    target.write_text("---\n" + "\n".join(fm_lines) + "\n---\n" + body, encoding="utf-8")
    return True, "ok", target


# ---- CLI (for debugging) ----
def _main():
    import json
    company_root = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(__file__).parent.parent.parent
    include_archived = "--archived" in sys.argv
    board = build_board(company_root, include_archived=include_archived)
    print(json.dumps(board, indent=2, default=str)[:6000])


if __name__ == "__main__":
    _main()
