#!/usr/bin/env python3
"""
NofiTech Mission Control v1.7.0 (Logs/Health panel)
Local-only dashboard for NOFI. 3-agent company. 6 sections.
Stage 9: Logs/Health panel with 7 fields (events, errors, warnings, app/api health, last verification, env status).

Endpoints:
  GET  /                              → static HTML
  GET  /mission-control.html          → static HTML (alt)
  GET  /api/health                    → {status, version, uptime_sec}
  GET  /api/version                   → {version, commit, uptime_sec, started_at}
  GET  /api/data/overview             → 6 fields, real or null+reason
  GET  /api/data/agents               → 3 rows: thor, forge, argus
  GET  /api/data/tasks                → 0+ rows from 01_projects/*/tasks/*.md
  GET  /api/data/projects             → 0+ rows from 01_projects/*/status.md
  GET  /api/data/provider             → 2 rows: free, paid
  GET  /api/data/logs                 → events + health + env (no secret values)
"""
import http.server
import socketserver
import json
import os
import re
import time
import urllib.parse
import glob
from pathlib import Path
from datetime import datetime, timezone

PORT = 8767
HOST = "0.0.0.0"  # v1.3.0 — full LAN access (reversed Stage-1 'local only' lock per NOFI directive)
HOST_IP = "192.168.0.29"  # NOFI's local network IP, for banner display only
HERE = Path(__file__).parent.resolve()
PROJECT_ROOT = HERE.parent              # 01_projects/mission-control
COMPANY_ROOT = PROJECT_ROOT.parent.parent  # ~/NofiTech-Ind
START_TIME = time.time()
VERSION = "1.7.0"
COMMIT = "v1.7.0-logs-health-panel"  # v1.7.0 — Stage 9 Logs/Health panel (7 fields, real level detection, env status w/o values)

# ---- 3-agent company (locked 2026-06-10, charter v3.0) ----
AGENTS = ["thor", "forge", "argus"]

AGENT_META = {
    "thor":  {"name": "Thor",  "role": "CEO / Planner / Coordinator", "emoji": "⚡"},
    "forge": {"name": "Forge", "role": "Builder / Engineer / DevOps", "emoji": "🔨"},
    "argus": {"name": "Argus", "role": "QA / Tester / Security",       "emoji": "👁️"},
}


# ---------- helpers ----------

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

    # 3. Active tasks count: tasks with status open|in-progress across all projects
    active = 0
    failed = 0
    blocked = 0
    total = 0
    tasks_dirs = list((COMPANY_ROOT / "01_projects").glob("*/tasks"))
    for td in tasks_dirs:
        for tf in td.glob("*.md"):
            txt = safe_read(tf)
            if not txt:
                continue
            meta, _ = parse_frontmatter(txt)
            total += 1
            st = (meta.get("status") or "").lower()
            if st in ("open", "in-progress", "blocked"):
                active += 1
            if st == "failed":
                failed += 1
            if st == "blocked":
                blocked += 1
    out["active_tasks"] = {
        "value": active if total else None,
        "reason": None if total else "no tasks yet",
    }
    out["failed_tasks"] = {
        "value": failed if total else None,
        "reason": None if total else "no tasks yet",
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

        rows.append({
            "id": oid,
            "name": meta["name"],
            "role": meta["role"],
            "emoji": meta["emoji"],
            "status": status,
            "last_activity": rel_time(last_mtime) if last_mtime else "—",
            "last_activity_iso": datetime.fromtimestamp(last_mtime, tz=timezone.utc).isoformat() if last_mtime else None,
            "last_log": str(last_file.relative_to(COMPANY_ROOT)) if last_file else None,
            "current_assignment": current_assignment,
            "blocker": blocker,
            "reasons": reasons,
        })
    return {"agents": rows, "count": len(rows)}


def data_tasks():
    """All tasks across all projects."""
    rows = []
    for td in (COMPANY_ROOT / "01_projects").glob("*/tasks"):
        for tf in td.glob("*.md"):
            txt = safe_read(tf)
            if not txt:
                continue
            meta, body = parse_frontmatter(txt)
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
    rows.sort(key=lambda r: r.get("updated") or "", reverse=True)
    sources = set()
    for r in rows:
        if r.get("data_source"):
            sources.add(r["data_source"])
    return {
        "tasks": rows,
        "count": len(rows),
        "data_sources": sorted(sources) if sources else [],
        "reason": None if rows else "no tasks yet — Thor hasn't opened one",
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
    """
    events = []
    roots = [COMPANY_ROOT / "00_company_os" / "04_agents" / "logs"]
    for proj in (COMPANY_ROOT / "01_projects").glob("*/logs"):
        roots.append(proj)

    errors = 0
    warnings = 0
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

            # Real level detection
            level = (meta.get("level") or "").lower()
            if not level:
                # Infer from filename and body
                fname = f.stem.lower()
                body_low = (body or "")[:500].lower()
                if any(k in fname for k in ["error", "fail"]) or any(k in body_low for k in ["error:", "failed", "exception", "traceback"]):
                    level = "error"
                elif any(k in fname for k in ["warn"]) or "warn:" in body_low or "warning" in body_low:
                    level = "warn"
                else:
                    level = "info"
            if level == "error":
                errors += 1
            elif level == "warn":
                warnings += 1

            events.append({
                "ts": datetime.fromtimestamp(f.stat().st_mtime, tz=timezone.utc).isoformat(),
                "rel": rel_time(f.stat().st_mtime),
                "source": str(f.relative_to(COMPANY_ROOT)),
                "officer": (meta.get("officer") or meta.get("agent") or (f.stem.split("-")[0] if "-" in f.stem else None)),
                "level": level,
                "title": meta.get("title") or f.stem,
            })

            # Track last verification (argus-*.md)
            if f.stem.startswith("argus-") and (last_verification is None or f.stat().st_mtime > last_verification):
                last_verification = f.stat().st_mtime
                last_verification_source = str(f.relative_to(COMPANY_ROOT))

    events.sort(key=lambda e: e["ts"], reverse=True)
    events = events[:20]

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
        "app_health": app_health,
        "app_health_reason": app_health_reason,
        "api_health": api_health,
        "api_health_reason": api_health_reason,
        "last_verification": datetime.fromtimestamp(last_verification, tz=timezone.utc).isoformat() if last_verification else None,
        "last_verification_rel": rel_time(last_verification) if last_verification else "—",
        "last_verification_source": last_verification_source,
        "env": _env_status(),
    }


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
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        try:
            p = urllib.parse.urlparse(self.path)
            path = p.path

            if path in ("/", "/mission-control.html", "/index.html"):
                return self._static("mission-control.html")

            if path == "/api/health":
                return self._json({
                    "status": "ok",
                    "version": VERSION,
                    "uptime_sec": int(time.time() - START_TIME),
                })

            if path == "/api/version":
                return self._json({
                    "version": VERSION,
                    "commit": COMMIT,
                    "uptime_sec": int(time.time() - START_TIME),
                    "started_at": datetime.fromtimestamp(START_TIME, tz=timezone.utc).isoformat(),
                })

            if path == "/api/data/overview":
                return self._json(data_overview())
            if path == "/api/data/agents":
                return self._json(data_agents())
            if path == "/api/data/tasks":
                return self._json(data_tasks())
            if path == "/api/data/projects":
                return self._json(data_projects())
            if path == "/api/data/provider":
                return self._json(data_provider())
            if path == "/api/data/logs":
                return self._json(data_logs())

            return self._json({"error": "not found", "path": path}, 404)

        except Exception as e:
            return self._json({"error": "server error", "detail": str(e)}, 500)


class ReuseTCPServer(socketserver.TCPServer):
    allow_reuse_address = True


def main():
    os.chdir(HERE)
    print(f"NofiTech Mission Control {VERSION} ({COMMIT})")
    print(f"  project:  {PROJECT_ROOT}")
    print(f"  company:  {COMPANY_ROOT}")
    print(f"  serving:  http://0.0.0.0:{PORT}/  (LAN access: http://{HOST_IP}:{PORT}/)")
    with ReuseTCPServer((HOST, PORT), Handler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
