"""Components router — Stage 3 (real Wikipedia images).

Three endpoints, all under ``/api/components``:

- ``POST /api/components/search`` — returns candidate list from the local
  mock catalog. For each candidate we also call the Wikipedia REST
  endpoint to attach a real ``image_url``/``image_source``/
  ``image_attribution`` block (or null when Wikipedia has no thumbnail).
- ``POST /api/components`` — persists a single component to SQLite and,
  if the request carries an ``image_url``, downloads that image to
  ``data/images/<slug>.<ext>`` and writes the local path into
  ``image_path``. Image download failure NEVER fails the save
  (graceful degradation: ``image_path`` is null).
- ``GET /api/components`` — returns the list of saved components,
  with their stored ``image_path`` resolved to a public ``image_url``
  for the Inventory page.

The Stage 1 ``components`` table already has the columns we need:
``id, name, category, quantity, location, notes, image_path,
created_at, updated_at``. The new spec fields (``interfaces``,
``key_specs``, ``tags``, ``voltage``, ``datasheet_url``, ``source_url``,
``model_number``) are stored as a JSON blob inside ``notes`` — no
schema change, no migration. Stage 4+ can split them out into proper
columns.
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
from ..mock_data import search_components, slug_for_image
from ..wikipedia import fetch_wikipedia_image


router = APIRouter(prefix="/api/components", tags=["components"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SearchRequest(BaseModel):
    name: str = Field(..., description="Component name, e.g. 'ESP32'")
    model_number: str = Field(..., description="Model number, e.g. 'DevKit V1'")


class CreateComponentRequest(BaseModel):
    """Full payload sent by the frontend after the user picks a candidate.

    The fields are a superset of the Stage 1 ``components`` row. Extra
    spec fields are kept at the top level for convenience and stored in
    the ``notes`` column as a JSON blob. ``image_url`` is optional —
    if present, we download the image to disk and store the local
    path in ``image_path``.
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
    datasheet_url: Optional[str] = None
    source_url: Optional[str] = None
    image_url: Optional[str] = None


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
    """Map a SQLAlchemy Row to the public JSON shape, unflattening ``notes``."""
    raw: Dict[str, Any] = dict(row._mapping)
    notes_blob: Dict[str, Any] = {}
    raw_notes = raw.pop("notes", None)
    if raw_notes:
        try:
            notes_blob = json.loads(raw_notes)
        except (TypeError, ValueError):
            notes_blob = {}
    # Flatten notes keys into the public response.
    for key in (
        "model_number",
        "voltage",
        "interfaces",
        "key_specs",
        "tags",
        "datasheet_url",
        "source_url",
    ):
        if key in notes_blob and key not in raw:
            raw[key] = notes_blob[key]
    # Add a public image_url that the Inventory page can render. We resolve
    # the stored relative path to ``/api/images/<basename>`` which the
    # static file mount in main.py serves.
    image_path = raw.get("image_path")
    if image_path:
        raw["image_url"] = f"/api/images/{Path(image_path).name}"
    else:
        raw["image_url"] = None
    raw["image_source"] = "wikipedia" if image_path else None
    return raw


# ---------------------------------------------------------------------------
# Image download helper (used by POST /api/components)
# ---------------------------------------------------------------------------

# Magic byte signatures for the three image types Wikipedia can return.
# We don't accept SVG — Stage 2's SVG fallback is REMOVED.
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
    """Download a Wikipedia/Wikimedia image to ``data/images/<slug>.<ext>``.

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

    # Validate it's actually an image. Pick the extension from the
    # content-type header if it looks safe; otherwise infer from magic.
    ext = _ext_from_content_type(content_type) or _detect_image_format(data)
    if ext is None:
        print(
            f"[image-download] rejecting {image_url}: not a JPEG/PNG/WebP (content-type={content_type!r}, head={data[:8]!r})",
            file=sys.stderr,
        )
        return None

    # Cross-check: the magic bytes and the content-type should agree.
    magic_ext = _detect_image_format(data)
    if magic_ext is None:
        print(f"[image-download] magic-byte check failed for {image_url}", file=sys.stderr)
        return None
    # If content-type was wrong, fall back to the magic-byte version.
    if ext != magic_ext:
        ext = magic_ext

    images_dir = Path(get_images_dir())
    images_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{slug}.{ext}"
    abs_path = images_dir / filename
    abs_path.write_bytes(data)

    # Relative to project root: "data/images/<slug>.<ext>"
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
    """Return candidate components from the local mock catalog.

    Response shape matches the Stage 3 spec: ``{candidates, total}``.
    Each candidate has all the public spec fields the confirmation
    popup needs, plus ``image_url`` / ``image_source`` /
    ``image_attribution`` (or null when Wikipedia has no thumbnail for
    the candidate's ``wikipedia_title``). The lookup is cached in
    process, so duplicate searches are free.
    """
    name = (req.name or "").strip()
    model_number = (req.model_number or "").strip()
    if not name or not model_number:
        raise HTTPException(
            status_code=400,
            detail="Both 'name' and 'model_number' are required",
        )

    candidates = search_components(name, model_number)
    for c in candidates:
        title = c.get("wikipedia_title") or c.get("name") or ""
        wiki = fetch_wikipedia_image(title)
        # Attach image metadata. Keep all candidate fields as-is.
        c["image_url"] = wiki["url"]
        c["image_source"] = wiki["source"]
        c["image_attribution"] = wiki["attribution"]
    return {"candidates": candidates, "total": len(candidates)}


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

    # 2) Pack the new spec fields into the notes column as JSON.
    notes_blob = {
        "model_number": model_number,
        "voltage": req.voltage or "",
        "interfaces": list(req.interfaces or []),
        "key_specs": list(req.key_specs or []),
        "tags": list(req.tags or []),
        "datasheet_url": req.datasheet_url or "",
        "source_url": req.source_url or "",
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
                     created_at, updated_at)
                VALUES
                    (:name, :category, :quantity, :location, :notes, :image_path,
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
