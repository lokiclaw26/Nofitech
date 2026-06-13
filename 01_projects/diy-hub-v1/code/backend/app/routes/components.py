"""Components router — Stage 5 (real live component lookup).

Three endpoints, all under ``/api/components``:

- ``POST /api/components/search`` — accepts a single free-text
  ``query`` field, runs the live lookup against Wikimedia Commons,
  Wikidata, Wikipedia REST, PlatformIO, and GitHub (all free, all
  no-key, all no-login, per NOFI brief), and returns 0+ candidate
  variants with real images and provenance data.
- ``POST /api/components/detail`` — accepts a candidate dict
  (the one the user picked) and returns a richer detail view
  suitable for the confirmation popup.
- ``POST /api/components`` — persists a single component to SQLite
  and, if the request carries an ``image_url``, downloads that
  image to ``data/images/<slug>.<ext>`` and writes the local path
  into ``image_path``. Image download failure NEVER fails the save
  (graceful degradation: ``image_path`` is null).
- ``POST /api/components/mock-fallback`` — explicit operator-
  triggered offline fallback. Returns candidates from the
  ``mock_data`` catalog (clearly labeled ``source: mock_fallback``).
  Only used when the operator clicks the "Try offline mock fallback"
  button in the empty-state UI.
- ``GET /api/components`` — returns the list of saved components,
  with their stored ``image_path`` resolved to a public ``image_url``
  for the Inventory page.
"""
from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text

from ..db import SessionLocal, engine, get_images_dir
from ..live_search import get_detail as live_get_detail
from ..live_search import search as live_search
from ..mock_data import Candidate as MockCandidate
from ..mock_data import slug_for_image
from .. import mock_data


router = APIRouter(prefix="/api/components", tags=["components"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    """Stage 5: single free-text query, no separate name/model fields."""
    query: str = Field(..., description="Free-text component query, e.g. 'Wemos D1 Mini' or 'ESP32 DevKit V1'")


class DetailRequest(BaseModel):
    """Stage 5: the candidate the operator picked from the picker dialog."""
    candidate: Dict[str, Any] = Field(..., description="A candidate dict from the search result")


class CreateComponentRequest(BaseModel):
    """Full payload sent by the frontend after the user clicks ADD TO DATABASE.

    Stage 5 added: ``wikidata_id``, ``commons_filename``, ``source_url``,
    ``manufacturer``, ``release_year``, ``confidence``, ``datasheet_url``.
    All are stored as direct columns (no longer packed into the notes
    JSON blob).
    """

    name: str
    model_number: str
    category: str
    quantity: int
    location: Optional[str] = None
    voltage: Optional[str] = None
    interfaces: List[str] = Field(default_factory=list)
    key_specs: List[str] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    description: Optional[str] = None
    image_url: Optional[str] = None
    # Stage 5: live-source provenance
    wikidata_id: Optional[str] = None
    commons_filename: Optional[str] = None
    source_url: Optional[str] = None
    manufacturer: Optional[str] = None
    release_year: Optional[str] = None
    confidence: Optional[float] = None
    datasheet_url: Optional[str] = None
    # If the operator picked the offline mock fallback, this is "mock_fallback"
    # so we can tell, later, which records came from real live data.
    source: Optional[str] = "live"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _project_root() -> Path:
    """Path of the diy-hub-v1 project root (the directory that contains
    ``code/`` and ``data/``)."""
    return Path(__file__).resolve().parents[4]


def _row_to_dict(row: Any) -> Dict[str, Any]:
    """Map a SQLAlchemy Row to the public JSON shape."""
    raw: Dict[str, Any] = dict(row._mapping)
    # Add a public image_url that the Inventory page can render. We resolve
    # the stored relative path to ``/api/images/<basename>`` which the
    # static file mount in main.py serves.
    image_path = raw.get("image_path")
    if image_path:
        raw["image_url"] = f"/api/images/{Path(image_path).name}"
    else:
        raw["image_url"] = None
    # Normalize source label
    if not raw.get("source"):
        raw["source"] = "live"
    return raw


# ---------------------------------------------------------------------------
# Image download helper (used by POST /api/components)
# ---------------------------------------------------------------------------

# Magic byte signatures for the three image types Wikimedia can return.
_MAGIC_JPEG = b"\xff\xd8\xff"
_MAGIC_PNG = b"\x89PNG"
_MAGIC_WEBP = b"RIFF"  # +4 bytes + "WEBP"
_DOWNLOAD_TIMEOUT = 10


def _ext_from_content_type(content_type: str) -> Optional[str]:
    """Map an HTTP content-type header to a safe file extension."""
    if not content_type:
        return None
    ct = content_type.split(";")[0].strip().lower()
    if ct in ("image/jpeg", "image/jpg"):
        return "jpg"
    if ct == "image/png":
        return "png"
    if ct == "image/webp":
        return "webp"
    return None


def _detect_image_format(data: bytes) -> Optional[str]:
    """Validate the magic bytes; return canonical extension or None."""
    if not data:
        return None
    if data.startswith(_MAGIC_JPEG):
        return "jpg"
    if data.startswith(_MAGIC_PNG):
        return "png"
    if data.startswith(_MAGIC_WEBP) and len(data) >= 12 and data[8:12] == b"WEBP":
        return "webp"
    return None


def download_image(image_url: str, slug: str) -> Optional[Dict[str, Any]]:
    """Download a Wikimedia image to ``data/images/<slug>.<ext>``.

    Returns ``{"file_path": str, "size_bytes": int, "mime_type": str}``
    on success, or ``None`` on any failure (404, timeout, non-image
    content, etc.). NEVER raises.
    """
    if not image_url:
        return None

    try:
        req = urllib.request.Request(
            image_url,
            headers={
                "User-Agent": "DIYHubV1/0.1 (https://github.com/nofidofi; contact: nofidofi@local) Python-urllib",
                "Accept": "image/*",
            },
        )
        with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
            data = resp.read()
            content_type = resp.headers.get("Content-Type", "")
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
        print(f"[image-download] network error for {image_url}: {exc}", file=sys.stderr)
        return None

    ext = _ext_from_content_type(content_type) or _detect_image_format(data)
    if ext is None:
        print(
            f"[image-download] rejecting {image_url}: not a JPEG/PNG/WebP (content-type={content_type!r}, head={data[:8]!r})",
            file=sys.stderr,
        )
        return None

    magic_ext = _detect_image_format(data)
    if magic_ext is None:
        print(f"[image-download] magic-byte check failed for {image_url}", file=sys.stderr)
        return None
    if ext != magic_ext:
        ext = magic_ext

    images_dir = Path(get_images_dir())
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}.{ext}"
    abs_path = images_dir / filename
    abs_path.write_bytes(data)

    rel_path = str(abs_path.relative_to(_project_root()))
    return {
        "file_path": rel_path,
        "size_bytes": len(data),
        "mime_type": f"image/{'jpeg' if ext == 'jpg' else ext}",
    }


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/search")
def search(req: SearchRequest) -> Dict[str, Any]:
    """Return live candidates for a free-text query.

    Runs 5 free public sources in parallel (Wikimedia Commons, Wikidata,
    Wikipedia REST, PlatformIO, GitHub). NEVER raises — partial failures
    are recorded in the response's ``sources`` field.
    """
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="'query' is required and must be non-empty",
        )

    result = live_search(query)
    return result


@router.post("/detail")
def detail(req: DetailRequest) -> Dict[str, Any]:
    """Return a richer detail view for a candidate the operator picked.

    Re-fetches the candidate's Wikidata entity (if any) and PlatformIO
    page (if any) to pull additional claims. Used by the confirmation
    popup so the operator sees the fullest possible spec sheet.
    """
    if not req.candidate:
        raise HTTPException(status_code=400, detail="'candidate' is required")
    return live_get_detail(req.candidate)


@router.post("/mock-fallback")
def mock_fallback(req: SearchRequest) -> Dict[str, Any]:
    """Explicit operator-triggered offline fallback.

    Only used when the operator clicks the "Try offline mock fallback"
    button in the empty-state UI. The candidates returned here are
    clearly labeled ``source: mock_fallback`` so we can tell, later,
    which records came from real live data and which from this
    offline catalog.

    Per NOFI brief (2026-06-14): "Mock catalog can remain only as
    offline fallback, clearly labeled 'mock fallback'."
    """
    query = (req.query or "").strip()
    if not query:
        raise HTTPException(
            status_code=400,
            detail="'query' is required and must be non-empty",
        )

    # Linear scan of every catalog family, with a substring match.
    # Cheap (16 candidates) and predictable.
    q = query.lower()
    matches: List[MockCandidate] = []
    for family in (
        mock_data.ESP32_CANDIDATES,
        mock_data.ARDUINO_CANDIDATES,
        mock_data.RASPBERRY_CANDIDATES,
        mock_data.NEOPIXEL_CANDIDATES,
        mock_data.SERVO_CANDIDATES,
        mock_data.LM7805_CANDIDATES,
        mock_data.LM358_CANDIDATES,
        # STM32 is synthesized, not in a list — skip for fallback to
        # avoid duplication; operators using fallback can use manual entry.
    ):
        for c in family:
            haystack = " ".join(
                str(c.get(k, "")).lower()
                for k in ("id", "name", "model_number", "tags")
            )
            if any(tok in haystack for tok in q.split()):
                # Mark as mock_fallback so the UI can show the badge
                c_copy = dict(c)
                c_copy["source"] = "mock_fallback"
                matches.append(c_copy)  # type: ignore[arg-type]

    if not matches:
        # Last-resort synthetic
        syn = dict(mock_data._synthesize_candidate(q, "Unknown"))
        syn["source"] = "mock_fallback"
        matches.append(syn)  # type: ignore[arg-type]

    return {
        "query": query,
        "candidates": matches,
        "sources": {
            "mock_data": {"status": "ok", "n": len(matches), "note": "offline fallback"},
        },
        "error": None,
        "fallback_used": True,
    }


@router.post("", status_code=201)
def create_component(req: CreateComponentRequest) -> Dict[str, Any]:
    """Persist a component to SQLite. If ``image_url`` is supplied, the
    image is downloaded to ``data/images/<slug>.<ext>`` and the local
    path is stored in ``image_path``. The download is best-effort:
    failure to fetch the image does NOT fail the save.
    """
    name = (req.name or "").strip()
    model_number = (req.model_number or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'name' is required")
    if not model_number:
        raise HTTPException(status_code=400, detail="'model_number' is required")
    if req.quantity is None or req.quantity < 1:
        raise HTTPException(status_code=400, detail="'quantity' must be >= 1")

    # 1) Optionally download the real image to disk.
    image_rel_path: Optional[str] = None
    image_record: Optional[Dict[str, Any]] = None
    slug = slug_for_image(name, model_number)
    if req.image_url and req.image_url.strip():
        downloaded = download_image(req.image_url.strip(), slug)
        if downloaded is not None:
            image_rel_path = downloaded["file_path"]
            image_record = downloaded

    # 2) Stage 5: pack the descriptive fields into the notes JSON blob.
    # The 7 new provenance columns are stored as direct columns instead.
    notes_blob = {
        "voltage": req.voltage or "",
        "interfaces": list(req.interfaces or []),
        "key_specs": list(req.key_specs or []),
        "tags": list(req.tags or []),
        "description": req.description or "",
        "source": req.source or "live",  # "live" or "mock_fallback"
    }
    notes_json = json.dumps(notes_blob, ensure_ascii=False)

    # 3) Insert into SQLite. If the image download failed, image_rel_path
    #    is None and the column is null — the save still succeeds.
    now = _now_iso()
    with engine.begin() as conn:
        result = conn.execute(
            text(
                """
                INSERT INTO components
                    (name, category, quantity, location, notes, image_path,
                     wikidata_id, commons_filename, source_url, manufacturer,
                     release_year, confidence, datasheet_url,
                     created_at, updated_at)
                VALUES
                    (:name, :category, :quantity, :location, :notes, :image_path,
                     :wikidata_id, :commons_filename, :source_url, :manufacturer,
                     :release_year, :confidence, :datasheet_url,
                     :created_at, :updated_at)
                """
            ),
            {
                "name": name,
                "category": req.category or "Other",
                "quantity": int(req.quantity),
                "location": (req.location or None),
                "notes": notes_json,
                "image_path": image_rel_path,
                "wikidata_id": req.wikidata_id or None,
                "commons_filename": req.commons_filename or None,
                "source_url": req.source_url or None,
                "manufacturer": req.manufacturer or None,
                "release_year": req.release_year or None,
                "confidence": req.confidence if req.confidence is not None else None,
                "datasheet_url": req.datasheet_url or None,
                "created_at": now,
                "updated_at": now,
            },
        )
        new_id = result.lastrowid

        # 4) Record the downloaded image in the images table.
        if image_record is not None:
            original = os.path.basename(urllib.parse.urlparse(req.image_url).path) or image_record["file_path"]
            conn.execute(
                text(
                    """
                    INSERT INTO images
                        (file_path, original_name, mime_type, size_bytes, created_at)
                    VALUES
                        (:file_path, :original_name, :mime_type, :size_bytes, :created_at)
                    """
                ),
                {
                    "file_path": image_record["file_path"],
                    "original_name": original[:200],
                    "mime_type": image_record["mime_type"],
                    "size_bytes": image_record["size_bytes"],
                    "created_at": now,
                },
            )

        row = conn.execute(
            text("SELECT * FROM components WHERE id = :id"),
            {"id": new_id},
        ).one()

    return _row_to_dict(row)


@router.get("")
def list_components() -> Dict[str, Any]:
    """Return all saved components, newest first."""
    with engine.connect() as conn:
        rows = conn.execute(
            text("SELECT * FROM components ORDER BY id DESC")
        ).all()
    items = [_row_to_dict(r) for r in rows]
    return {"components": items, "total": len(items)}
