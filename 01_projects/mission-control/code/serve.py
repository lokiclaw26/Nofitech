#!/usr/bin/env python3
"""
NofiTech Mission Control v1.9.0 (Stage 14 — auto task+event wiring)
Local-only dashboard for NOFI. 3-agent company. 6 sections.
Stage 9: Logs/Health panel with 7 fields (events, errors, warnings, app/api health, last verification, env status).
Stage 11: stabilization — task filter (demo/real), auto-detect LAN IP, LAN warning banner.
Stage 12: live data only — demo tasks hidden by default (?include=demo opt-in),
          strict log level detection (explicit `level:` only, no body inference),
          real projects only, "Last refreshed" timestamp, v1.8.0 bump.
Stage 14: automatic task and event wiring — data_tasks() reads 14-field
          frontmatter for real tasks; data_overview() counts only real
          tasks; new /api/data/events endpoint serves events.jsonl;
          data_logs() merges events.jsonl into the Logs/Health panel.
Stage 17: Provider/Model panel retired from the HTML; new Warnings panel
          with fix-order buttons (POST /api/data/order). The /api/data/provider
          endpoint is still served for any hidden API consumer.
Stage 20 (2026-06-16): added Section 9 "GitHub Connection" — new endpoint
          /api/data/github reads git remote, GitHub API, last cron run, and
          last_run.json. Additive only — no changes to existing endpoints.
MC-KANBAN-1 (2026-06-16): added Section 10 "Kanban — Multi-Agent Board" —
          3 endpoints serve the Hermes Agent Kanban tab (NOFI's 3-agent team:
          Thor/Forge/Argus). Reads the same project task files already on
          disk; no external kanban.db, no pip deps.
MC-KANBAN-2 (2026-06-16): dual-format parser. kanban_parser now reads BOTH
          YAML frontmatter (Format A) and markdown `| Field | Value |` tables
          (Format B). PATCH writes a SEPARATE `kanban_status` field instead
          of overwriting the project-native `status` field (data-loss fix).

Endpoints:
  GET  /                              → static HTML
  GET  /mission-control.html          → static HTML (alt)
  GET  /api/health                    → {status, version, uptime_sec}
  GET  /api/version                   → {version, commit, uptime_sec, started_at, lan_ip, port}
  GET  /api/data/overview             → 6 fields, real or null+reason
  GET  /api/data/agents               → 3 rows: thor, forge, argus
  GET  /api/data/tasks                → real tasks by default; ?include=demo to also show demo
  GET  /api/data/projects             → 0+ rows from 01_projects/*/status.md
  GET  /api/data/provider             → 2 rows: free, paid  (panel retired; endpoint kept)
  GET  /api/data/logs                 → events + health + env + jsonl_events
  GET  /api/data/github               → git remote + GitHub API + last cron run (Stage 20)
  GET  /api/data/events               → last 50 events from events.jsonl
  POST /api/data/order                → append a fix_order event to events.jsonl (Stage 17→19)
  GET  /api/data/orders               → list pending/in_progress fix_order events (Stage 19)
  GET  /api/data/kanban               → full board grouped by status + 3-agent lanes (MC-KANBAN-1)
  PATCH /api/data/kanban/task/:id     → update task status on disk (MC-KANBAN-1)
  POST  /api/data/kanban/task         → create a new task file from the UI (MC-KANBAN-1)
  PATCH /api/data/kanban/task/:id/assign → update task assignee on disk (MC-KANBAN-ASSIGN-1)
"""
import http.server
import socketserver
import json
import os
import re
import time
import urllib.parse
import urllib.request
import glob
import socket
import subprocess
import uuid
from pathlib import Path
from datetime import datetime, timezone

# MC-KANBAN-1 (2026-06-16): 3-endpoint Kanban tab.
# Imported here so the board parser lives next to the static HTML/JS that
# renders it. The parser reads the SAME project task files that the existing
# /api/data/tasks endpoint already scans, so no DB is introduced.
import kanban_parser  # noqa: E402  (intentional local import — keeps top of file clean)

PORT = 8767
HOST = "0.0.0.0"  # v1.3.0 — full LAN access (reversed Stage-1 'local only' lock per NOFI directive)
HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent              # 01_projects/mission-control
COMPANY_ROOT = PROJECT_ROOT.parent.parent  # ~/NofiTech-Ind
START_TIME = time.time()

# v1.10.0 — live version: read from git at request time (no restart needed).
# Fallback to manual values if git is unavailable or this is a fresh checkout.
FALLBACK_VERSION = "1.10.0"
FALLBACK_COMMIT = "live"

def _git(*args):
    try:
        out = subprocess.run(
            ["git", "-C", str(COMPANY_ROOT), *args],
            capture_output=True, text=True, timeout=2
        )
        return out.stdout.strip() if out.returncode == 0 else ""
    except Exception:
        return ""

def get_version():
    """Read version + commit from git tags/HEAD at call time. Falls back to constants."""
    # Prefer: latest annotated tag matching 'mission-control-v*'
    tag = _git("describe", "--tags", "--abbrev=0", "--match", "mission-control-v*")
    head_short = _git("rev-parse", "--short", "HEAD")
    head_long = _git("rev-parse", "HEAD")
    dirty = _git("status", "--porcelain")
    branch = _git("rev-parse", "--abbrev-ref", "HEAD")
    if tag:
        # tag looks like "mission-control-v1.10.0-ui-ux" — strip prefix
        ver = tag.replace("mission-control-", "")
        commit = ver + (f"+{head_short}-dirty" if dirty else f" @ {head_short}")
    elif head_short:
        ver = FALLBACK_VERSION
        commit = head_short + ("-dirty" if dirty else "")
    else:
        ver = FALLBACK_VERSION
        commit = FALLBACK_COMMIT
    return {
        "version": ver,
        "commit": commit,
        "commit_full": head_long or None,
        "branch": branch or None,
        "dirty": bool(dirty),
        "tag": tag or None,
    }

# ---- 3-agent company (locked 2026-06-10, charter v3.0) ----
AGENTS = ["thor", "forge", "argus"]

AGENT_META = {
    "thor":  {"name": "Thor",  "role": "CEO / Planner / Coordinator", "emoji": "⚡"},
    "forge": {"name": "Forge", "role": "Builder / Engineer / DevOps", "emoji": "🔨"},
    "argus": {"name": "Argus", "role": "QA / Tester / Security",       "emoji": "👁️"},
}


# ---- MC-MEMORY-GRAPH-1 (2026-06-17): Memory Graph page integration ----
# Locked decisions: Python stdlib only, JSON on disk, polling for realtime.
# Event contract: {type, ...payload} where type ∈ {node.upsert, edge.upsert,
# memory.snapshot, node.delete, edge.delete}. Nodes keyed by stable id; edges
# get stable id `edge-<source>-target-<kind>` for idempotent upsert. The
# append-only event log lives next to the snapshot file.
MG_DATA_DIR = PROJECT_ROOT / "data"
MG_GRAPH_PATH = MG_DATA_DIR / "memory-graph.json"
MG_EVENTS_PATH = MG_DATA_DIR / "memory-graph-events.jsonl"
MG_SAMPLE_PATH = MG_DATA_DIR / "sample-graph.json"
MG_EVENT_LOG_MAX_LINES = 10_000
MG_NODE_KINDS = {
    "goal", "task", "memory", "decision", "tool", "file",
    "error", "concept", "entity", "session", "message",
}
MG_VALID_EVENT_TYPES = {
    "node.upsert", "edge.upsert", "memory.snapshot",
    "node.delete", "edge.delete",
}


# ---------- helpers ----------

def _detect_lan_ip():
    """Detect primary outbound LAN IP via UDP-socket trick.
    Opens a UDP socket, 'connects' to 8.8.8.8:80 (no packet sent), reads
    the local endpoint the OS assigned, closes. Falls back to 127.0.0.1.
    Returns (ip, ok) tuple so callers can show a banner on failure."""
    s = None
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.3)
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0], True
    except Exception:
        return "127.0.0.1", False
    finally:
        if s:
            try: s.close()
            except Exception: pass


# Detect once at import time so the value is stable across requests.
# Stage 16: also seed the per-request fallback cache with the import-time value,
# so a later transient detection failure still returns SOMETHING sensible.
HOST_IP, _LAN_IP_OK = _detect_lan_ip()
_last_known_lan_ip = HOST_IP  # cache for get_lan_ip() fallback


def get_lan_ip():
    """Stage 16: per-request LAN IP detection with last-known-good fallback.

    Tries to re-detect the outbound LAN IP (handles DHCP/VPN/network switch
    mid-session). On any failure, returns the cached `_last_known_lan_ip`
    so the dashboard never goes blank. As a side effect, updates the cache
    on success so subsequent failures degrade to the freshest good value.
    """
    global _last_known_lan_ip
    try:
        ip, ok = _detect_lan_ip()
    except Exception:
        return _last_known_lan_ip
    if ok and ip:
        _last_known_lan_ip = ip
        return ip
    return _last_known_lan_ip


def safe_read(path, max_bytes=256 * 1024):
    try:
        p = Path(path)
        if not p.is_file():
            return None
        if p.stat().st_size > max_bytes:
            return None
        return p.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return None


def parse_frontmatter(text):
    """Returns (meta_dict, body_str). Empty meta if no frontmatter."""
    if not text or not text.startswith("---\n"):
        return {}, text or ""
    end = text.find("\n---\n", 4)
    if end < 0:
        return {}, text
    fm = text[4:end]
    body = text[end + 5:]
    meta = {}
    for line in fm.splitlines():
        if ":" in line:
            k, _, v = line.partition(":")
            meta[k.strip()] = v.strip().strip('"').strip("'")
    return meta, body


def safe_join(root, requested):
    """Resolve a path under root, raise if it escapes."""
    rel = os.path.normpath(requested or ".").lstrip("/")
    if rel in ("", "."):
        return str(root)
    full = os.path.abspath(os.path.join(str(root), rel))
    if not (full == str(root) or full.startswith(str(root) + os.sep)):
        raise ValueError("Path escapes root")
    return full


def list_subdirs(root):
    p = Path(root)
    if not p.is_dir():
        return []
    return sorted([d.name for d in p.iterdir() if d.is_dir() and not d.name.startswith(".")])


def list_files(root, pattern):
    p = Path(root)
    if not p.is_dir():
        return []
    return sorted(p.glob(pattern), key=lambda x: x.stat().st_mtime, reverse=True)


def rel_time(iso_or_mtime):
    """Return 'Xm ago' / 'Xh ago' / 'Xd ago' or '—'."""
    try:
        if isinstance(iso_or_mtime, (int, float)):
            dt = datetime.fromtimestamp(iso_or_mtime, tz=timezone.utc)
        else:
            dt = datetime.fromisoformat(str(iso_or_mtime).replace("Z", "+00:00"))
        diff = (datetime.now(timezone.utc) - dt).total_seconds()
        if diff < 0:
            return "now"
        if diff < 60:
            return f"{int(diff)}s ago"
        if diff < 3600:
            return f"{int(diff // 60)}m ago"
        if diff < 86400:
            return f"{int(diff // 3600)}h ago"
        return f"{int(diff // 86400)}d ago"
    except Exception:
        return "—"


# ---------- data endpoints ----------

def data_overview():
    """6 fields, each real or null+reason. Stage 4 added warnings."""
    out = {}

    # 1. Hermes status: probe the gateway (best-effort) + report uptime
    try:
        # Light probe: check that ~/.hermes/ exists and has a config
        cfg = Path.home() / ".hermes" / "config.yaml"
        out["hermes_status"] = {
            "value": "ok" if cfg.exists() else "unknown",
            "reason": None if cfg.exists() else "no ~/.hermes/config.yaml",
        }
    except Exception as e:
        out["hermes_status"] = {"value": None, "reason": str(e)}

    # 2. Current project: first subdir of 01_projects/ (or null)
    projects = list_subdirs(COMPANY_ROOT / "01_projects")
    if projects:
        out["current_project"] = {
            "value": projects[0],
            "reason": None,
        }
    else:
        out["current_project"] = {
            "value": None,
            "reason": "no projects yet — 01_projects/ is empty",
        }

    # 3. Active tasks count: tasks with status in the active set across all
    #    REAL projects (data_source=real). Stage 14 schema: assigned,
    #    in_progress, verification. We also keep the legacy 'in-progress'
    #    mapping for backward compatibility with any older real tasks.
    active = 0
    failed = 0
    blocked = 0
    total = 0
    active_statuses = {"assigned", "in_progress", "in-progress", "verification", "triage"}
    failed_statuses = {"failed"}
    blocked_statuses = {"blocked"}
    tasks_dirs = list((COMPANY_ROOT / "01_projects").glob("*/tasks"))
    for td in tasks_dirs:
        for tf in td.glob("*.md"):
            txt = safe_read(tf)
            if not txt:
                continue
            meta, _ = parse_frontmatter(txt)
            # Stage 14: only count REAL tasks toward active/failed/blocked.
            # Demo tasks (data_source: local-demo) are excluded from these
            # top-level counters — they were authored for the Stage 6 demo
            # and the Stage 12 lock hides them from the main dashboard.
            ds = (meta.get("data_source") or "").strip().lower()
            if ds != "real":
                continue
            total += 1
            st = (meta.get("status") or "").lower()
            if st in active_statuses:
                active += 1
            if st in failed_statuses:
                failed += 1
            if st in blocked_statuses:
                blocked += 1
    out["active_tasks"] = {
        "value": active if total else None,
        "reason": None if total else "no real tasks yet",
    }
    out["failed_tasks"] = {
        "value": failed if total else None,
        "reason": None if total else "no real tasks yet",
    }

    # 3b. Warnings: count tasks with status=blocked (UI badge uses WARN color)
    #     and log files containing level=warn. Two sources, same semantic.
    log_warnings = 0
    logs_root = COMPANY_ROOT / "00_company_os" / "04_agents" / "logs"
    if logs_root.is_dir():
        for f in logs_root.rglob("*.md"):
            txt = safe_read(f)
            if not txt:
                continue
            meta, _ = parse_frontmatter(txt)
            if (meta.get("level") or "").lower() == "warn":
                log_warnings += 1
    warnings = blocked + log_warnings
    have_any_source = bool(tasks_dirs) or logs_root.is_dir()
    out["warnings"] = {
        "value": warnings if have_any_source else None,
        "reason": None if have_any_source else "no tasks or log files yet",
        "breakdown": {"blocked_tasks": blocked, "log_warns": log_warnings},
    }

    # 4. Last check time: most recent memory-log entry, else last agent log, else null
    last_iso = None
    mem_log = safe_read(COMPANY_ROOT / "00_company_os" / "memory-log.md")
    if mem_log:
        # Find most recent ### entry
        m = re.findall(r"### \d+\..*?- \*\*When:\*\* (\S+ \S+)", mem_log)
        if m:
            try:
                last_iso = datetime.strptime(m[0], "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).isoformat()
            except Exception:
                pass
    if not last_iso:
        # fallback: most recent agent log mtime
        logs_root = COMPANY_ROOT / "00_company_os" / "04_agents" / "logs"
        if logs_root.is_dir():
            latest = None
            for f in logs_root.rglob("*.md"):
                mt = f.stat().st_mtime
                if latest is None or mt > latest[0]:
                    latest = (mt, f)
            if latest:
                last_iso = datetime.fromtimestamp(latest[0], tz=timezone.utc).isoformat()
    if last_iso:
        out["last_check"] = {"value": last_iso, "reason": None, "rel": rel_time(last_iso)}
    else:
        out["last_check"] = {"value": None, "reason": "no log entries yet"}

    return out


def _read_agent_state():
    """Read 00_company_os/04_agents/state.json if present. Returns dict or {}."""
    p = COMPANY_ROOT / "00_company_os" / "04_agents" / "state.json"
    txt = safe_read(p)
    if not txt:
        return {}
    try:
        d = json.loads(txt)
        if not isinstance(d, dict):
            return {}
        return d
    except Exception:
        return {}


def data_agents():
    """3 rows: thor, forge, argus.
    Sources of truth (in priority order):
      1. state.json → status, current_assignment, blocker
      2. 04_agents/logs/<oid>-*.md mtime → last activity (real log file)
      3. state.json 'updated' timestamp → last activity fallback (e.g. for thor who has no log file)
    """
    state = _read_agent_state()
    agent_state = state.get("agents", {}) if isinstance(state.get("agents"), dict) else {}
    state_updated_mtime = None
    sp = COMPANY_ROOT / "00_company_os" / "04_agents" / "state.json"
    if sp.is_file():
        state_updated_mtime = sp.stat().st_mtime

    logs_root = COMPANY_ROOT / "00_company_os" / "04_agents" / "logs"
    rows = []
    for oid in AGENTS:
        meta = AGENT_META[oid]
        ast = agent_state.get(oid, {}) if isinstance(agent_state.get(oid), dict) else {}

        # ---- last activity (real file mtime) ----
        last_mtime = None
        last_file = None
        if logs_root.is_dir():
            # Match BOTH the canonical convention (<oid>-*.md) AND legacy files
            # that contain the agent name anywhere (e.g. test-warn-argus.md from Stage 4).
            # We dedupe via a set to avoid double-counting files that match both.
            seen = set()
            for pattern in (f"{oid}-*.md", f"*-{oid}-*.md", f"*{oid}*.md"):
                for f in logs_root.rglob(pattern):
                    if f in seen:
                        continue
                    seen.add(f)
                    mt = f.stat().st_mtime
                    if last_mtime is None or mt > last_mtime:
                        last_mtime = mt
                        last_file = f
        # For thor (the CEO agent), also count the state.json itself as activity
        # ONLY if the state has an entry for thor with status=active.
        # This is honest because thor literally wrote that file.
        if oid == "thor" and state_updated_mtime and ast.get("status") == "active":
            if last_mtime is None or state_updated_mtime > last_mtime:
                # Use state.json as the last_activity timestamp source
                last_mtime = state_updated_mtime
                last_file = sp

        # ---- status ----
        status = ast.get("status") or ("active" if last_mtime and (time.time() - last_mtime) < 86400 else ("idle" if last_mtime else "never-active"))
        # Auto-derive: if status is 'active' but last activity is > 24h, demote to 'idle'.
        if status == "active" and last_mtime and (time.time() - last_mtime) >= 86400:
            status = "idle"

        # ---- current assignment + blocker ----
        current_assignment = ast.get("current_assignment") or None
        blocker = ast.get("blocker") or None
        # If current_assignment is empty string, treat as None
        if current_assignment == "":
            current_assignment = None
        if blocker == "":
            blocker = None

        # ---- reason for unavailable fields ----
        reasons = []
        if not last_mtime and status == "never-active":
            reasons.append("no log files yet for this agent")
        if current_assignment is None:
            reasons.append("no current assignment")
        if blocker is None:
            reasons.append("no blocker")

        # ---- MC-AGENT-LOG-FIX-1: expose mtime_iso + mtime_age_seconds so the
        # frontend can decide its own "stuck" threshold. Stale = no fresh log
        # in 30+ min AND agent claims to be spawning/in_progress (i.e. should
        # be writing logs but isn't).
        if last_mtime:
            mtime_iso = datetime.fromtimestamp(last_mtime, tz=timezone.utc).isoformat()
            mtime_age_seconds = int(time.time() - last_mtime)
        else:
            mtime_iso = None
            mtime_age_seconds = None
        STUCK_STATUSES = {"spawning", "in_progress", "in-progress"}
        stale = bool(
            mtime_age_seconds is not None
            and mtime_age_seconds > 30 * 60
            and status in STUCK_STATUSES
        )

        rows.append({
            "id": oid,
            "name": meta["name"],
            "role": meta["role"],
            "emoji": meta["emoji"],
            "status": status,
            "last_activity": rel_time(last_mtime) if last_mtime else "—",
            "last_activity_iso": mtime_iso,
            "mtime_iso": mtime_iso,
            "mtime_age_seconds": mtime_age_seconds,
            "stale": stale,
            "last_log": str(last_file.relative_to(COMPANY_ROOT)) if last_file else None,
            "current_assignment": current_assignment,
            "blocker": blocker,
            "reasons": reasons,
        })
    return {"agents": rows, "count": len(rows)}


def data_tasks(include_demo=False):
    """All tasks across all projects. By default, EXCLUDES demo data.
    Pass include_demo=True to also include local-demo tasks.
    A task is "demo" if its frontmatter has data_source: local-demo.
    Stage 12: live-data dashboard — demo is opt-in via ?include=demo.
    Stage 14: returns the full 14-field schema for real tasks; legacy
    Stage 6 demo tasks get a 'description' / 'evidence' / 'argus_result'
    passthrough so they still render the same way as before.
    """
    rows = []
    tasks_dirs = sorted((COMPANY_ROOT / "01_projects").glob("*/tasks"))
    for td in tasks_dirs:
        for tf in td.glob("*.md"):
            txt = safe_read(tf)
            if not txt:
                continue
            meta, body = parse_frontmatter(txt)
            ds = (meta.get("data_source") or "").strip()
            if ds == "local-demo" and not include_demo:
                continue  # hide demo from main dashboard (Stage 12)

            is_real = ds == "real"
            if is_real:
                # Stage 14 schema — 14 fields. Use '—' for missing values
                # so the UI never renders an empty cell.
                def _or_dash(v):
                    return v if (v is not None and str(v).strip() not in ("", "none")) else "—"
                rows.append({
                    "id": meta.get("id") or tf.stem,
                    "title": meta.get("title") or tf.stem,
                    "project": meta.get("project") or td.parent.name,
                    "created_by": _or_dash(meta.get("created_by") or meta.get("agent")),
                    "assigned_to": _or_dash(meta.get("assigned_to") or meta.get("agent")),
                    "status": (meta.get("status") or "triage").lower(),
                    "priority": (meta.get("priority") or "normal").lower(),
                    "created": _or_dash(meta.get("created_at") or meta.get("created")),
                    "updated": _or_dash(meta.get("updated_at") or meta.get("updated")),
                    "created_at": _or_dash(meta.get("created_at")),
                    "updated_at": _or_dash(meta.get("updated_at")),
                    "current_stage": _or_dash(meta.get("current_stage")),
                    "blocker": _or_dash(meta.get("blocker") or meta.get("blockers")),
                    "description": meta.get("description") or "",
                    "acceptance": meta.get("acceptance") or "",
                    "evidence": meta.get("evidence") or "none",
                    "argus_result": meta.get("argus_result") or "pending",
                    "data_source": "real",
                    "path": str(tf.relative_to(COMPANY_ROOT)),
                })
            else:
                # Legacy / demo shape — keep the old render path intact.
                rows.append({
                    "id": meta.get("id") or tf.stem,
                    "title": meta.get("title") or tf.stem,
                    "project": meta.get("project") or td.parent.name,
                    "agent": meta.get("agent") or "—",
                    "status": meta.get("status") or "open",
                    "priority": meta.get("priority") or "P2",
                    "created": meta.get("created") or "—",
                    "updated": meta.get("updated") or "—",
                    "description": meta.get("description") or "",
                    "evidence": meta.get("evidence") or "none",
                    "blockers": meta.get("blockers") or "",
                    "argus_result": meta.get("argus_result") or "pending",
                    "data_source": meta.get("data_source") or "",
                    "path": str(tf.relative_to(COMPANY_ROOT)),
                })
    rows.sort(key=lambda r: r.get("updated") or r.get("updated_at") or "", reverse=True)
    sources = set()
    for r in rows:
        if r.get("data_source"):
            sources.add(r["data_source"])
    return {
        "tasks": rows,
        "count": len(rows),
        "data_sources": sorted(sources) if sources else [],
        "include_demo": include_demo,
        "reason": None if rows else "No real tasks yet.",
    }


# ---------- GitHub Connection (Section 9, added 2026-06-16 FORGE/NOFI directive) ----------

def data_github():
    """GitHub connection status + cron job state.
    Reads:
      - git remote origin URL
      - GitHub API for repo info (if token available)
      - git log for unpushed commits
      - ~/.hermes/cron-output/github-push-nofitech/last_run.json
      - hermes cron list (parsed for next run)
    Additive — does not modify any existing endpoint or function.
    """
    out = {"ts": datetime.now(tz=timezone.utc).isoformat(), "errors": []}

    # ---- repo info ----
    out["repo"] = {"url": "", "visibility": "?", "last_push_at": None,
                   "total_commits_on_main": 0, "description": ""}
    try:
        r = subprocess.run(
            ["git", "-C", str(COMPANY_ROOT), "remote", "get-url", "origin"],
            capture_output=True, text=True, timeout=5,
        )
        out["repo"]["url"] = r.stdout.strip()
    except Exception as e:
        out["errors"].append(f"git remote failed: {e}")

    # GitHub API (if token)
    env_file = Path.home() / ".hermes" / "scripts" / ".env.github"
    if env_file.exists():
        try:
            env = {}
            for line in env_file.read_text().splitlines():
                if "=" in line and not line.startswith("#"):
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip()
            token = env.get("GITHUB_TOKEN", "")
            # Parse owner/repo from URL
            url = out["repo"]["url"]
            if "github.com/" in url:
                owner_repo = url.split("github.com/")[-1].rstrip(".git").rstrip("/")
                if "/" in owner_repo:
                    owner, repo = owner_repo.split("/", 1)
                    api_url = f"https://api.github.com/repos/{owner}/{repo}"
                    req = urllib.request.Request(api_url, headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github+json",
                        "User-Agent": "nofitech-mission-control",
                    })
                    try:
                        with urllib.request.urlopen(req, timeout=5) as r:
                            data = json.loads(r.read())
                            out["repo"]["visibility"] = data.get("visibility", "?")
                            out["repo"]["last_push_at"] = data.get("pushed_at")
                            out["repo"]["description"] = data.get("description", "")
                            # default_branch + size
                            out["repo"]["default_branch"] = data.get("default_branch", "?")
                            out["repo"]["size_kb"] = data.get("size", 0)
                            out["repo"]["stars"] = data.get("stargazers_count", 0)
                            out["repo"]["open_issues"] = data.get("open_issues_count", 0)
                    except Exception as api_e:
                        out["errors"].append(f"github api repo: {api_e}")
        except Exception as e:
            out["errors"].append(f"github api: {e}")

    # ---- local state ----
    out["local"] = {"branch": "?", "last_commit_sha": "", "last_commit_msg": "",
                    "unpushed_commits": 0}
    try:
        r = subprocess.run(
            ["git", "-C", str(COMPANY_ROOT), "branch", "--show-current"],
            capture_output=True, text=True, timeout=5,
        )
        out["local"]["branch"] = r.stdout.strip() or "(detached)"
    except Exception:
        pass
    try:
        r = subprocess.run(
            ["git", "-C", str(COMPANY_ROOT), "log", "-1", "--format=%H|%s"],
            capture_output=True, text=True, timeout=5,
        )
        parts = r.stdout.strip().split("|", 1)
        if parts and parts[0]:
            out["local"]["last_commit_sha"] = parts[0]
            out["local"]["last_commit_msg"] = parts[1] if len(parts) > 1 else ""
    except Exception:
        pass
    # Unpushed commits — try origin/<branch>, then fall back to 0 if ref not found
    try:
        branch = out["local"]["branch"] or "main"
        # Try the exact remote ref
        r = subprocess.run(
            ["git", "-C", str(COMPANY_ROOT), "log", f"origin/{branch}..HEAD", "--oneline"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0:
            out["local"]["unpushed_commits"] = len(
                [l for l in r.stdout.splitlines() if l.strip()]
            )
    except Exception:
        pass

    # ---- cron state ----
    out["cron"] = {
        "job_id": "", "name": "", "schedule": "", "next_run": "", "last_run": None,
        "last_outcome": "unknown", "last_message": "", "last_error": "",
        "last_duration_ms": 0, "last_files_changed": 0, "last_commit_sha": "",
    }
    try:
        r = subprocess.run(
            ["hermes", "cron", "list"],
            capture_output=True, text=True, timeout=5,
        )
        text = r.stdout
        # The cron list output is a pretty-printed block per job. Find the
        # block that mentions github-push-nofitech and extract its fields.
        # Block delimiters: hex job_id line `  <hex> [active]` followed by
        # indented `Name: ...`, `Schedule: ...`, `Next run: ...`.
        lines = text.splitlines()
        for i, line in enumerate(lines):
            if "github-push-nofitech" in line.lower():
                # Walk backwards to find the job_id (8+ hex chars at line start)
                for j in range(i, max(-1, i - 5), -1):
                    m = re.search(r'^\s*([a-f0-9]{8,})\s*\[', lines[j])
                    if m:
                        out["cron"]["job_id"] = m.group(1)
                        break
                # Walk forward within the same block to extract fields.
                # The block ends at the next job_id or at a blank line followed
                # by another job_id. Cap at +10 lines.
                ctx = "\n".join(lines[i:i + 10])
                m = re.search(r'Name:\s*(\S+)', ctx)
                if m:
                    out["cron"]["name"] = m.group(1)
                m = re.search(r'Schedule:\s*(\S+)', ctx)
                if m:
                    out["cron"]["schedule"] = m.group(1)
                m = re.search(r'Next run:\s*(\S+)', ctx)
                if m:
                    out["cron"]["next_run"] = m.group(1)
                break
    except Exception as e:
        out["errors"].append(f"hermes cron: {e}")

    # ---- last run status from file ----
    status_file = (Path.home() / ".hermes" / "cron-output"
                   / "github-push-nofitech" / "last_run.json")
    if status_file.exists():
        try:
            data = json.loads(status_file.read_text())
            out["cron"]["last_run"] = data.get("ts")
            out["cron"]["last_outcome"] = data.get("outcome", "unknown")
            out["cron"]["last_message"] = data.get("message", "")
            out["cron"]["last_error"] = data.get("error", "")
            out["cron"]["last_duration_ms"] = data.get("duration_ms", 0)
            out["cron"]["last_files_changed"] = data.get("files_changed", 0)
            out["cron"]["last_commit_sha"] = data.get("commit_sha", "")
        except Exception as e:
            out["errors"].append(f"last_run.json read: {e}")
    else:
        out["cron"]["last_outcome"] = "never_ran"

    # ---- overall status ----
    if out["cron"]["last_outcome"] == "failed":
        out["status"] = "failed"
    elif out["local"]["unpushed_commits"] and out["local"]["unpushed_commits"] > 0:
        out["status"] = "behind"
    elif out["cron"]["last_outcome"] in ("success", "no_changes"):
        out["status"] = "ok"
    else:
        out["status"] = "unknown"

    return out


# ---------- events.jsonl (Stage 14) ----------

def _read_events_tail(limit: int = 50):
    """Read the last `limit` lines of events.jsonl as parsed dicts.
    Returns ([], 'No events yet.') if the file is missing or empty.
    Tolerates malformed lines (skips them)."""
    p = COMPANY_ROOT / "00_company_os" / "events.jsonl"
    if not p.is_file() or p.stat().st_size == 0:
        return [], "No events yet."
    out = []
    try:
        with p.open("r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return out, None
    if not out:
        return [], "No events yet."
    # Keep last `limit`, most recent first
    return out[-limit:][::-1], None


def data_events(limit: int = 50):
    """Public wrapper for /api/data/events."""
    events, reason = _read_events_tail(limit=limit)
    return {
        "events": events,
        "count": len(events),
        "limit": limit,
        "reason": reason,
    }


# ---------- Stage 17→19: append a structured fix_order event to events.jsonl ----------

def _build_recommended_fix(warning_text: str, warning_source: str) -> str:
    """Heuristic that maps a warning context to a recommended fix string.

    Stage 19: simple keyword-based triage. This is a SUGGESTION only — Thor
    decides what to do in chat, gated by 'Thor, do it' or
    'Thor, execute pending order <order_id>'. No auto-execution ever.
    """
    wt = (warning_text or "").lower()
    src = (warning_source or "").lower()
    if "warning" in wt and "test-" in src:
        return f"delete the test fixture file at {warning_source or 'unknown'}"
    if ("no key" in wt) or ("missing" in wt) or ("not configured" in wt):
        return f"configure the missing dependency referenced in {warning_source or 'unknown'}"
    return f"investigate and resolve the issue: {warning_text}"


def _append_fix_order_event(payload: dict) -> dict:
    """Append one nofitech-event/v1 fix_order line to events.jsonl.

    Stage 19: event_type is now "fix_order" (an allowed value in
    00_company_os/event-schema.md). The event carries structured order
    fields (order_id, recommended_fix, requires_chat_confirmation,
    requested_by, etc.) so /api/data/orders can list them and the
    Pending Orders panel can render them.

    The button only WRITES an order; it does NOT execute anything. Per
    NOFI directive 2026-06-11, Thor acts only on chat confirmation.

    Returns a dict with ok / event_id / ts / order_id / status /
    requires_chat_confirmation / recommended_fix. The old (Stage 17)
    `ok` and `event_id` keys are preserved for backward compatibility.
    """
    warning_text = (payload.get("warning_text") or "").strip()
    if not warning_text:
        raise ValueError("warning_text is required")
    warning_id   = (payload.get("warning_id")   or "").strip()
    warning_src  = (payload.get("warning_source") or "").strip()
    warning_lvl  = (payload.get("warning_level")  or "warn").strip().lower()
    if warning_lvl not in ("warn", "error", "info"):
        warning_lvl = "warn"
    ts = datetime.now(timezone.utc).isoformat()
    order_id = f"order-{uuid.uuid4().hex[:8]}"
    short = uuid.uuid4().hex[:8]
    event_id = f"fix-order-{int(time.time())}-{short}"

    recommended_fix = _build_recommended_fix(warning_text, warning_src)
    title_text = warning_text[:80]
    source_file = warning_src or "00_company_os/events.jsonl"

    line = {
        "ts":            ts,
        "actor":         "nofi",
        "event_type":    "fix_order",
        "project":       "mission-control",
        "task_id":       "",
        "title":         f"FIX ORDER: {title_text}",
        "message": (
            f"{recommended_fix}. "
            f"(warning_id={warning_id}, level={warning_lvl}). "
            f"Awaiting chat confirmation: 'Thor, do it' or "
            f"'Thor, execute pending order {order_id}'. "
            f"NO auto-execution per NOFI directive 2026-06-11."
        ),
        "status":      "pending",
        "source_file": source_file,
        "schema":      "nofitech-event/v1",
        "order_id":    order_id,
        "recommended_fix": recommended_fix,
        "requires_chat_confirmation": True,
        "requested_by": "nofi",
        "chat_confirmation_phrase": "Thor, do it",
        "chat_confirmation_phrase_with_id": f"Thor, execute pending order {order_id}",
        "execution_locked_reason": "NOFI directive 2026-06-11: no auto-fix from dashboard buttons",
    }
    p = COMPANY_ROOT / "00_company_os" / "events.jsonl"
    # Append in a single open() so concurrent writers can't interleave a
    # half-line. No secrets are echoed; warning_text is a user-visible
    # warning message, not a key.
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, ensure_ascii=False) + "\n")
    return {
        "ok": True,
        "event_id": event_id,
        "ts": ts,
        "order_id": order_id,
        "status": "pending",
        "requires_chat_confirmation": True,
        "recommended_fix": recommended_fix,
    }


# ---------- Stage 19: list pending/in_progress fix_order events ----------

def data_orders() -> dict:
    """Read events.jsonl and return all fix_order events with
    status in (pending, in_progress). Newest first.

    Stage 20: also exclude any order_id that has ANY event
    whose status is in (cancelled, resolved) — so cancellation
    append-events (added by Forge/Thor) supersede the original
    pending entry without modifying the original on disk.
    Implemented as a two-pass scan: pass 1 collects superseded
    order_ids; pass 2 emits the visible (pending/in_progress)
    orders, skipping any whose order_id was superseded.

    Source: 00_company_os/events.jsonl (single source of truth).
    Open endpoint, no auth, no secrets logged. Tolerant of corrupt
    lines (skipped, never raises on bad JSON).
    """
    p = COMPANY_ROOT / "00_company_os" / "events.jsonl"
    orders = []
    superseded_ids = set()  # order_ids that have a cancelled/resolved event
    parsed_events = []      # all parsed fix_order events, for the second pass
    if p.exists():
        try:
            with p.open("r", encoding="utf-8") as f:
                for line in f:
                    s = line.strip()
                    if not s:
                        continue
                    try:
                        ev = json.loads(s)
                    except json.JSONDecodeError:
                        continue
                    if not isinstance(ev, dict):
                        continue
                    if ev.get("event_type") != "fix_order":
                        continue
                    parsed_events.append(ev)
                    ev_status = (ev.get("status") or "").strip().lower()
                    ev_oid = ev.get("order_id")
                    # Pass 1: any fix_order with status in
                    # (cancelled, resolved) marks its order_id as superseded.
                    if ev_oid and ev_status in ("cancelled", "resolved"):
                        superseded_ids.add(ev_oid)
        except OSError:
            pass
    # Pass 2: emit pending/in_progress orders, skipping superseded ones.
    for ev in parsed_events:
        ev_status = (ev.get("status") or "").strip().lower()
        ev_oid = ev.get("order_id")
        if ev_status not in ("pending", "in_progress"):
            continue
        if ev_oid and ev_oid in superseded_ids:
            continue
        ev["rel"] = rel_time(ev.get("ts") or "")
        ev["source"] = ev.get("source_file") or ""
        orders.append(ev)
    # Newest first; fall back to ts lexicographic (ISO sorts correctly).
    orders.sort(key=lambda r: r.get("ts") or "", reverse=True)
    return {
        "orders": orders,
        "count": len(orders),
        "reason": None if orders else "no pending orders",
    }


# ---------- Stage 19: mark_order_status() — NO-OP stub ----------
# Intentionally NOT exposed via any HTTP endpoint in Stage 19.
# This stub exists so future code (Stage 20+) can mark orders as
# in_progress / resolved / cancelled without rewiring the call site.
# The button does NOT call it. Per NOFI directive 2026-06-11, the
# only way an order changes status is via chat confirmation.
def mark_order_status(order_id: str, new_status: str, actor: str = "thor") -> dict:
    """Stage 19 stub. Returns a sentinel; does NOT mutate events.jsonl."""
    return {
        "ok": False,
        "noop": True,
        "reason": "mark_order_status is a Stage 19 no-op stub; status changes require chat confirmation",
        "order_id": order_id,
        "new_status": new_status,
        "actor": actor,
    }


def data_projects():
    """All projects in 01_projects/."""
    rows = []
    for proj_dir in sorted((COMPANY_ROOT / "01_projects").iterdir()):
        if not proj_dir.is_dir() or proj_dir.name.startswith("."):
            continue
        status_path = proj_dir / "status.md"
        charter_path = proj_dir / "charter.md"
        txt = safe_read(status_path) if status_path.exists() else None
        if txt:
            meta, body = parse_frontmatter(txt)
        else:
            meta, body = {}, ""
        rows.append({
            "name": proj_dir.name,
            "phase": meta.get("phase") or "—",
            "status": meta.get("status") or "—",
            "progress_pct": meta.get("progress_pct") or "—",
            "next_action": meta.get("next_action") or "—",
            "approval_needed": (meta.get("approval_needed") or "false").lower() == "true",
            "blocker": meta.get("blocker") or "",
            "charter_exists": charter_path.exists(),
            "status_exists": status_path.exists(),
            "data_source": meta.get("data_source") or "—",
            "updated": meta.get("updated") or "—",
            "path": str(proj_dir.relative_to(COMPANY_ROOT)),
        })
    sources = set()
    for r in rows:
        if r.get("data_source") and r["data_source"] != "—":
            sources.add(r["data_source"])
    return {
        "projects": rows,
        "count": len(rows),
        "data_sources": sorted(sources) if sources else [],
        "reason": None if rows else "no projects yet",
    }


def _check_port_open(host, port, timeout=0.3):
    """Quick non-blocking check whether a TCP port is open on host.
    Returns True/False. Does not send any data."""
    import socket
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except Exception:
        return False


def _dns_resolves(host, timeout=0.5):
    """Quick check whether a hostname resolves via /etc/hosts or DNS.
    Does not make an HTTP request."""
    import socket
    try:
        socket.getaddrinfo(host, None, socket.AF_INET)
        return True
    except Exception:
        return False


def data_provider():
    """2 rows: free (Hermes proxy) + paid (Minimax).
    Connection status is determined by CHEAP, HONEST signals:
      - Free: is port 8768 bound on localhost?
      - Paid: is .env present + key set + DNS resolves for api.minimax.io?
    NO live LLM calls. NO fake 'Connected' state.
    Never echoes the API key."""
    env_path = COMPANY_ROOT / ".config" / "nofitech" / ".env"
    env_exists = env_path.exists()

    key_set = False
    free_model = "nvidia/nemotron-3-ultra:free"
    paid_model = "minimax/minimax-m3"
    if env_exists:
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k = k.strip()
            v = v.strip()
            if k == "NOFITECH_LLM_API_KEY" and v:
                key_set = True
            elif k == "NOFITECH_LLM_MODEL_FREE":
                free_model = v
            elif k == "NOFITECH_LLM_MODEL_PAID":
                paid_model = v

    # Last successful/failed check from agent logs (existing logic, kept)
    logs_root = COMPANY_ROOT / "00_company_os" / "04_agents" / "logs"
    last_ok = None
    last_fail = None
    if logs_root.is_dir():
        for f in sorted(logs_root.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True):
            txt = safe_read(f)
            if not txt:
                continue
            if last_ok is None and "model:" in txt and "error" not in txt.lower()[:200]:
                m = re.search(r"model:\s*(\S+)", txt)
                if m:
                    last_ok = {
                        "model": m.group(1),
                        "at": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                    }
            if last_fail is None and re.search(r"\b(LLM call failed|primary failed|error)\b", txt, re.IGNORECASE):
                last_fail = {
                    "at": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                    "source": str(f.relative_to(COMPANY_ROOT)),
                }
            if last_ok and last_fail:
                break

    # FREE slot: Hermes proxy on 127.0.0.1:8768
    free_port_open = _check_port_open("127.0.0.1", 8768)
    if free_port_open:
        free_conn = "Unknown"  # port open but we haven't called it
        free_conn_detail = "port 8768 open; live call not performed"
    else:
        free_conn = "Not connected"
        free_conn_detail = "port 8768 not bound (Hermes proxy not running)"

    # PAID slot: Minimax direct endpoint
    paid_dns = _dns_resolves("api.minimax.io")
    if not env_exists:
        paid_conn = "Not configured"
        paid_conn_detail = ".env missing at .config/nofitech/.env"
    elif not key_set:
        paid_conn = "Not configured"
        paid_conn_detail = "NOFITECH_LLM_API_KEY not set in .env"
    elif not paid_dns:
        paid_conn = "Unreachable"
        paid_conn_detail = "DNS resolution for api.minimax.io failed"
    else:
        paid_conn = "Unknown"  # key + DNS ok, but no live call
        paid_conn_detail = "key set + DNS resolves; live call not performed"

    rows = [
        {
            "slot": "free",
            "provider": "Nous (Hermes proxy)",
            "model": free_model,
            "endpoint": "http://127.0.0.1:8768/v1/chat/completions",
            "key_configured": free_port_open,  # HONEST: only true if port is open
            "connection_status": free_conn,
            "connection_detail": free_conn_detail,
            "last_ok": last_ok,
            "last_fail": last_fail,
        },
        {
            "slot": "paid",
            "provider": "Minimax (Anthropic-compat)",
            "model": paid_model,
            "endpoint": "https://api.minimax.io/anthropic/v1/messages",
            "key_configured": key_set,
            "connection_status": paid_conn,
            "connection_detail": paid_conn_detail,
            "last_ok": None,
            "last_fail": None,
        },
    ]
    return {"providers": rows, "count": len(rows)}


# ---- env status (no secret values exposed) ----
# Mapping from internal env-var name → safe public display name.
# The env-var name is NOT exposed in the API response. Only the safe label.
_ENV_DISPLAY = {
    "NOFITECH_LLM_API_KEY":     "LLM API key",
    "NOFITECH_LLM_MODEL_FREE":  "LLM model (free)",
    "NOFITECH_LLM_MODEL_PAID":  "LLM model (paid)",
}


def _env_status():
    """Return env var status without ever exposing the value OR the raw var name.
    Status is one of: 'configured' | 'missing' | 'unknown'.
    Keys returned are safe display labels; the underlying env-var name never appears
    in HTTP responses (avoids trivial grep hits on common secret-var names).
    """
    env_path = COMPANY_ROOT / ".config" / "nofitech" / ".env"
    out = {}
    for var, label in _ENV_DISPLAY.items():
        v = None
        if env_path.exists():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                kk, _, vv = line.partition("=")
                if kk.strip() == var:
                    v = vv.strip()
                    break
        out[label] = "configured" if v else "missing"   # NEVER the value, NEVER the var name
    # Also: is the env file itself present at all? (boolean only)
    out["__env_file_present__"] = env_path.exists()
    return out


def data_logs():
    """Last 20 log events + health + env summary.
    Stage 9: real level detection, last_verification, env status (no values),
    app/api health booleans + reasons.
    Stage 18: single source of truth for warnings/errors. The warnings count
    and the warnings panel both read from `warnings_list` / `errors_list`
    (unbounded, every warn/error entry). The `events` array now contains
    ALL warn + ALL error + the 20 most recent info entries (sorted by ts desc)
    so the recent-activity view still surfaces them too.
    """
    warnings_list = []   # ALL warn-level entries, no cap
    errors_list = []     # ALL error-level entries, no cap
    info_list = []       # ALL info-level entries, capped to 20 most recent below
    roots = [COMPANY_ROOT / "00_company_os" / "04_agents" / "logs"]
    for proj in (COMPANY_ROOT / "01_projects").glob("*/logs"):
        roots.append(proj)

    last_verification = None  # newest argus-*.md mtime
    last_verification_source = None
    for r in roots:
        if not r.is_dir():
            continue
        for f in r.rglob("*.md"):
            txt = safe_read(f)
            if not txt:
                continue
            meta, body = parse_frontmatter(txt)

            # Strict level detection (Stage 12) — ONLY explicit `level:` in frontmatter.
            # No body-inference, no filename-inference. If a log has no `level:` field,
            # it is treated as `info`. This is the rule visible to the user.
            level = (meta.get("level") or "").strip().lower()
            if level not in ("error", "warn", "info"):
                level = "info"  # default to info, not error

            entry = {
                "ts": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                "rel": rel_time(f.stat().st_mtime),
                "source": str(f.relative_to(COMPANY_ROOT)),
                "officer": (meta.get("officer") or meta.get("agent") or (f.stem.split("-")[0] if "-" in f.stem else None)),
                "level": level,
                "title": meta.get("title") or f.stem,
            }

            if level == "error":
                errors_list.append(entry)
            elif level == "warn":
                warnings_list.append(entry)
            else:
                info_list.append(entry)

            # Track last verification (argus-*.md)
            if f.stem.startswith("argus-") and (last_verification is None or f.stat().st_mtime > last_verification):
                last_verification = f.stat().st_mtime
                last_verification_source = str(f.relative_to(COMPANY_ROOT))

    # Sort all three lists by ts desc
    warnings_list.sort(key=lambda e: e["ts"], reverse=True)
    errors_list.sort(key=lambda e: e["ts"], reverse=True)
    info_list.sort(key=lambda e: e["ts"], reverse=True)

    # Counts derived from the unbounded lists
    errors = len(errors_list)
    warnings = len(warnings_list)

    # Final events array: ALL warnings + ALL errors + 20 most recent infos,
    # sorted by ts desc. This guarantees the warn/error entries never get
    # pushed out of view by a flood of newer info entries.
    events = warnings_list + errors_list + info_list[:20]
    events.sort(key=lambda e: e["ts"], reverse=True)

    # Stage 14: merge events.jsonl into the Logs/Health panel. The last 20
    # entries from 00_company_os/events.jsonl surface alongside the log-file
    # events so the user sees the full activity stream in one place.
    jsonl_events, jsonl_reason = _read_events_tail(limit=20)
    # jsonl_events is already most-recent-first; UI sorts by ts desc which
    # is the same direction, so we just pass it through.

    # App health: derived from errors count
    if errors > 0:
        app_health = "degraded"
        app_health_reason = f"{errors} error event(s) in log"
    elif warnings > 0:
        app_health = "degraded"
        app_health_reason = f"{warnings} warning(s) in log"
    else:
        app_health = "ok"
        app_health_reason = None

    # API health: simple — server is responding means API health is ok
    api_health = "ok"  # we are responding, so the server itself is healthy
    api_health_reason = None

    return {
        "events": events,
        "count": len(events),
        "errors": errors,
        "warnings": warnings,
        "info_count": sum(1 for e in events if e["level"] == "info"),
        # Stage 18: unbounded, every warn/error entry — single source of truth
        # for the Warnings panel and the warnings count.
        "warnings_list": warnings_list,
        "errors_list": errors_list,
        "app_health": app_health,
        "app_health_reason": app_health_reason,
        "api_health": api_health,
        "api_health_reason": api_health_reason,
        "last_verification": datetime.fromtimestamp(last_verification, tz=timezone.utc).isoformat() if last_verification else None,
        "last_verification_rel": rel_time(last_verification) if last_verification else "—",
        "last_verification_source": last_verification_source,
        "env": _env_status(),
        # Stage 14: events.jsonl surface area
        "jsonl_events": jsonl_events,
        "jsonl_count": len(jsonl_events),
        "jsonl_reason": jsonl_reason,
    }


# ---------- MC-KANBAN-1: Kanban tab endpoints (added 2026-06-16) ----------

def data_kanban(include_archived: bool = False) -> dict:
    """GET /api/data/kanban — full board grouped by 6 columns, with 3-agent
    swimlanes inside Running. Reads project task files via kanban_parser.
    No external kanban.db; no pip deps. Additive to the existing endpoints."""
    board = kanban_parser.build_board(COMPANY_ROOT, include_archived=include_archived)
    board["last_updated"] = datetime.now(timezone.utc).isoformat()
    board["errors"] = []
    return board


def get_kanban_task_result(task_id: str) -> tuple[int, dict]:
    """MC-KANBAN-5 (2026-06-17): GET /api/data/kanban/task/:id/result — return
    the full "## Result" section body for the kanban modal popup, plus the
    parsed metadata (date/by/status). Returns 404 if the task or its Result
    section is not found. The body is the raw markdown text AFTER the header
    block (`**Date:**/By/Status` lines) and AFTER the `---` separator, so the
    frontend can render it as markdown directly.
    """
    task_id = (task_id or "").strip()
    if not task_id:
        return 400, {"error": "task_id is required"}

    # Locate the task file using the same logic as the parser
    found_path = None
    for proj_dir in (COMPANY_ROOT / "01_projects").iterdir():
        if not proj_dir.is_dir():
            continue
        candidate = proj_dir / "tasks" / f"{task_id}.md"
        if candidate.is_file():
            found_path = candidate
            break
    if not found_path:
        # also try 00_company_os
        co = COMPANY_ROOT / "00_company_os"
        if co.is_dir():
            for sub in co.iterdir():
                candidate = sub / "tasks" / f"{task_id}.md"
                if candidate.is_file():
                    found_path = candidate
                    break
    if not found_path:
        return 404, {"error": f"task file not found: {task_id}"}

    try:
        text = found_path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return 500, {"error": f"read failed: {e}"}

    # Extract the body and locate the ## Result section
    if not text.startswith("---\n"):
        return 404, {"error": f"task has no frontmatter: {task_id}"}
    end = text.find("\n---\n", 4)
    if end < 0:
        return 404, {"error": f"task has malformed frontmatter: {task_id}"}
    body = text[end + 5:]

    # Use the parser's extractor for metadata
    teaser, metadata = kanban_parser._extract_result_section(body)
    if teaser is None and not metadata:
        return 404, {"error": f"task has no Result section: {task_id}"}

    # Slice the result body out (between the header block and the closing ---)
    # so the modal can render the markdown verbatim.
    import re as _re
    header_re = _re.compile(r"^##\s+Result\s*$\n", _re.MULTILINE)
    m = header_re.search(body)
    if not m:
        return 404, {"error": f"task has no Result section: {task_id}"}
    rest = body[m.end():]
    next_h = _re.search(r"^##\s+", rest, _re.MULTILINE)
    section = rest if not next_h else rest[: next_h.start()]
    # Strip the **Date:**/**By:**/**Status:** header lines + the closing ---
    body_lines = []
    for line in section.splitlines():
        s = line.strip()
        if s.startswith("**Date:**") or s.startswith("**By:**") or s.startswith("**Status:**"):
            continue
        body_lines.append(line)
    # Drop trailing "---" line if present
    while body_lines and body_lines[-1].strip() == "---":
        body_lines.pop()
    # Drop leading blank lines
    while body_lines and not body_lines[0].strip():
        body_lines.pop(0)
    # Drop trailing blank lines
    while body_lines and not body_lines[-1].strip():
        body_lines.pop()
    full_body = "\n".join(body_lines).strip()

    return 200, {
        "task_id": task_id,
        "title": "",  # caller already has it from the kanban card
        "metadata": metadata or {},
        "teaser": teaser,
        "body": full_body,
    }




def patch_kanban_task(task_id: str, new_status: str) -> tuple[int, dict]:
    """PATCH /api/data/kanban/task/:id — update task's `kanban_status` on disk.

    MC-KANBAN-2: writes to `kanban_status` (a separate field), NOT to `status`.
    The project-native `status` field is preserved exactly. Detects the file
    format (YAML frontmatter vs markdown table) and routes to the correct
    mutator. For Format B (markdown table), inserts/updates a
    `| **kanban_status** | <new> |` row right after the `| **status** | ... |`
    row, leaving all other rows untouched.

    Returns (http_status, body_dict). The body is a full updated board on
    success, an error dict on failure."""
    task_id = (task_id or "").strip()
    new_status = (new_status or "").strip().lower()
    if not task_id:
        return 400, {"error": "task_id is required", "ok": False}
    if new_status not in kanban_parser.ALLOWED_STATUSES:
        return 400, {
            "error": f"unknown status: {new_status!r}",
            "allowed": list(kanban_parser.ALLOWED_STATUSES),
            "ok": False,
        }
    ok, reason, path = kanban_parser.update_task_status(task_id, new_status, COMPANY_ROOT)
    if not ok:
        # 404 only for "not found"; 400 for any other write failure
        if "not found" in reason:
            return 404, {"error": reason, "ok": False, "task_id": task_id}
        return 400, {"error": reason, "ok": False}
    board = data_kanban(include_archived=False)
    # MC-MEMORY-GRAPH-1 (2026-06-17): event bridge — emit node.upsert and a
    # derived `task->status` edge for every status change. Best-effort.
    emit_kanban_memory_event(
        task_id, new_status,
        extra_edge={"source": f"task-{task_id}", "target": f"status-{new_status}",
                    "kind": "kanban_status", "weight": 0.6},
    )
    return 200, {
        "ok": True,
        "task_id": task_id,
        "new_status": new_status,
        "path": str(path.relative_to(COMPANY_ROOT)) if path else None,
        "reason": reason,
        "board": board,
    }


def assign_kanban_task(task_id: str, payload: dict) -> tuple[int, dict]:
    """PATCH /api/data/kanban/task/:id/assign — update task's `assigned_to`
    (Format A YAML) or `owner` row (Format B markdown table) on disk.

    MC-KANBAN-ASSIGN-1 (2026-06-17): supports 4 values — thor, forge, argus,
    or "" (unassign). Empty string removes the field (Format A) or the row
    (Format B). Preserves every other line in the file exactly. Returns
    (http_status, body_dict) with the full updated board on success.
    """
    import pathlib  # local; cheap
    task_id = (task_id or "").strip()
    if not task_id:
        return 400, {"error": "task_id is required", "ok": False}
    new_assignee = (payload.get("assignee") or "").strip().lower()
    if new_assignee not in {"thor", "forge", "argus", ""}:
        return 400, {
            "error": f"unknown assignee: {new_assignee!r}; must be thor, forge, argus, or empty (unassign)",
            "ok": False,
            "task_id": task_id,
        }

    # Find the task file (reuse the same matching strategy as
    # kanban_parser.update_task_status: stem, exact filename, or frontmatter
    # task_id / Format B id row).
    target: pathlib.Path | None = None
    company_root = pathlib.Path(COMPANY_ROOT)
    for root in (company_root / "01_projects", company_root / "00_company_os"):
        if not root.is_dir():
            continue
        for td in root.glob("*/tasks"):
            if not td.is_dir():
                continue
            for tf in sorted(td.glob("*.md")):
                if tf.stem == task_id or tf.name == f"{task_id}.md":
                    target = tf
                    break
                # also match by Format A frontmatter task_id or Format B id
                try:
                    txt = tf.read_text(encoding="utf-8")
                except Exception:
                    continue
                meta, _ = kanban_parser.parse_frontmatter(txt)
                if (meta.get("task_id") or "").strip() == task_id:
                    target = tf
                    break
                table, _ = kanban_parser.parse_markdown_table(txt)
                if (table.get("id") or "").strip() == task_id:
                    target = tf
                    break
            if target is not None:
                break
        if target is not None:
            break
    if target is None:
        return 404, {"error": f"task_id not found: {task_id!r}", "ok": False, "task_id": task_id}

    # Re-detect format
    txt = target.read_text(encoding="utf-8")
    fmt = kanban_parser.detect_format(txt)

    # ---- Apply the assign update ----
    if fmt == "A":
        # Format A: YAML frontmatter. Update or insert `assigned_to: <value>`
        # right after `task_id:`. If empty, REMOVE the `assigned_to:` line.
        lines = txt.splitlines()
        # find frontmatter bounds
        if not lines or lines[0].strip() != "---":
            return 400, {"error": "Format A file is missing leading `---`", "ok": False, "task_id": task_id}
        end_idx = None
        for i in range(1, len(lines)):
            if lines[i].strip() == "---":
                end_idx = i
                break
        if end_idx is None:
            return 400, {"error": "Format A file is missing closing `---`", "ok": False, "task_id": task_id}
        header = lines[1:end_idx]
        body = lines[end_idx + 1:]

        assigned_to_re = re.compile(r"^(\s*assigned_to\s*:\s*)(.*?)(\s*(?:#.*)?)$")
        task_id_re = re.compile(r"^(\s*task_id\s*:\s*)(.*?)(\s*(?:#.*)?)$")

        if new_assignee:
            new_header = []
            replaced = False
            for line in header:
                m = assigned_to_re.match(line)
                if m:
                    new_header.append(f"{m.group(1)}{new_assignee}{m.group(3)}")
                    replaced = True
                else:
                    new_header.append(line)
            if not replaced:
                # insert after task_id: (or at end of header if not found)
                new_header2 = []
                inserted = False
                for line in new_header:
                    new_header2.append(line)
                    if (not inserted) and task_id_re.match(line):
                        new_header2.append(f"assigned_to: {new_assignee}")
                        inserted = True
                if not inserted:
                    new_header2.append(f"assigned_to: {new_assignee}")
                new_header = new_header2
        else:
            # Unassign: remove the `assigned_to:` line entirely (preserve blank lines around it)
            new_header = [ln for ln in header if not assigned_to_re.match(ln)]

        out = "---\n" + "\n".join(new_header) + "\n---\n" + "\n".join(body)
        if not out.endswith("\n"):
            out += "\n"
        target.write_text(out, encoding="utf-8")

    elif fmt == "B":
        # Format B: markdown `| **field** | value |` table. Update or insert
        # the `| **owner** | <value> |` row. If empty, REMOVE the row entirely.
        lines = txt.splitlines()
        header_idx = None
        for i, line in enumerate(lines):
            if kanban_parser._TABLE_HEADER_RE.match(line):
                header_idx = i
                break
        if header_idx is None:
            return 400, {"error": "Format B table header not found", "ok": False, "task_id": task_id}
        data_start = header_idx + 1
        if data_start < len(lines) and kanban_parser._TABLE_SEP_RE.match(lines[data_start]):
            data_start += 1

        row_kv_re = kanban_parser._TABLE_ROW_KV_RE
        owner_row_idx = None
        id_row_idx = None
        for j in range(data_start, len(lines)):
            ln = lines[j]
            if not ln.lstrip().startswith("|"):
                break
            m = row_kv_re.match(ln)
            if not m:
                break
            raw_key = m.group("key").strip()
            if raw_key.startswith("**") and raw_key.endswith("**") and len(raw_key) >= 4:
                key = raw_key[2:-2].strip().lower()
            else:
                key = raw_key.strip().lower()
            if key == "owner":
                owner_row_idx = j
            elif key == "id":
                id_row_idx = j

        if new_assignee:
            if owner_row_idx is not None:
                # update existing row, preserve exact key rendering
                ln = lines[owner_row_idx]
                m = row_kv_re.match(ln)
                raw_key = m.group("key").strip()
                lines[owner_row_idx] = f"| {raw_key} | {new_assignee} |"
            else:
                # insert new owner row after the id row (or as first data row)
                insert_at = (id_row_idx + 1) if id_row_idx is not None else data_start
                lines.insert(insert_at, f"| **owner** | {new_assignee} |")
        else:
            # Unassign: remove the owner row entirely
            if owner_row_idx is not None:
                lines.pop(owner_row_idx)

        out = "\n".join(lines)
        if not out.endswith("\n"):
            out += "\n"
        target.write_text(out, encoding="utf-8")

    else:
        return 400, {
            "error": f"task file is not in a recognized format (A or B): {target.name}",
            "ok": False,
            "task_id": task_id,
        }

    board = data_kanban(include_archived=False)
    return 200, {
        "ok": True,
        "task_id": task_id,
        "assignee": new_assignee,
        "path": str(target.relative_to(COMPANY_ROOT)),
        "board": board,
    }


def create_kanban_task(payload: dict) -> tuple[int, dict]:
    """POST /api/data/kanban/task — create a new task file from the Kanban UI.

    Body: { title, assignee, priority }
    Writes to 01_projects/mission-control/tasks/<TASK_ID>.md (existing convention
    — keeps everything in one project tree). Returns 201 on success."""
    title = (payload.get("title") or "").strip()
    assignee = (payload.get("assignee") or "").strip().lower()
    priority = (payload.get("priority") or "normal").strip().lower()
    if not title:
        return 400, {"error": "title is required", "ok": False}
    if assignee not in kanban_parser.AGENT_IDS:
        return 400, {
            "error": f"unknown assignee: {assignee!r}",
            "allowed": kanban_parser.AGENT_IDS,
            "ok": False,
        }
    # TASK_ID format per spec: "MC-KANBAN-CREATE-<timestamp>" or "MC-<random>"
    import secrets
    ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    rand = secrets.token_hex(3).upper()
    task_id = f"MC-KANBAN-CREATE-{ts}-{rand}"
    ok, reason, path = kanban_parser.create_task_file(
        task_id, title, assignee, priority, COMPANY_ROOT
    )
    if not ok:
        return 400, {"error": reason, "ok": False, "task_id": task_id}
    board = data_kanban(include_archived=False)
    # Return the new card so the UI can optimistically insert it
    new_card = None
    for col in board.get("columns", []):
        for t in col.get("tasks", []):
            if t.get("task_id") == task_id:
                new_card = t
                break
        if new_card:
            break
    # MC-MEMORY-GRAPH-1 (2026-06-17): event bridge — emit node.upsert + a
    # `task -> assignee` edge when a new task is created.
    try:
        assignee = (new_card or {}).get("assignee") or (new_card or {}).get("assigned_to") or "unassigned"
        emit_kanban_memory_event(
            task_id, "triage",
            extra_node={"importance": 0.6, "status": "triage"},
            extra_edge={"source": f"task-{task_id}", "target": f"agent-{assignee}",
                        "kind": "assigned_to", "weight": 0.7},
        )
    except Exception:
        pass
    return 201, {
        "ok": True,
        "task_id": task_id,
        "path": str(path.relative_to(COMPANY_ROOT)) if path else None,
        "card": new_card,
        "board": board,
    }


# ---------- MC-MEMORY-GRAPH-1 (2026-06-17): Memory Graph page integration ----------
# Locked stack: Python stdlib only (no pip deps), JSON on disk (no SQLite for v1),
# 5s polling on the frontend (no SSE/WebSocket). This block adds the
# redactor, snapshot persistence, event-log append, and the ingest helper
# that turns an event dict into a mutated graph + log line. Routes are
# wired in the Handler class below (do_GET, do_POST, do_DELETE).

# --- Redactor (Phase C) ---
# Recursively walks dicts / lists / strings. Strips known secret patterns and
# truncates long strings. Does NOT mutate the input; returns a new structure.
_SECRET_PATTERNS = [
    # OpenAI / Anthropic style
    re.compile(r"sk-[A-Za-z0-9_\-]{16,}"),
    re.compile(r"sk-ant-[A-Za-z0-9_\-]{16,}"),
    # GitHub
    re.compile(r"ghp_[A-Za-z0-9]{16,}"),
    re.compile(r"gho_[A-Za-z0-9]{16,}"),
    re.compile(r"ghu_[A-Za-z0-9]{16,}"),
    re.compile(r"ghs_[A-Za-z0-9]{16,}"),
    re.compile(r"ghr_[A-Za-z0-9]{16,}"),
    # Slack
    re.compile(r"xox[bp]-[A-Za-z0-9\-]{10,}"),
    # AWS
    re.compile(r"AKIA[0-9A-Z]{12,}"),
    # Generic "password=..." and "Bearer ..." and "Authorization: ..."
    re.compile(r"(?i)(password\s*=\s*)([^\s,'\"}\]\)]{3,})"),
    re.compile(r"(?i)(api[_-]?key\s*[=:]\s*)([A-Za-z0-9_\-]{8,})"),
    re.compile(r"(?i)(token\s*[=:]\s*)([A-Za-z0-9_\-\.]{8,})"),
    re.compile(r"(?i)(Bearer\s+)([A-Za-z0-9_\-\.=]{8,})"),
    re.compile(r"(?i)(Authorization\s*:\s*)([^\n\r]{6,})"),
    # JWT
    re.compile(r"eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}"),
]
_REDACTED = "[REDACTED]"


def _redact_string(s: str) -> str:
    if not isinstance(s, str):
        return s
    out = s
    for pat in _SECRET_PATTERNS:
        out = pat.sub(_REDACTED, out)
    if len(out) > 500:
        out = out[:500] + "...[truncated]"
    return out


def redact_secrets(obj):
    """Recursively walk obj and redact secret-shaped strings. Returns a new
    structure; the input is not mutated. Tolerates non-JSON-native values
    (datetime, etc.) by stringifying first."""
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return _redact_string(obj)
    if isinstance(obj, dict):
        return {k: redact_secrets(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [redact_secrets(v) for v in obj]
    # Fallback: stringify, redact, keep as string.
    try:
        return _redact_string(str(obj))
    except Exception:
        return obj


# --- Snapshot persistence (Phase A) ---
def _mg_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _mg_ensure_data_dir() -> None:
    MG_DATA_DIR.mkdir(parents=True, exist_ok=True)


def _mg_atomic_write(path: Path, data: str) -> None:
    """Write to <path>.tmp then rename. Survives partial writes / crashes."""
    _mg_ensure_data_dir()
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def _mg_empty_graph() -> dict:
    return {
        "metadata": {
            "name": "Mission Control Memory Graph",
            "schema_version": "1.0.0",
            "created": _mg_now_iso(),
            "source": "fresh",
        },
        "nodes": [],
        "edges": [],
        "last_updated": _mg_now_iso(),
    }


def _mg_load_graph() -> dict:
    """Load the graph from disk. On first run, seed from sample-graph.json.
    Returns the in-memory graph (always nodes=list, edges=list)."""
    if not MG_GRAPH_PATH.is_file():
        seed = _mg_empty_graph()
        # Seed from sample if present.
        if MG_SAMPLE_PATH.is_file():
            try:
                sample = json.loads(MG_SAMPLE_PATH.read_text(encoding="utf-8"))
                if isinstance(sample, dict):
                    if isinstance(sample.get("nodes"), list):
                        seed["nodes"] = list(sample["nodes"])
                    if isinstance(sample.get("edges"), list):
                        seed["edges"] = list(sample["edges"])
                    if isinstance(sample.get("metadata"), dict):
                        seed["metadata"] = {**seed["metadata"], **sample["metadata"]}
                        seed["metadata"]["source"] = "sample-seed"
            except Exception:
                pass  # bad sample → start empty
        return seed
    try:
        g = json.loads(MG_GRAPH_PATH.read_text(encoding="utf-8"))
        if not isinstance(g, dict):
            return _mg_empty_graph()
        g.setdefault("metadata", {})
        g.setdefault("nodes", [])
        g.setdefault("edges", [])
        g.setdefault("last_updated", _mg_now_iso())
        # Normalize: nodes can be a list OR a dict. We accept both; the API
        # always returns a list for the frontend.
        if isinstance(g["nodes"], dict):
            g["nodes"] = [v for v in g["nodes"].values() if isinstance(v, dict)]
        if not isinstance(g["nodes"], list):
            g["nodes"] = []
        if not isinstance(g["edges"], list):
            g["edges"] = []
        return g
    except Exception:
        return _mg_empty_graph()


def _mg_save_graph(graph: dict) -> None:
    graph["last_updated"] = _mg_now_iso()
    _mg_atomic_write(MG_GRAPH_PATH, json.dumps(graph, ensure_ascii=False, indent=2))


def _mg_append_event(event: dict) -> None:
    """Append one event to the JSONL log. Trim to MG_EVENT_LOG_MAX_LINES."""
    _mg_ensure_data_dir()
    line = json.dumps(event, ensure_ascii=False)
    # Read existing lines (cap read size for safety — 1MB is fine here).
    lines: list[str] = []
    if MG_EVENTS_PATH.is_file():
        try:
            txt = MG_EVENTS_PATH.read_text(encoding="utf-8", errors="replace")
            lines = [ln for ln in txt.splitlines() if ln.strip()]
        except Exception:
            lines = []
    lines.append(line)
    if len(lines) > MG_EVENT_LOG_MAX_LINES:
        lines = lines[-MG_EVENT_LOG_MAX_LINES:]
    _mg_atomic_write(MG_EVENTS_PATH, "\n".join(lines) + "\n")


def _mg_recent_events(n: int = 20) -> list[dict]:
    """Return the last n events from the JSONL log, oldest-first stripped of
    malformed lines. Newest at the end."""
    n = max(1, min(int(n), 200))
    if not MG_EVENTS_PATH.is_file():
        return []
    try:
        txt = MG_EVENTS_PATH.read_text(encoding="utf-8", errors="replace")
    except Exception:
        return []
    raw = [ln for ln in txt.splitlines() if ln.strip()]
    tail = raw[-n:]
    out: list[dict] = []
    for ln in tail:
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                out.append(obj)
        except Exception:
            continue
    return out


# --- Event ingestion helper (Phase B) ---
def ingest_memory_event(event: dict, *, admin: bool = False) -> dict:
    """Apply one event to the on-disk graph + event log. Returns a result
    dict {ok, type, applied, error}. Admin-gated events raise ValueError
    when admin=False.

    Event contract (from MC-MEMORY-GRAPH-1 spec section 4):
      { "type": "node.upsert",  "node":  {id, kind, label, summary, ...} }
      { "type": "edge.upsert",  "edge":  {source, target, kind, ...} }
      { "type": "memory.snapshot", "graph": {nodes, edges, metadata} }  # admin
      { "type": "node.delete",  "id":    "<node_id>" }
      { "type": "edge.delete",  "id":    "<edge_id>" }
    All payloads are passed through `redact_secrets` before being persisted.
    """
    if not isinstance(event, dict):
        raise ValueError("event must be a JSON object")
    etype = (event.get("type") or "").strip()
    if etype not in MG_VALID_EVENT_TYPES:
        raise ValueError(f"unknown event type: {etype!r}")
    if etype == "memory.snapshot" and not admin:
        raise ValueError("memory.snapshot requires admin confirmation")

    redacted = redact_secrets(event)
    graph = _mg_load_graph()
    applied = False

    if etype == "node.upsert":
        node = redacted.get("node")
        if not isinstance(node, dict):
            raise ValueError("node.upsert requires 'node' object")
        nid = (node.get("id") or "").strip()
        if not nid:
            raise ValueError("node.upsert requires non-empty 'id'")
        nkind = (node.get("kind") or "concept").strip()
        if nkind not in MG_NODE_KINDS:
            nkind = "concept"
        # Find existing by id; merge instead of duplicate.
        existing = None
        for i, n in enumerate(graph["nodes"]):
            if isinstance(n, dict) and n.get("id") == nid:
                existing = i
                break
        merged = {
            "id": nid,
            "kind": nkind,
            "label": str(node.get("label") or nid),
            "summary": str(node.get("summary") or ""),
            "importance": float(node.get("importance", 0.5) or 0.0),
            "confidence": float(node.get("confidence", 0.8) or 0.0),
            "status": str(node.get("status") or "active"),
            "tags": list(node.get("tags") or []) if isinstance(node.get("tags"), list) else [],
            "updated": _mg_now_iso(),
        }
        # Carry over assignee / extra fields if present.
        for opt_key in ("assignee", "owner", "project", "path", "url"):
            if opt_key in node:
                merged[opt_key] = node[opt_key]
        if existing is not None:
            prev = graph["nodes"][existing]
            if isinstance(prev, dict):
                prev_tags = prev.get("tags") or []
                new_tags = merged["tags"] or []
                merged["tags"] = list(dict.fromkeys(list(prev_tags) + list(new_tags)))
                merged["created"] = prev.get("created") or merged["updated"]
            else:
                merged["created"] = merged["updated"]
            graph["nodes"][existing] = merged
        else:
            merged["created"] = merged["updated"]
            graph["nodes"].append(merged)
        applied = True

    elif etype == "edge.upsert":
        edge = redacted.get("edge")
        if not isinstance(edge, dict):
            raise ValueError("edge.upsert requires 'edge' object")
        source = (edge.get("source") or "").strip()
        target = (edge.get("target") or "").strip()
        kind = (edge.get("kind") or "relates_to").strip()
        if not source or not target:
            raise ValueError("edge.upsert requires 'source' and 'target'")
        # Stable id: edge-<source>-<target>-<kind>
        eid = (edge.get("id") or "").strip() or f"edge-{source}-{target}-{kind}"
        merged_e = {
            "id": eid,
            "source": source,
            "target": target,
            "kind": kind,
            "weight": float(edge.get("weight", 0.5) or 0.0),
            "updated": _mg_now_iso(),
        }
        existing = None
        for i, e in enumerate(graph["edges"]):
            if isinstance(e, dict) and e.get("id") == eid:
                existing = i
                break
        if existing is not None:
            prev = graph["edges"][existing]
            if isinstance(prev, dict):
                merged_e["created"] = prev.get("created") or merged_e["updated"]
            else:
                merged_e["created"] = merged_e["updated"]
            graph["edges"][existing] = merged_e
        else:
            merged_e["created"] = merged_e["updated"]
            graph["edges"].append(merged_e)
        applied = True

    elif etype == "memory.snapshot":
        snap = redacted.get("graph")
        if not isinstance(snap, dict):
            raise ValueError("memory.snapshot requires 'graph' object")
        new_nodes = snap.get("nodes") or []
        new_edges = snap.get("edges") or []
        if not isinstance(new_nodes, list) or not isinstance(new_edges, list):
            raise ValueError("memory.snapshot: nodes/edges must be lists")
        new_meta = snap.get("metadata") or {}
        if not isinstance(new_meta, dict):
            new_meta = {}
        graph = {
            "metadata": {**graph.get("metadata", {}), **new_meta},
            "nodes": [n for n in new_nodes if isinstance(n, dict)],
            "edges": [e for e in new_edges if isinstance(e, dict)],
            "last_updated": _mg_now_iso(),
            "snapshot_at": _mg_now_iso(),
        }
        applied = True

    elif etype == "node.delete":
        nid = (redacted.get("id") or "").strip()
        if not nid:
            raise ValueError("node.delete requires 'id'")
        before = len(graph["nodes"])
        graph["nodes"] = [n for n in graph["nodes"] if not (isinstance(n, dict) and n.get("id") == nid)]
        # Cascade-delete any edges that touched the removed node.
        graph["edges"] = [
            e for e in graph["edges"]
            if not (isinstance(e, dict) and (e.get("source") == nid or e.get("target") == nid))
        ]
        applied = len(graph["nodes"]) < before

    elif etype == "edge.delete":
        eid = (redacted.get("id") or "").strip()
        if not eid:
            raise ValueError("edge.delete requires 'id'")
        before = len(graph["edges"])
        graph["edges"] = [e for e in graph["edges"] if not (isinstance(e, dict) and e.get("id") == eid)]
        applied = len(graph["edges"]) < before

    if applied:
        _mg_save_graph(graph)
        # Always log the redacted event (never the raw input — safety).
        _mg_append_event({
            "ts": _mg_now_iso(),
            "type": etype,
            "payload": redacted,
        })

    return {"ok": applied, "type": etype, "applied": applied}


def mg_reset() -> dict:
    """Wipe the graph + log back to the sample seed (or empty if no sample)."""
    _mg_ensure_data_dir()
    if MG_GRAPH_PATH.is_file():
        try:
            MG_GRAPH_PATH.unlink()
        except Exception:
            pass
    if MG_EVENTS_PATH.is_file():
        try:
            MG_EVENTS_PATH.unlink()
        except Exception:
            pass
    # Reload will re-seed from sample.
    g = _mg_load_graph()
    _mg_save_graph(g)
    return {
        "ok": True,
        "reset_at": _mg_now_iso(),
        "node_count": len(g.get("nodes", [])),
        "edge_count": len(g.get("edges", [])),
    }


# --- Event bridge (Phase D) ---
# Emit a single node.upsert (and optionally an edge.upsert) when a kanban
# task changes. Best-effort: if the memory graph layer is broken, the
# kanban operation must still succeed.
def emit_kanban_memory_event(task_id: str, new_status: str, *,
                             extra_node: dict | None = None,
                             extra_edge: dict | None = None) -> None:
    try:
        # Find the task to get its label / project.
        label = task_id
        project = None
        kind = "task"
        importance = 0.7
        for root in (COMPANY_ROOT / "01_projects", COMPANY_ROOT / "00_company_os"):
            if not root.is_dir():
                continue
            for td in root.glob("*/tasks"):
                if not td.is_dir():
                    continue
                for tf in sorted(td.glob("*.md")):
                    if tf.stem == task_id or tf.name == f"{task_id}.md":
                        project = td.parent.name
                        try:
                            txt = tf.read_text(encoding="utf-8")
                        except Exception:
                            continue
                        meta, _ = kanban_parser.parse_frontmatter(txt)
                        label = meta.get("title") or meta.get("label") or tf.stem
                        kind = "task"
                        break
                if project:
                    break
            if project:
                break
        node_payload = {
            "id": f"task-{task_id}",
            "kind": kind,
            "label": str(label),
            "summary": f"Kanban task {task_id} → {new_status}",
            "importance": importance,
            "confidence": 0.9,
            "status": str(new_status or "active"),
            "tags": ["kanban", "task"],
        }
        if project:
            node_payload["project"] = project
        if isinstance(extra_node, dict):
            node_payload.update(extra_node)
        try:
            ingest_memory_event({"type": "node.upsert", "node": node_payload})
        except Exception:
            pass
        if isinstance(extra_edge, dict):
            try:
                ingest_memory_event({"type": "edge.upsert", "edge": extra_edge})
            except Exception:
                pass
    except Exception:
        # Memory graph is a side effect — never let it break the kanban op.
        pass


# ---------- HTTP ----------

class Handler(http.server.BaseHTTPRequestHandler):
    def log_message(self, fmt, *args):
        # quiet
        pass

    def _json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _static(self, path):
        full = HERE / path.lstrip("/")
        if not full.is_file():
            self.send_response(404)
            self.end_headers()
            return
        if full.suffix == ".html":
            ctype = "text/html; charset=utf-8"
        else:
            ctype = "application/octet-stream"
        body = full.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        # MC-KANBAN-BUGFIX-2 (2026-06-16): prevent browser from caching the
        # static HTML/JS — NOFI was seeing stale pages that didn't include
        # the prior fix. no-store forces a fresh fetch on every page load.
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            p = urllib.parse.urlparse(self.path)
            path = p.path
            qs = urllib.parse.parse_qs(p.query)

            if path in ("/", "/mission-control.html", "/index.html"):
                return self._static("mission-control.html")

            # MC-KANBAN-MOVE-1 (2026-06-16): standalone Kanban page
            if path == "/kanban":
                return self._static("kanban.html")

            if path == "/api/health":
                v = get_version()
                return self._json({
                    "status": "ok",
                    "version": v["version"],
                    "commit": v["commit"],
                    "uptime_sec": int(time.time() - START_TIME),
                })

            if path == "/api/version":
                v = get_version()
                # Stage 16: live per-request detection, with last-known-good
                # surfaced separately for debugging. `lan_ip` remains a string
                # so the existing dashboard contract is preserved.
                _live_ip = get_lan_ip()
                return self._json({
                    **v,
                    "uptime_sec": int(time.time() - START_TIME),
                    "started_at": datetime.fromtimestamp(START_TIME, tz=timezone.utc).isoformat(),
                    "lan_ip": _live_ip,
                    "lan_ip_fallback": _last_known_lan_ip,
                    "lan_ip_auto": _LAN_IP_OK,
                    "port": PORT,
                })

            if path == "/api/data/overview":
                return self._json(data_overview())
            if path == "/api/data/agents":
                return self._json(data_agents())
            if path == "/api/data/tasks":
                # Stage 12: demo hidden by default. Use ?include=demo to opt in.
                # Backward compat: legacy ?filter=demo|real still respected.
                qs_p = urllib.parse.parse_qs(p.query)
                include_demo = "demo" in qs_p.get("include", [])
                _legacy = (qs_p.get("filter", [None])[0] or "").strip().lower()
                if _legacy == "demo":
                    include_demo = True
                elif _legacy == "real":
                    include_demo = False  # explicit real → keep demo hidden
                return self._json(data_tasks(include_demo=include_demo))
            if path == "/api/data/projects":
                return self._json(data_projects())
            if path == "/api/data/provider":
                return self._json(data_provider())
            if path == "/api/data/logs":
                return self._json(data_logs())
            if path == "/api/data/github":
                # Section 9, added 2026-06-16 (FORGE/NOFI directive)
                return self._json(data_github())
            if path == "/api/data/events":
                # Stage 14: serve the last 50 events from events.jsonl
                qs_e = urllib.parse.parse_qs(p.query)
                try:
                    limit = int((qs_e.get("limit", [50])[0] or "50"))
                except (TypeError, ValueError):
                    limit = 50
                limit = max(1, min(limit, 200))
                return self._json(data_events(limit=limit))
            if path == "/api/data/orders":
                # Stage 19: list pending/in_progress fix_order events
                return self._json(data_orders())
            if path == "/api/data/kanban":
                # MC-KANBAN-1: 6-column board + 3-agent lanes
                qs_k = urllib.parse.parse_qs(p.query)
                include_archived = "true" in (x.lower() for x in qs_k.get("include_archived", []))
                return self._json(data_kanban(include_archived=include_archived))
            if path.startswith("/api/data/kanban/task/"):
                # MC-KANBAN-5 (2026-06-17): GET /api/data/kanban/task/:id/result
                # returns the full "## Result" section body for the modal popup.
                # Other /api/data/kanban/task/:id* GETs return 405 (PATCH only).
                if path.endswith("/result"):
                    task_id = path[len("/api/data/kanban/task/"):-len("/result")]
                    status, payload = get_kanban_task_result(task_id)
                    return self._json(payload, status)
                # PATCH only — GET returns 405
                return self._json({
                    "error": "method not allowed; use PATCH",
                    "allowed": ["PATCH"],
                    "path": path,
                }, 405)

            # ---- MC-MEMORY-GRAPH-1 (2026-06-17): Memory Graph page + API ----
            if path == "/memory-graph":
                # Serve the new vanilla-JS page (same pattern as /kanban).
                return self._static("memory-graph.html")

            if path == "/api/memory-graph" or path == "/api/memory-graph/":
                g = _mg_load_graph()
                return self._json({
                    "nodes": g.get("nodes", []),
                    "edges": g.get("edges", []),
                    "metadata": g.get("metadata", {}),
                    "last_updated": g.get("last_updated"),
                    "node_count": len(g.get("nodes", [])),
                    "edge_count": len(g.get("edges", [])),
                })

            if path.startswith("/api/memory-graph/events/recent"):
                # GET /api/memory-graph/events/recent?n=20
                qs_mg = urllib.parse.parse_qs(p.query)
                try:
                    n = int((qs_mg.get("n", [20])[0] or "20"))
                except (TypeError, ValueError):
                    n = 20
                n = max(1, min(n, 200))
                return self._json({"events": _mg_recent_events(n), "count": n})

            if path == "/api/memory-graph/stream":
                # Server-Sent Events low-priority enhancement. The primary UI
                # polls /api/memory-graph every 5s. We send a snapshot now
                # and a heartbeat every 15s, then close on client disconnect
                # (the http.server BaseHTTPRequestHandler's wfile raises on
                # broken pipe — we just let that propagate).
                self.send_response(200)
                self.send_header("Content-Type", "text/event-stream")
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Accel-Buffering", "no")
                self.end_headers()
                try:
                    g = _mg_load_graph()
                    payload = json.dumps({
                        "nodes": g.get("nodes", []),
                        "edges": g.get("edges", []),
                        "last_updated": g.get("last_updated"),
                    }, ensure_ascii=False)
                    self.wfile.write(b"event: snapshot\ndata: " + payload.encode("utf-8") + b"\n\n")
                    self.wfile.flush()
                    for i in range(2):  # up to 2 heartbeats (~30s)
                        time.sleep(15)
                        self.wfile.write(b": heartbeat\n\n")
                        self.wfile.flush()
                except (BrokenPipeError, ConnectionResetError):
                    pass
                return

            return self._json({"error": "not found", "path": path}, 404)

        except Exception as e:
            return self._json({"error": "server error", "detail": str(e)}, 500)

    def do_POST(self):
        """Stage 17→19: POST /api/data/order — append a structured
        fix_order event to events.jsonl (nofitech-event/v1 schema). Open
        endpoint, no auth, no secrets logged. 400 on bad JSON / missing
        warning_text, 200 on success with {ok, event_id, ts, order_id,
        status, requires_chat_confirmation, recommended_fix}. The Stage 17
        `ok` and `event_id` fields are preserved for backward compat.

        MC-KANBAN-1: POST /api/data/kanban/task — create a new task file
        from the UI. Returns 201 on success, 400 on bad input.

        MC-MEMORY-GRAPH-1 (2026-06-17): POST /api/memory-graph/events —
        ingest one event object OR an array of events. Body caps at 64 KiB.
        All payloads are redacted server-side before persistence.
        POST /api/memory-graph/reset — admin reset; requires header
        X-MC-Admin: yes OR a body of {confirm: true}.
        """
        try:
            p = urllib.parse.urlparse(self.path)

            # ---- MC-MEMORY-GRAPH-1: events ingest ----
            if p.path == "/api/memory-graph/events":
                try:
                    length = int(self.headers.get("Content-Length") or "0")
                except (TypeError, ValueError):
                    length = 0
                if length < 0 or length > 64 * 1024:
                    return self._json({"error": "missing or oversized body"}, 400)
                raw = self.rfile.read(length) if length > 0 else b""
                if not raw:
                    return self._json({"error": "empty body"}, 400)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    return self._json({"error": "invalid JSON", "detail": str(e)}, 400)
                # Accept single object or list of objects.
                events = payload if isinstance(payload, list) else [payload]
                if not events:
                    return self._json({"error": "no events in payload"}, 400)
                results = []
                for ev in events:
                    if not isinstance(ev, dict):
                        results.append({"ok": False, "error": "event must be a JSON object"})
                        continue
                    try:
                        results.append(ingest_memory_event(ev))
                    except ValueError as e:
                        results.append({"ok": False, "error": str(e), "type": ev.get("type")})
                ok = all(r.get("ok") for r in results)
                return self._json({"ok": ok, "results": results, "count": len(results)}, 200 if ok else 400)

            # ---- MC-MEMORY-GRAPH-1: admin reset ----
            if p.path == "/api/memory-graph/reset":
                # Authorization: either X-MC-Admin: yes header OR {confirm: true} body.
                try:
                    length = int(self.headers.get("Content-Length") or "0")
                except (TypeError, ValueError):
                    length = 0
                body_ok = False
                if length > 0 and length <= 4 * 1024:
                    raw = self.rfile.read(length)
                    try:
                        body = json.loads(raw.decode("utf-8") or "{}")
                        if isinstance(body, dict) and body.get("confirm") is True:
                            body_ok = True
                    except Exception:
                        body_ok = False
                header_ok = (self.headers.get("X-MC-Admin", "").strip().lower() == "yes")
                if not (body_ok or header_ok):
                    return self._json({
                        "error": "admin confirmation required",
                        "how": "POST {confirm: true} OR header X-MC-Admin: yes",
                    }, 403)
                return self._json(mg_reset(), 200)

            if p.path == "/api/data/kanban/task":
                # Read the body (Content-Length, capped to 16 KiB to be safe)
                try:
                    length = int(self.headers.get("Content-Length") or "0")
                except (TypeError, ValueError):
                    length = 0
                if length <= 0 or length > 16 * 1024:
                    return self._json({"error": "missing or oversized body"}, 400)
                raw = self.rfile.read(length)
                try:
                    payload = json.loads(raw.decode("utf-8"))
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    return self._json({"error": "invalid JSON", "detail": str(e)}, 400)
                if not isinstance(payload, dict):
                    return self._json({"error": "body must be a JSON object"}, 400)
                status, body = create_kanban_task(payload)
                return self._json(body, status)

            if p.path != "/api/data/order":
                return self._json({"error": "not found", "path": p.path}, 404)

            # Read the body (Content-Length, capped to 16 KiB to be safe)
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except (TypeError, ValueError):
                length = 0
            if length <= 0 or length > 16 * 1024:
                return self._json({"error": "missing or oversized body"}, 400)
            raw = self.rfile.read(length)
            try:
                payload = json.loads(raw.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                return self._json({"error": "invalid JSON", "detail": str(e)}, 400)
            if not isinstance(payload, dict):
                return self._json({"error": "body must be a JSON object"}, 400)

            try:
                result = _append_fix_order_event(payload)
            except ValueError as e:
                return self._json({"error": str(e)}, 400)
            return self._json(result, 200)

        except Exception as e:
            return self._json({"error": "server error", "detail": str(e)}, 500)

    def do_PATCH(self):
        """MC-KANBAN-1+2: PATCH /api/data/kanban/task/:id — update task's
        `kanban_status` on disk (separate from project-native `status`).
        Body: { "status": "<kanban_status>" }. Returns 200 on success with the full
        updated board, 400 on bad status, 404 on unknown task_id.

        MC-KANBAN-RUNNING-NOW-1 (2026-06-17): allowed statuses are now
            ("triage", "todo", "ready", "running_now", "blocked", "done", "archived")
        The old "running" status is no longer accepted (use "ready" for claimed/waiting
        or "running_now" for actively being worked on).

        MC-KANBAN-ASSIGN-1 (2026-06-17): PATCH /api/data/kanban/task/:id/assign
        — update task's `assigned_to` (Format A) or `owner` row (Format B).
        Body: { "assignee": "thor"|"forge"|"argus"|"" }. Returns 200 on
        success with the full updated board, 400 on bad assignee, 404 on
        unknown task_id. Empty `assignee` removes the field (unassign).
        """
        try:
            p = urllib.parse.urlparse(self.path)
            prefix = "/api/data/kanban/task/"
            if not p.path.startswith(prefix):
                return self._json({"error": "not found", "path": p.path}, 404)

            # MC-KANBAN-ASSIGN-1: /assign sub-route. Must be checked BEFORE
            # the bare /:id route below, so the suffix doesn't get mistaken
            # for a task_id.
            if p.path.endswith("/assign"):
                task_id = p.path[len(prefix):-len("/assign")].strip()
                if not task_id or "/" in task_id:
                    return self._json({"error": "task_id is required in path"}, 400)
                # Read body (capped to 4 KiB — only need {"assignee": "..."})
                try:
                    length = int(self.headers.get("Content-Length") or "0")
                except (TypeError, ValueError):
                    length = 0
                if length < 0 or length > 4 * 1024:
                    return self._json({"error": "missing or oversized body"}, 400)
                raw = self.rfile.read(length) if length > 0 else b"{}"
                try:
                    payload = json.loads(raw.decode("utf-8") or "{}")
                except (UnicodeDecodeError, json.JSONDecodeError) as e:
                    return self._json({"error": "invalid JSON", "detail": str(e)}, 400)
                if not isinstance(payload, dict):
                    return self._json({"error": "body must be a JSON object"}, 400)
                status, body = assign_kanban_task(task_id, payload)
                return self._json(body, status)

            # Original MC-KANBAN-2: PATCH /api/data/kanban/task/:id (status)
            task_id = p.path[len(prefix):].strip()
            if not task_id or "/" in task_id:
                return self._json({"error": "task_id is required in path"}, 400)
            # Read body (capped to 4 KiB — only need {"status": "..."})
            try:
                length = int(self.headers.get("Content-Length") or "0")
            except (TypeError, ValueError):
                length = 0
            if length < 0 or length > 4 * 1024:
                return self._json({"error": "missing or oversized body"}, 400)
            raw = self.rfile.read(length) if length > 0 else b"{}"
            try:
                payload = json.loads(raw.decode("utf-8") or "{}")
            except (UnicodeDecodeError, json.JSONDecodeError) as e:
                return self._json({"error": "invalid JSON", "detail": str(e)}, 400)
            if not isinstance(payload, dict):
                return self._json({"error": "body must be a JSON object"}, 400)
            new_status = payload.get("status") or ""
            status, body = patch_kanban_task(task_id, new_status)
            return self._json(body, status)
        except Exception as e:
            return self._json({"error": "server error", "detail": str(e)}, 500)


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    os.chdir(HERE)
    lan_note = "" if _LAN_IP_OK else " (auto-detect failed, using loopback)"
    _v = get_version()
    print(f"NofiTech Mission Control {_v['version']} ({_v['commit']})")
    print(f"  project:  {PROJECT_ROOT}")
    print(f"  company:  {COMPANY_ROOT}")
    print(f"  serving:  http://0.0.0.0:{PORT}/  (LAN access: http://{HOST_IP}:{PORT}/{lan_note})")
    with ReuseTCPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
