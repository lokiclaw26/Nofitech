"""Components router — Stage 2 (Add Component flow).

Three endpoints, all under ``/api/components``:

- ``POST /api/components/search`` — returns candidate list from the local
  mock catalog. No network calls.
- ``POST /api/components`` — persists a single component to SQLite and
  writes a generated SVG to ``data/images/<slug>.svg``. Returns 201.
- ``GET /api/components`` — returns the list of saved components.

The Stage 1 ``components`` table already has the columns we need:
``id, name, category, quantity, location, notes, image_path,
created_at, updated_at``. The new spec fields (``interfaces``,
``key_specs``, ``tags``, ``voltage``, ``datasheet_url``, ``source_url``,
``model_number``) are stored as a JSON blob inside ``notes`` — no
schema change, no migration. Stage 3 can split them out into proper
columns.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from ..db import SessionLocal, engine, get_images_dir
from ..mock_data import generate_mock_svg, search_components, slug_for_image
from sqlalchemy import text


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
    the ``notes`` column as a JSON blob.
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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


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
    return raw


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/search")
def search(req: SearchRequest) -> Dict[str, Any]:
    """Return candidate components from the local mock catalog.

    Response shape matches the Stage 2 spec: ``{candidates, total}``.
    Each candidate has all the public spec fields the confirmation
    popup needs. ``mock_image_data`` is included so the frontend can
    preview the eventual image, but the authoritative SVG is generated
    server-side on save.
    """
    name = (req.name or "").strip()
    model_number = (req.model_number or "").strip()
    if not name or not model_number:
        raise HTTPException(
            status_code=400,
            detail="Both 'name' and 'model_number' are required",
        )

    candidates = search_components(name, model_number)
    # Generate the SVG preview string up front so the frontend doesn't
    # have to. This is a pure function — no filesystem writes here.
    for c in candidates:
        c["mock_image_data"] = generate_mock_svg(
            c.get("name", ""),
            c.get("model_number", ""),
            c.get("category", "Other"),
        )
    return {"candidates": candidates, "total": len(candidates)}


@router.post("", status_code=201)
def create_component(req: CreateComponentRequest) -> Dict[str, Any]:
    """Persist a component to SQLite + write its SVG to data/images/.

    Returns 201 with the saved row. Raises 400 on validation errors.
    """
    name = (req.name or "").strip()
    model_number = (req.model_number or "").strip()
    if not name:
        raise HTTPException(status_code=400, detail="'name' is required")
    if not model_number:
        raise HTTPException(status_code=400, detail="'model_number' is required")
    if req.quantity is None or req.quantity < 1:
        raise HTTPException(status_code=400, detail="'quantity' must be >= 1")

    # 1) Generate the SVG and write it to disk.
    svg = generate_mock_svg(name, model_number, req.category or "Other")
    slug = slug_for_image(name, model_number)
    images_dir = Path(get_images_dir())
    images_dir.mkdir(parents=True, exist_ok=True)
    image_filename = f"{slug}.svg"
    image_abs_path = images_dir / image_filename
    image_abs_path.write_text(svg, encoding="utf-8")
    # Store the *relative* path so the project is portable.
    # components.py -> routes -> app -> backend -> code -> project_root
    project_root = Path(__file__).resolve().parents[4]
    image_rel_path = str(image_abs_path.relative_to(project_root))

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

    # 3) Insert into SQLite.
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
