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
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response
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

    Stage 12 (DIY-012) added: ``query`` so the verified_components cache
    can be seeded with the original free-text query that produced this
    candidate. The frontend sends it alongside the rest of the create
    payload.
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
    # Stage 12: the original free-text query that produced this candidate.
    # Used to seed the verified_components cache.
    query: Optional[str] = None


class UpdateComponentRequest(BaseModel):
    """Stage 9: partial update payload. All fields optional; only those
    present are updated. Used by the inline quantity editor in the
    Inventory page (and any future edit forms).
    """
    name: Optional[str] = None
    model_number: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[int] = None
    location: Optional[str] = None
    voltage: Optional[str] = None
    interfaces: Optional[List[str]] = None
    key_specs: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    description: Optional[str] = None
    manufacturer: Optional[str] = None
    confidence: Optional[float] = None


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
    """Map a SQLAlchemy Row to the public JSON shape.

    Stage 7: parse the notes JSON blob and promote the descriptive fields
    (source, interfaces, key_specs, tags, description, voltage) to the
    top level so the Inventory page can render them directly.
    """
    raw: Dict[str, Any] = dict(row._mapping)
    # Parse the notes JSON blob and promote descriptive fields to top level.
    notes_raw = raw.pop("notes", None)
    notes_blob: Dict[str, Any] = {}
    if notes_raw:
        try:
            notes_blob = json.loads(notes_raw)
        except (TypeError, ValueError):
            notes_blob = {}
    for key in (
        "source",
        "voltage",
        "interfaces",
        "key_specs",
        "tags",
        "description",
    ):
        if key in notes_blob and not raw.get(key):
            raw[key] = notes_blob[key]
    # Default source to "live" if not set anywhere
    if not raw.get("source"):
        raw["source"] = "live"
    # Add a public image_url that the Inventory page can render. We resolve
    # the stored relative path to ``/api/images/<basename>`` which the
    # static file mount in main.py serves.
    image_path = raw.get("image_path")
    if image_path:
        raw["image_url"] = f"/api/images/{Path(image_path).name}"
    else:
        raw["image_url"] = None
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
# DIY-015 (Stage 13): Manual image upload helpers
# ---------------------------------------------------------------------------

# Whitelist of accepted image extensions for manual uploads.
_ALLOWED_EXTS = {"jpg", "jpeg", "png", "gif", "webp"}
_MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5 MB

# Content-Types we'll accept when downloading a URL.
_URL_ALLOWED_CT = {"image/jpeg", "image/jpg", "image/png", "image/gif", "image/webp"}

# Filename extension normaliser.
_EXT_FROM_CT = {
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/png": "png",
    "image/gif": "gif",
    "image/webp": "webp",
}


def _ext_from_filename(name: str) -> Optional[str]:
    """Return the canonical extension for an uploaded filename, or None if not allowed."""
    if not name:
        return None
    # Strip any query string and pull the last ".xxx".
    base = name.split("?", 1)[0].split("#", 1)[0]
    if "." not in base:
        return None
    ext = base.rsplit(".", 1)[-1].lower()
    if ext == "jpeg":
        ext = "jpg"
    return ext if ext in _ALLOWED_EXTS else None


def _save_bytes_to_images_dir(component_id: int, data: bytes, ext: str) -> Dict[str, str]:
    """Write ``data`` to ``data/images/<component-id>-<uuid>.<ext>``.

    Returns the public-shape fields for the response.
    """
    images_dir = Path(get_images_dir())
    images_dir.mkdir(parents=True, exist_ok=True)
    safe_id = int(component_id)
    short_uuid = uuid.uuid4().hex[:8]
    filename = f"{safe_id}-{short_uuid}.{ext}"
    abs_path = images_dir / filename
    abs_path.write_bytes(data)
    rel_path = str(abs_path.relative_to(_project_root()))
    return {"file_path": rel_path, "filename": filename}


def _validate_uploaded_bytes(data: bytes) -> Optional[str]:
    """Quick sanity check on uploaded bytes; returns an error message or None."""
    if not data:
        return "uploaded file is empty"
    if len(data) > _MAX_UPLOAD_BYTES:
        return f"file too large ({len(data)} bytes; max {_MAX_UPLOAD_BYTES})"
    return None


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

    # Stage 12 (DIY-012): if we have the original free-text query, also
    # write to the verified_components cache. The frontend may or may not
    # send the query; if not, we just skip the cache write.
    # The query comes through the `req.query` if the frontend sent it.
    original_query = getattr(req, "query", None) or ""
    if original_query.strip() and req.source == "live":
        try:
            from .. import identity_cache as _id_cache
            from ..identity import classify_query
            component_type = classify_query(req.name or "") or classify_query(original_query)
            source_urls = []
            if req.source_url:
                source_urls.append(req.source_url)
            if req.datasheet_url:
                source_urls.append(req.datasheet_url)
            if req.wikidata_id:
                source_urls.append(f"https://www.wikidata.org/wiki/{req.wikidata_id}")
            _id_cache.put_verified(
                query=original_query,
                canonical_name=req.name or "",
                manufacturer=req.manufacturer or None,
                model_number=req.model_number or None,
                component_type=component_type,
                description=req.description or None,
                voltage=req.voltage or None,
                interfaces=list(req.interfaces or []),
                specs={"key_specs": list(req.key_specs or [])},
                datasheet_url=req.datasheet_url or None,
                image_url=req.image_url or None,
                source_urls=source_urls,
                confidence=req.confidence,
                verified_by="nofi",
            )
        except Exception as exc:  # noqa: BLE001
            # Cache write is best-effort; do not fail the save.
            print(f"[create_component] verified cache write failed: {exc}", file=sys.stderr)

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


# Stage 9 fields that live in the ``notes`` JSON blob (not direct columns).
# PATCH needs to merge these INTO the existing blob.
_NOTES_FIELDS = ("voltage", "interfaces", "key_specs", "tags", "description")


@router.patch("/{component_id}")
def update_component(component_id: int, req: UpdateComponentRequest) -> Dict[str, Any]:
    """Stage 9: partial update. Only fields explicitly set in the body
    are written. ``notes``-blob fields (voltage, interfaces, key_specs,
    tags, description) are merged into the existing notes JSON, not
    replaced. Returns the updated row in the public shape.
    """
    # 1) Verify the component exists
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM components WHERE id = :id"),
            {"id": component_id},
        ).first()
    if not existing:
        raise HTTPException(status_code=404, detail=f"component {component_id} not found")

    # 2) Build the direct-column update set
    direct_payload: Dict[str, Any] = {}
    for fname in ("name", "model_number", "category", "quantity", "location", "manufacturer", "confidence"):
        val = getattr(req, fname, None)
        if val is not None:
            direct_payload[fname] = val

    # Validate quantity if present
    if "quantity" in direct_payload and direct_payload["quantity"] < 1:
        raise HTTPException(status_code=400, detail="'quantity' must be >= 1")

    # 3) Build the notes-merge payload
    notes_payload: Dict[str, Any] = {}
    for fname in _NOTES_FIELDS:
        val = getattr(req, fname, None)
        if val is not None:
            notes_payload[fname] = val

    # 4) Apply
    now = _now_iso()
    with engine.begin() as conn:
        if direct_payload:
            set_clauses = ", ".join(f"{k} = :{k}" for k in direct_payload)
            direct_payload["updated_at"] = now
            direct_payload["id"] = component_id
            conn.execute(
                text(f"UPDATE components SET {set_clauses}, updated_at = :updated_at WHERE id = :id"),
                direct_payload,
            )

        if notes_payload:
            # Merge into existing notes blob
            row = conn.execute(
                text("SELECT notes FROM components WHERE id = :id"),
                {"id": component_id},
            ).first()
            existing_blob: Dict[str, Any] = {}
            if row and row[0]:
                try:
                    existing_blob = json.loads(row[0])
                except (TypeError, ValueError):
                    existing_blob = {}
            existing_blob.update(notes_payload)
            conn.execute(
                text("UPDATE components SET notes = :notes, updated_at = :updated_at WHERE id = :id"),
                {"notes": json.dumps(existing_blob, ensure_ascii=False), "updated_at": now, "id": component_id},
            )

        row = conn.execute(
            text("SELECT * FROM components WHERE id = :id"),
            {"id": component_id},
        ).one()

    return _row_to_dict(row)


@router.post("/{component_id}/image")
async def upload_component_image(
    component_id: int,
    request: Request,
    image: Optional[UploadFile] = File(None),
    source_url: Optional[str] = Form(None),
) -> Dict[str, Any]:
    """DIY-015 (Stage 13): manually attach an image to an existing component.

    Two content-types are supported on the same URL:

    1. ``multipart/form-data`` with a file field named ``image`` and an
       optional ``source_url`` string field. NOFI picks a JPEG/PNG/etc.
       from disk and sends it.
    2. ``application/json`` with body ``{"url": "https://..."}``. The
       server downloads the URL with ``urllib``, validates the
       content-type, and stores it. Used when NOFI has the image hosted
       somewhere else.

    Storage layout: ``data/images/<component-id>-<uuid8>.<ext>`` so
    multiple uploads never collide and the audit trail is clear.

    Updates the component row's ``image_path``, ``image_source`` (one
    of ``user_uploaded`` / ``user_url``), and ``image_uploaded_at``
    (ISO timestamp).
    """
    # 1) Verify the component exists.
    with engine.connect() as conn:
        existing = conn.execute(
            text("SELECT id FROM components WHERE id = :id"),
            {"id": component_id},
        ).first()
    if not existing:
        raise HTTPException(
            status_code=404, detail=f"component {component_id} not found"
        )

    content_type = (request.headers.get("content-type") or "").lower()

    image_source: Optional[str] = None
    saved: Optional[Dict[str, str]] = None

    if "multipart/form-data" in content_type:
        # Path A: file upload.
        if image is None or not image.filename:
            raise HTTPException(
                status_code=400,
                detail="multipart upload requires a file field named 'image'",
            )
        ext = _ext_from_filename(image.filename or "")
        if ext is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    "unsupported file extension; allowed: "
                    + ", ".join(sorted(_ALLOWED_EXTS))
                ),
            )
        data = image.file.read()
        err = _validate_uploaded_bytes(data)
        if err:
            raise HTTPException(status_code=400, detail=err)
        saved = _save_bytes_to_images_dir(component_id, data, ext)
        image_source = "user_uploaded"

    elif "application/json" in content_type:
        # Path B: URL paste.
        try:
            body = await request.json()
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(
                status_code=400, detail=f"invalid JSON body: {exc}"
            ) from exc
        if not isinstance(body, dict):
            raise HTTPException(
                status_code=400, detail="JSON body must be an object"
            )
        url = (body.get("url") or "").strip()
        if not url:
            raise HTTPException(
                status_code=400, detail="JSON body must include a non-empty 'url' field"
            )
        if not (url.startswith("http://") or url.startswith("https://")):
            raise HTTPException(
                status_code=400, detail="'url' must be an http(s) URL"
            )

        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "DIYHubV1/0.1 (https://github.com/nofidofi; contact: nofidofi@local) Python-urllib",
                    "Accept": "image/*",
                },
            )
            with urllib.request.urlopen(req, timeout=_DOWNLOAD_TIMEOUT) as resp:
                data = resp.read()
                remote_ct = (resp.headers.get("Content-Type") or "").split(";")[0].strip().lower()
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, OSError) as exc:
            raise HTTPException(
                status_code=400, detail=f"failed to download URL: {exc}"
            ) from exc

        err = _validate_uploaded_bytes(data)
        if err:
            raise HTTPException(status_code=400, detail=err)

        ext: Optional[str] = _EXT_FROM_CT.get(remote_ct)
        if ext is None:
            # Fall back to URL extension.
            path_part = urllib.parse.urlparse(url).path
            ext = _ext_from_filename(path_part)
        if ext is None:
            raise HTTPException(
                status_code=400,
                detail=(
                    f"URL content-type {remote_ct!r} not allowed; need one of "
                    + ", ".join(sorted(_URL_ALLOWED_CT))
                ),
            )
        saved = _save_bytes_to_images_dir(component_id, data, ext)
        image_source = "user_url"
    else:
        raise HTTPException(
            status_code=400,
            detail=(
                "unsupported Content-Type; expected multipart/form-data or "
                "application/json"
            ),
        )

    assert saved is not None and image_source is not None  # noqa: S101

    # 2) Update the component row.
    now = _now_iso()
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                UPDATE components
                SET image_path = :image_path,
                    image_source = :image_source,
                    image_uploaded_at = :image_uploaded_at,
                    updated_at = :updated_at
                WHERE id = :id
                """
            ),
            {
                "image_path": saved["file_path"],
                "image_source": image_source,
                "image_uploaded_at": now,
                "updated_at": now,
                "id": component_id,
            },
        )
        row = conn.execute(
            text("SELECT * FROM components WHERE id = :id"),
            {"id": component_id},
        ).one()

    return _row_to_dict(row)


@router.delete("/{component_id}", status_code=204, response_class=Response)
def delete_component(component_id: int) -> Response:
    """Stage 9: hard delete a component and its image file (if any).

    Returns 204 No Content on success. Returns 404 if the component does
    not exist. The on-disk image file is removed best-effort; failure
    to remove the file does NOT fail the delete.
    """
    # 1) Look up the image path (if any) so we can remove the file after.
    image_path_to_remove: Optional[str] = None
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT image_path FROM components WHERE id = :id"),
            {"id": component_id},
        ).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"component {component_id} not found")
    if row[0]:
        image_path_to_remove = row[0]

    # 2) Delete the row (CASCADE handles images table FK if it exists)
    with engine.begin() as conn:
        # Remove from images table (best effort)
        conn.execute(
            text("DELETE FROM images WHERE file_path = :fp"),
            {"fp": image_path_to_remove} if image_path_to_remove else {"fp": ""},
        )
        # Also try matching by basename (some images have only basename stored)
        if image_path_to_remove:
            basename = Path(image_path_to_remove).name
            conn.execute(
                text("DELETE FROM images WHERE file_path LIKE :pat OR file_path = :bn"),
                {"pat": f"%/{basename}", "bn": basename},
            )
        result = conn.execute(
            text("DELETE FROM components WHERE id = :id"),
            {"id": component_id},
        )
        if result.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"component {component_id} not found")

    # 3) Remove the image file best-effort (do not fail the delete)
    if image_path_to_remove:
        try:
            full_path = _project_root() / image_path_to_remove
            if full_path.exists():
                full_path.unlink()
        except OSError as exc:
            print(f"[delete-component] could not remove image file {image_path_to_remove}: {exc}", file=sys.stderr)

    return Response(status_code=204)
