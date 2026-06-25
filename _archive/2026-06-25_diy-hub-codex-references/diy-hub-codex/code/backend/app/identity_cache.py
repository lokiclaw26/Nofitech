"""DIY Hub V1 — Stage 12: verified / rejected cache helpers.

The component identity engine consults the ``verified_components`` table on
every search (rule 10) and consults the ``rejected_components`` table to drop
candidates the operator has previously marked as wrong (rule 5).

This module is stdlib-only (sqlite3 + json). It does NOT import SQLAlchemy
so it can be called from background threads (like live_search's
ThreadPoolExecutor) without conflicting with the request-time engine.
"""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .db import get_db_path


# ---------------------------------------------------------------------------
# Query signature: a normalized form of the free-text query that we use to
# match against the verified cache.
# ---------------------------------------------------------------------------

def query_signature(query: str) -> str:
    """Return a stable, normalized signature for a free-text query.

    Same logic as the token-set normalizer: lowercase, alphanumeric-only,
    tokens sorted, joined. Two queries that differ only in word order or
    extra whitespace collapse to the same signature.

    >>> query_signature("Wemos D1 Mini")
    'd1miniwemos'
    >>> query_signature("  d1 mini wemos  ")
    'd1miniwemos'
    """
    q = (query or "").lower().strip()
    # Keep alphanumerics, split on non-alphanumeric
    tokens = re.findall(r"[a-z0-9]+", q)
    return "".join(sorted(tokens))


def candidate_signature(candidate: Dict[str, Any]) -> str:
    """A stable hash identifying this candidate (used to record rejections).

    The signature is over the title + source_url + (optional) wikidata_id.
    That way "Wemos D1 Mini" from Adafruit vs "Wemos D1 Mini" from PlatformIO
    are the SAME signature (same title), but "Wemos D1 Mini Pro" is different.
    """
    parts = [
        (candidate.get("title") or candidate.get("name") or "").lower().strip(),
        (candidate.get("source_url") or "").lower().strip(),
        (candidate.get("wikidata_id") or "").strip(),
        (candidate.get("commons_filename") or "").strip(),
    ]
    blob = "|".join(parts)
    return hashlib.sha1(blob.encode("utf-8")).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Verified cache lookup + store
# ---------------------------------------------------------------------------

def get_verified(query: str) -> Optional[Dict[str, Any]]:
    """Return a verified_components row for this query, or None.

    The returned dict mirrors the SQL row but with ``interfaces``,
    ``specs``, ``source_urls`` deserialized from JSON.
    """
    sig = query_signature(query)
    if not sig:
        return None
    try:
        with sqlite3.connect(get_db_path()) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM verified_components WHERE query_signature = ?",
                (sig,),
            ).fetchone()
    except sqlite3.OperationalError:
        # Table doesn't exist yet (very early boot or test setup) — return
        # None silently. init_db() creates it on app boot.
        return None
    if not row:
        return None
    out = dict(row)
    for key in ("interfaces", "specs", "source_urls"):
        raw = out.get(key)
        if isinstance(raw, str) and raw:
            try:
                out[key] = json.loads(raw)
            except (TypeError, ValueError):
                out[key] = []
        elif raw is None:
            out[key] = []
    return out


def put_verified(
    *,
    query: str,
    canonical_name: str,
    manufacturer: Optional[str] = None,
    model_number: Optional[str] = None,
    component_type: Optional[str] = None,
    description: Optional[str] = None,
    voltage: Optional[str] = None,
    interfaces: Optional[List[str]] = None,
    specs: Optional[Dict[str, Any]] = None,
    datasheet_url: Optional[str] = None,
    image_url: Optional[str] = None,
    source_urls: Optional[List[str]] = None,
    confidence: Optional[float] = None,
    verified_by: str = "nofi",
) -> Dict[str, Any]:
    """Upsert a verified-components row for this query. Returns the row."""
    sig = query_signature(query)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    interfaces_json = json.dumps(interfaces or [], ensure_ascii=False)
    specs_json = json.dumps(specs or {}, ensure_ascii=False)
    source_urls_json = json.dumps(source_urls or [], ensure_ascii=False)
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO verified_components
                (query_signature, canonical_name, manufacturer, model_number,
                 component_type, description, voltage, interfaces, specs,
                 datasheet_url, image_url, source_urls, confidence,
                 verified_at, verified_by)
            VALUES
                (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(query_signature) DO UPDATE SET
                canonical_name = excluded.canonical_name,
                manufacturer = excluded.manufacturer,
                model_number = excluded.model_number,
                component_type = excluded.component_type,
                description = excluded.description,
                voltage = excluded.voltage,
                interfaces = excluded.interfaces,
                specs = excluded.specs,
                datasheet_url = excluded.datasheet_url,
                image_url = excluded.image_url,
                source_urls = excluded.source_urls,
                confidence = excluded.confidence,
                verified_at = excluded.verified_at,
                verified_by = excluded.verified_by
            """,
            (
                sig,
                canonical_name,
                manufacturer or "",
                model_number or "",
                component_type or "",
                description or "",
                voltage or "",
                interfaces_json,
                specs_json,
                datasheet_url or "",
                image_url or "",
                source_urls_json,
                confidence if confidence is not None else 1.0,
                now,
                verified_by,
            ),
        )
        conn.commit()
    return get_verified(query) or {}


# ---------------------------------------------------------------------------
# Rejection cache
# ---------------------------------------------------------------------------

def get_rejected_signatures(query: str) -> List[str]:
    """Return the list of candidate_signatures the operator has rejected
    for this query. The caller drops any candidate whose signature is in
    this list."""
    sig = query_signature(query)
    if not sig:
        return []
    try:
        with sqlite3.connect(get_db_path()) as conn:
            rows = conn.execute(
                "SELECT candidate_signature FROM rejected_components WHERE query_signature = ?",
                (sig,),
            ).fetchall()
    except sqlite3.OperationalError:
        # Table doesn't exist yet (very early boot or test setup) — return
        # empty list silently. init_db() creates it on app boot.
        return []
    return [r[0] for r in rows]


def put_rejected(query: str, candidate: Dict[str, Any], reason: str = "") -> None:
    """Record that the operator rejected ``candidate`` for ``query``."""
    sig = query_signature(query)
    cand_sig = candidate_signature(candidate)
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    with sqlite3.connect(get_db_path()) as conn:
        conn.execute(
            """
            INSERT INTO rejected_components
                (query_signature, candidate_signature, reason, rejected_at)
            VALUES (?, ?, ?, ?)
            """,
            (sig, cand_sig, reason or "", now),
        )
        conn.commit()


__all__ = [
    "candidate_signature",
    "get_rejected_signatures",
    "get_verified",
    "put_rejected",
    "put_verified",
    "query_signature",
]
