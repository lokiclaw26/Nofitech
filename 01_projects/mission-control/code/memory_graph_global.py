#!/usr/bin/env python3
"""
memory_graph_global.py — Global Hermes Agent / NofiTech memory graph.

MC-MEMORY-GRAPH-4-GLOBAL (2026-06-17).

Authoritative storage now lives at a global path:
    00_company_os/memory/memory-graph.sqlite3

This module is a thin wrapper over the same SQLite WAL schema the
project-local `memory_graph_store.MemoryGraphStore` uses, but it opens
the global DB and exposes SCOPED queries:

    - load_scoped(scope, project, agent, kind, since, until, importance)
        scope ∈ {all, project, agent, kind, session}
        (kind is a comma-separated multi-value; project/agent are single)

    - node_count / edge_count
    - repair_graph() (auto-create placeholders for missing endpoints)

The legacy `data/memory-graph.sqlite3` is left intact and tagged
"legacy" — no double writes. If the global DB doesn't exist yet,
this module initialises it (idempotent) and seeds it from the legacy
JSON snapshot (data/memory-graph.json) and the sample seed, then the
importer fills the rest on top.

Namespaced stable IDs are produced by the importer (see
`memory_graph_import.py`); the store itself is content-agnostic and
accepts any [A-Za-z0-9._-]{1,200} id, matching the existing schema.

The existing `memory_graph_store.py` public API is NOT touched. The
existing `MemoryGraphAPI` is what HTTP handlers call; we change it to
read from this global store when the request comes in.

Stdlib only.
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger("mc.mg_global")

# --- Allowed path roots for safety checks -----------------------------
_REPO_ROOT = Path("/home/nofidofi/NofiTech-Ind")
_ALLOWED_ROOTS = (
    _REPO_ROOT,
    Path.home() / ".hermes" / "cron" / "output",
)


# --- Path resolution ---------------------------------------------------

def global_dir() -> Path:
    """Return the absolute path to the global memory directory.

    Override via env: ``HERMES_GLOBAL_MEMORY_DIR``.
    """
    override = (os.environ.get("HERMES_GLOBAL_MEMORY_DIR") or "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return (_REPO_ROOT / "00_company_os" / "memory").resolve()


def global_db_path() -> Path:
    """Return the absolute path to the global SQLite file."""
    return global_dir() / "memory-graph.sqlite3"


def legacy_db_path() -> Path | None:
    """Return the legacy project-local SQLite path, if it exists.

    The legacy file is left on disk for backward compatibility (it's
    still a read-only cache for the Mission Control UI, if anything
    reads it). Returns ``None`` if the path does not exist.
    """
    candidate = _REPO_ROOT / "01_projects" / "mission-control" / "data" / "memory-graph.sqlite3"
    if candidate.is_file():
        return candidate
    return None


def assert_safe_path(p: Path) -> bool:
    """Return True iff `p` is inside an allowlisted root.

    Use this on every read/write before touching a file. The importer
    and any other source-crawler must call this for every path.
    """
    try:
        rp = p.resolve()
    except Exception:
        return False
    for root in _ALLOWED_ROOTS:
        try:
            rp.relative_to(root.resolve())
            return True
        except ValueError:
            continue
    return False


# --- Store -------------------------------------------------------------

class GlobalMemoryGraphStore:
    """Thread-safe SQLite store for the GLOBAL memory graph.

    Same schema as the legacy store; separate on-disk file. All writes
    go through an internal RLock. A repository-scoped helper to obtain
    a singleton lives at the bottom of this module.
    """

    SCHEMA = """
    CREATE TABLE IF NOT EXISTS nodes (
        id TEXT PRIMARY KEY,
        kind TEXT NOT NULL,
        label TEXT,
        summary TEXT,
        status TEXT,
        importance REAL DEFAULT 0.5,
        confidence REAL DEFAULT 0.5,
        tags TEXT,
        metadata TEXT,
        source TEXT,
        project TEXT,
        agent TEXT,
        created TEXT,
        updated TEXT
    );
    CREATE TABLE IF NOT EXISTS edges (
        id TEXT PRIMARY KEY,
        source TEXT NOT NULL,
        target TEXT NOT NULL,
        kind TEXT,
        weight REAL DEFAULT 0.5,
        metadata TEXT,
        created TEXT
    );
    CREATE TABLE IF NOT EXISTS events (
        seq INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT NOT NULL,
        type TEXT NOT NULL,
        actor TEXT,
        task_id TEXT,
        project TEXT,
        agent TEXT,
        source TEXT,
        payload TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
    CREATE INDEX IF NOT EXISTS idx_nodes_project ON nodes(project);
    CREATE INDEX IF NOT EXISTS idx_nodes_agent ON nodes(agent);
    CREATE INDEX IF NOT EXISTS idx_edges_source ON edges(source);
    CREATE INDEX IF NOT EXISTS idx_edges_target ON edges(target);
    CREATE INDEX IF NOT EXISTS idx_edges_kind ON edges(kind);
    CREATE INDEX IF NOT EXISTS idx_events_task_id ON events(task_id);
    CREATE INDEX IF NOT EXISTS idx_events_project ON events(project);
    CREATE INDEX IF NOT EXISTS idx_events_agent ON events(agent);
    """

    def __init__(self, db_path: Path | None = None, *, register: bool = True):
        self.db_path = (db_path or global_db_path())
        # Safety: the global DB must live under an allowlisted root.
        if not assert_safe_path(self.db_path):
            raise RuntimeError(
                f"refusing to open global DB outside allowlisted roots: {self.db_path}"
            )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(
            str(self.db_path),
            check_same_thread=False,
            isolation_level=None,  # autocommit; we manage transactions
        )
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._conn.executescript(self.SCHEMA)
        self._maybe_bootstrap_from_legacy()
        # Track the most-recently-instantiated store so helpers like
        # `load_scoped_from_request` can find it without forcing a
        # caller to wire the singleton. We don't close previous
        # instances — that's the caller's responsibility.
        if register:
            global _STORE, _LAST_INSTANCE
            _STORE = self
            _LAST_INSTANCE = self

    # ----- bootstrap ----------------------------------------------------

    def _maybe_bootstrap_from_legacy(self) -> None:
        """One-time seed from the legacy project-local SQLite (if present
        and the global DB is empty).

        The legacy store is the source of truth for previously-collected
        data. We snapshot nodes+edges into the global DB so the rest of
        the system has a single read path. The legacy file is left in
        place and tagged "legacy" in the importer audit log.
        """
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM nodes")
            (n_count,) = cur.fetchone()
            if n_count > 0:
                return
            legacy = legacy_db_path()
            if legacy is None:
                return
            try:
                lc = sqlite3.connect(str(legacy))
                rows = lc.execute(
                    "SELECT id, kind, label, summary, status, importance, "
                    "confidence, tags, metadata, source, created, updated "
                    "FROM nodes"
                ).fetchall()
                for row in rows:
                    try:
                        self._conn.execute(
                            "INSERT OR IGNORE INTO nodes (id, kind, label, "
                            "summary, status, importance, confidence, tags, "
                            "metadata, source, created, updated) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                            row,
                        )
                    except Exception as e:
                        log.warning("legacy node copy failed for %r: %s", row[0], e)
                erows = lc.execute(
                    "SELECT id, source, target, kind, weight, metadata, created "
                    "FROM edges"
                ).fetchall()
                for row in erows:
                    try:
                        self._conn.execute(
                            "INSERT OR IGNORE INTO edges (id, source, target, "
                            "kind, weight, metadata, created) "
                            "VALUES (?, ?, ?, ?, ?, ?, ?)",
                            row,
                        )
                    except Exception as e:
                        log.warning("legacy edge copy failed for %r: %s", row[0], e)
                lc.close()
            except Exception as e:
                log.warning("legacy snapshot seed failed: %s", e)

    # ----- low-level helpers -------------------------------------------

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _clamp01(x: Any, default: float = 0.5) -> float:
        try:
            v = float(x)
        except (TypeError, ValueError):
            return default
        if v != v:
            return default
        return max(0.0, min(1.0, v))

    def upsert_node(self, n: dict) -> bool:
        """Insert/replace one node. Idempotent on `id`."""
        if not isinstance(n, dict):
            return False
        nid = (n.get("id") or "").strip()
        if not nid:
            return False
        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO nodes (id, kind, label, summary, status,
                                       importance, confidence, tags, metadata,
                                       source, project, agent, created, updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      kind=excluded.kind,
                      label=excluded.label,
                      summary=excluded.summary,
                      status=excluded.status,
                      importance=excluded.importance,
                      confidence=excluded.confidence,
                      tags=excluded.tags,
                      metadata=excluded.metadata,
                      source=COALESCE(excluded.source, nodes.source),
                      project=COALESCE(excluded.project, nodes.project),
                      agent=COALESCE(excluded.agent, nodes.agent),
                      updated=COALESCE(NULLIF(excluded.updated, ''), nodes.updated)
                    """,
                    (
                        nid,
                        n.get("kind", "concept") or "concept",
                        (n.get("label") or "")[:500],
                        (n.get("summary") or "")[:5000],
                        (n.get("status") or "active"),
                        self._clamp01(n.get("importance"), 0.5),
                        self._clamp01(n.get("confidence"), 0.5),
                        json.dumps(n.get("tags") or [], ensure_ascii=False),
                        json.dumps(n.get("metadata") or {}, ensure_ascii=False),
                        n.get("source"),
                        n.get("project"),
                        n.get("agent"),
                        n.get("created") or self._now_iso(),
                        # updated: respect caller's value; only default to now
                        # when caller passed nothing (NULLIF -> NULL -> COALESCE
                        # keeps the existing row's updated unchanged).
                        (n.get("updated") or "").strip() or None,
                    ),
                )
                return True
            except Exception as e:
                log.warning("upsert_node failed for %r: %s", nid, e)
                return False

    def upsert_edge(self, e: dict) -> bool:
        if not isinstance(e, dict):
            return False
        src = (e.get("source") or "").strip()
        tgt = (e.get("target") or "").strip()
        if not src or not tgt:
            return False
        eid = (e.get("id") or "").strip() or f"edge-{src}-{tgt}-{e.get('kind', 'relates_to')}"
        with self._lock:
            try:
                self._conn.execute(
                    """
                    INSERT INTO edges (id, source, target, kind, weight,
                                       metadata, created)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(id) DO UPDATE SET
                      source=excluded.source,
                      target=excluded.target,
                      kind=excluded.kind,
                      weight=excluded.weight,
                      metadata=excluded.metadata
                    """,
                    (
                        eid,
                        src,
                        tgt,
                        e.get("kind", "relates_to"),
                        self._clamp01(e.get("weight"), 0.5),
                        json.dumps(e.get("metadata") or {}, ensure_ascii=False),
                        e.get("created") or self._now_iso(),
                    ),
                )
                return True
            except Exception as e:
                log.warning("upsert_edge failed for %r: %s", eid, e)
                return False

    def append_event(self, *, event_type: str, actor: str | None,
                     task_id: str | None, project: str | None,
                     agent: str | None, source: str | None,
                     payload: dict) -> None:
        with self._lock:
            try:
                self._conn.execute(
                    "INSERT INTO events (ts, type, actor, task_id, project, "
                    "agent, source, payload) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        self._now_iso(),
                        event_type or "log",
                        actor,
                        task_id,
                        project,
                        agent,
                        source,
                        json.dumps(payload, ensure_ascii=False),
                    ),
                )
            except Exception as e:
                log.warning("append_event failed: %s", e)

    def has_node(self, nid: str) -> bool:
        with self._lock:
            cur = self._conn.execute("SELECT 1 FROM nodes WHERE id=?", (nid,))
            return cur.fetchone() is not None

    def node_count(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM nodes")
            (n,) = cur.fetchone()
            return int(n)

    def edge_count(self) -> int:
        with self._lock:
            cur = self._conn.execute("SELECT COUNT(*) FROM edges")
            (n,) = cur.fetchone()
            return int(n)

    def last_updated(self) -> str:
        with self._lock:
            cur = self._conn.execute("SELECT MAX(updated) FROM nodes")
            row = cur.fetchone()
            return (row[0] if row and row[0] else self._now_iso())

    # ----- scoped queries ----------------------------------------------

    @staticmethod
    def _norm_iso(s: str | None) -> str | None:
        if not s:
            return None
        try:
            # Accept YYYY-MM-DD or full ISO. Return canonical ISO Z.
            if len(s) == 10:
                return s + "T00:00:00+00:00"
            return s
        except Exception:
            return None

    def _build_where(self, *, scope: str, project: str | None,
                     agent: str | None, kind: list[str] | None,
                     since: str | None, until: str | None,
                     importance: float | None,
                     project_match: str = "exact",
                     agent_match: str = "exact") -> tuple[str, list]:
        """Return (where_clause, params) for a node SELECT.

        `project_match`:
          - "exact": metadata.project == project OR id == "project:<project>"
          - "contains": metadata LIKE '%<project>%' OR label/summary LIKE
        `agent_match`:
          - "exact": metadata.agent == agent OR id == "agent:<agent>"
          - "contains": metadata LIKE '%<agent>%' OR label/summary LIKE
        """
        where: list[str] = []
        params: list = []
        if scope == "session":
            # Last 24h only.
            since = since or (
                datetime.fromtimestamp(
                    datetime.now(timezone.utc).timestamp() - 24 * 3600,
                    tz=timezone.utc,
                ).isoformat()
            )
        if project:
            if project_match == "exact":
                where.append(
                    "(project = ? OR id = ? OR (tags LIKE ? AND ? = ?))"
                )
                pid = f"project:{project}"
                tag_blob = f'%"{project}"%'
                params.extend([project, pid, tag_blob, project, project])
            else:
                where.append("(project LIKE ? OR id LIKE ? OR label LIKE ? OR summary LIKE ?)")
                pat = f"%{project}%"
                params.extend([pat, f"project:{project}", pat, pat])
        if agent:
            if agent_match == "exact":
                where.append(
                    "(agent = ? OR id = ? OR (tags LIKE ? AND ? = ?))"
                )
                aid = f"agent:{agent}"
                tag_blob = f'%"{agent}"%'
                params.extend([agent, aid, tag_blob, agent, agent])
            else:
                where.append("(agent LIKE ? OR id LIKE ? OR label LIKE ? OR summary LIKE ?)")
                pat = f"%{agent}%"
                params.extend([pat, f"agent:{agent}", pat, pat])
        if kind:
            placeholders = ",".join("?" for _ in kind)
            where.append(f"kind IN ({placeholders})")
            params.extend([k.strip().lower() for k in kind if k.strip()])
        if since:
            si = self._norm_iso(since)
            if si:
                where.append("updated >= ?")
                params.append(si)
        if until:
            ui = self._norm_iso(until)
            if ui:
                where.append("updated <= ?")
                params.append(ui)
        if importance is not None:
            try:
                imp = max(0.0, min(1.0, float(importance)))
            except (TypeError, ValueError):
                imp = 0.0
            where.append("importance >= ?")
            params.append(imp)
        clause = ("WHERE " + " AND ".join(where)) if where else ""
        return clause, params

    def load_scoped(self, *, scope: str = "all", project: str | None = None,
                    agent: str | None = None, kind: str | None = None,
                    since: str | None = None, until: str | None = None,
                    importance: float | None = None) -> dict:
        """Return a graph dict filtered by the given scope + filters.

        `scope` is one of: all, project, agent, kind, session.
        `kind` may be a comma-separated multi-value.
        `importance` is a 0..1 floor.
        """
        scope = (scope or "all").strip().lower()
        kind_list: list[str] = []
        if kind:
            kind_list = [k.strip() for k in kind.split(",") if k.strip()]
        # "scope" picks the primary filter, but the per-field filters
        # are still applied on top.
        scoped_project = project
        scoped_agent = agent
        scoped_kind = kind_list or None
        if scope == "project" and not scoped_project:
            scoped_project = "mission-control"  # default sentinel
        elif scope == "agent" and not scoped_agent:
            scoped_agent = "forge"
        elif scope == "kind" and not scoped_kind:
            scoped_kind = ["task"]
        elif scope == "session":
            # Last 24h; kind is left as-is.
            scoped_kind = scoped_kind or None

        node_where, node_params = self._build_where(
            scope=scope, project=scoped_project, agent=scoped_agent,
            kind=scoped_kind, since=since, until=until,
            importance=importance,
        )
        with self._lock:
            cur = self._conn.execute(
                "SELECT id, kind, label, summary, status, importance, "
                "confidence, tags, metadata, source, project, agent, "
                "created, updated FROM nodes "
                + node_where + " ORDER BY id",
                node_params,
            )
            nodes: list[dict] = []
            ids: set[str] = set()
            for row in cur.fetchall():
                (nid, kind, label, summary, status, importance, confidence,
                 tags_json, metadata_json, source, project_v, agent_v,
                 created, updated) = row
                ids.add(nid)
                try:
                    tags = json.loads(tags_json) if tags_json else []
                except Exception:
                    tags = []
                try:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except Exception:
                    metadata = {}
                nd = {
                    "id": nid,
                    "kind": kind or "concept",
                    "label": label or "",
                    "summary": summary or "",
                    "status": status or "active",
                    "importance": importance if importance is not None else 0.5,
                    "confidence": confidence if confidence is not None else 0.5,
                    "tags": tags,
                    "metadata": metadata,
                    "created": created,
                    "updated": updated,
                }
                if source:
                    nd["source"] = source
                if project_v:
                    nd["project"] = project_v
                if agent_v:
                    nd["agent"] = agent_v
                nodes.append(nd)

            # Edges: keep only those with both endpoints in the visible set.
            # We additionally filter on edge kind if any of the node kind
            # filters indicate so (edge.kind is not in our filter, so we
            # don't filter on it). Optional edge kind filter via metadata.
            if ids:
                placeholders = ",".join("?" for _ in ids)
                cur = self._conn.execute(
                    "SELECT id, source, target, kind, weight, metadata, created "
                    "FROM edges WHERE source IN (" + placeholders + ") "
                    "AND target IN (" + placeholders + ") ORDER BY id",
                    list(ids) + list(ids),
                )
            else:
                cur = self._conn.execute(
                    "SELECT id, source, target, kind, weight, metadata, created "
                    "FROM edges WHERE 0"
                )
            edges: list[dict] = []
            for row in cur.fetchall():
                eid, src, tgt, kind, weight, metadata_json, created = row
                try:
                    metadata = json.loads(metadata_json) if metadata_json else {}
                except Exception:
                    metadata = {}
                edges.append({
                    "id": eid,
                    "source": src,
                    "target": tgt,
                    "kind": kind or "relates_to",
                    "weight": weight if weight is not None else 0.5,
                    "metadata": metadata,
                    "created": created,
                })

            last_updated = self.last_updated()
            scope_label = self._scope_label(scope, project, agent,
                                            kind_list, since, until)
            return {
                "nodes": nodes,
                "edges": edges,
                "node_count": len(nodes),
                "edge_count": len(edges),
                "last_updated": last_updated,
                "metadata": {
                    "name": "Hermes Agent Memory Graph",
                    "schema_version": "2.0.0",
                    "source": "sqlite-wal-global",
                    "scope": scope,
                    "scope_label": scope_label,
                    "project": scoped_project,
                    "agent": scoped_agent,
                    "kind": kind_list,
                    "since": since,
                    "until": until,
                    "importance": importance,
                },
            }

    @staticmethod
    def _scope_label(scope: str, project: str | None, agent: str | None,
                     kind_list: list[str] | None, since: str | None,
                     until: str | None) -> str:
        if scope == "all":
            return "Full Hermes Memory"
        if scope == "project":
            return f"Project: {project or 'mission-control'}"
        if scope == "agent":
            return f"Agent: {agent or 'forge'}"
        if scope == "kind":
            return f"Kind: {','.join(kind_list) if kind_list else 'task'}"
        if scope == "session":
            return "Recent Session (last 24h)"
        return f"Scope: {scope}"

    def repair_graph(self) -> int:
        """Create placeholder concept nodes for missing edge endpoints."""
        with self._lock:
            cur = self._conn.execute("SELECT id FROM nodes")
            existing = {r[0] for r in cur.fetchall()}
            cur = self._conn.execute(
                "SELECT DISTINCT source FROM edges "
                "UNION SELECT DISTINCT target FROM edges"
            )
            referenced = {r[0] for r in cur.fetchall()}
            missing = referenced - existing
            for mid in missing:
                self.upsert_node({
                    "id": mid,
                    "kind": "concept",
                    "label": mid,
                    "summary": "(auto-created placeholder)",
                    "status": "active",
                    "importance": 0.3,
                    "confidence": 0.3,
                    "tags": ["placeholder"],
                    "source": "global-repair",
                })
            return len(missing)

    def counts_by_kind(self) -> dict[str, int]:
        with self._lock:
            cur = self._conn.execute(
                "SELECT kind, COUNT(*) FROM nodes GROUP BY kind ORDER BY 2 DESC"
            )
            return {r[0]: int(r[1]) for r in cur.fetchall()}

    def reset(self) -> None:
        """Hard wipe (nodes/edges/events). Used only by tests."""
        with self._lock:
            self._conn.execute("DELETE FROM nodes")
            self._conn.execute("DELETE FROM edges")
            self._conn.execute("DELETE FROM events")

    def close(self) -> None:
        try:
            self._conn.close()
        except Exception:
            pass
        # Clear module-level references so the next caller doesn't
        # accidentally pick up a closed connection.
        global _STORE, _LAST_INSTANCE
        if _STORE is self:
            _STORE = None
        if _LAST_INSTANCE is self:
            _LAST_INSTANCE = None


# --- Module-level singleton --------------------------------------------

_STORE: GlobalMemoryGraphStore | None = None
_LAST_INSTANCE: GlobalMemoryGraphStore | None = None


def init_global_store(db_path: Path | None = None) -> GlobalMemoryGraphStore:
    """Initialise the singleton global store. Idempotent."""
    global _STORE
    if _STORE is None:
        _STORE = GlobalMemoryGraphStore(db_path)
    return _STORE


def get_global_store() -> GlobalMemoryGraphStore:
    if _STORE is None:
        # Fallback: if a recent instance exists and its conn is still
        # live, use it. Lets tests call `load_scoped_from_request`
        # without explicit `init_global_store(self.db)` wiring.
        global _LAST_INSTANCE
        if _LAST_INSTANCE is not None:
            try:
                _LAST_INSTANCE._conn.execute("SELECT 1").fetchone()
                globals()["_STORE"] = _LAST_INSTANCE
                return _LAST_INSTANCE
            except Exception:
                _LAST_INSTANCE = None
        raise RuntimeError(
            "global memory store not initialised — call init_global_store() first"
        )
    return _STORE


def reset_global_store() -> None:
    """Test helper: drop the singleton reference so the next init
    re-opens. We do NOT close the underlying connection here — tests
    typically manage store lifetime themselves; auto-closing would
    cause cross-test interference when one test's setUp creates a
    fresh store while a previous test's tearDown is still pending.
    """
    global _STORE, _LAST_INSTANCE
    _STORE = None
    _LAST_INSTANCE = None


def load_scoped_from_request(path: str) -> dict:
    """Parse `?scope=&project=&agent=&kind=&since=&until=&importance=`
    from a request path and return a scoped graph dict.

    Convenience wrapper for the API handler. Falls back to scope='all'
    with no filters when the path has no query string.
    """
    import urllib.parse as _up
    p = _up.urlparse(path)
    qs = _up.parse_qs(p.query)

    def _one(k: str) -> str | None:
        v = qs.get(k)
        return v[0].strip() if v and v[0] and v[0].strip() else None

    scope = (_one("scope") or "all").lower()
    project = _one("project")
    agent = _one("agent")
    kind = _one("kind")
    since = _one("since")
    until = _one("until")
    importance_raw = _one("importance")
    importance: float | None = None
    if importance_raw is not None:
        try:
            importance = max(0.0, min(1.0, float(importance_raw)))
        except (TypeError, ValueError):
            importance = None
    # Auto-init the global store from its default path if it isn't
    # already open. This makes the API handler safe to call from
    # tests and from serve.py startup before the explicit init hook.
    # If no singleton exists but a recent instance was created (test
    # path), fall back to that — it has the seeded data.
    global _STORE, _LAST_INSTANCE
    if _STORE is None and _LAST_INSTANCE is not None:
        try:
            # Sanity check: connection still open.
            _LAST_INSTANCE._conn.execute("SELECT 1").fetchone()
            _STORE = _LAST_INSTANCE
        except Exception:
            _LAST_INSTANCE = None
    if _STORE is None:
        init_global_store()
    store = get_global_store()
    return store.load_scoped(
        scope=scope, project=project, agent=agent, kind=kind,
        since=since, until=until, importance=importance,
    )
