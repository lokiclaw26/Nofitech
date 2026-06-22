"""DIY Hub V1 — Stage 12: identity engine routes.

Two new endpoints under ``/api/components``:

  - ``POST /api/components/verify``  : record a verified component
                                       (writes the ``verified_components``
                                       row keyed by query_signature).
  - ``POST /api/components/reject``  : record a rejection
                                       (writes a ``rejected_components``
                                       row keyed by query_signature +
                                       candidate_signature).

Frontend flow:
  1. Operator sees search results with match_level + confidence badges.
  2. If single result, confidence >= 0.85 -> auto-confirm (still calls
     /verify to seed the cache).
  3. If < 0.85, UI shows "Needs review" pill. Operator can edit fields
     and click "Save & verify" to call /verify and add to inventory.
  4. Operator can click "Wrong result" to call /reject.
"""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from .. import identity_cache


router = APIRouter(prefix="/api/components", tags=["identity"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class VerifyRequest(BaseModel):
    """Request body for POST /api/components/verify.

    The frontend sends the candidate the operator confirmed, along with any
    edits they made. We persist it as a verified_components row.
    """

    query: str = Field(..., description="The original free-text query.")
    canonical_name: str = Field(..., description="Edited/confirmed name.")
    manufacturer: Optional[str] = None
    model_number: Optional[str] = None
    component_type: Optional[str] = None
    description: Optional[str] = None
    voltage: Optional[str] = None
    interfaces: List[str] = Field(default_factory=list)
    specs: Dict[str, Any] = Field(default_factory=dict)
    datasheet_url: Optional[str] = None
    image_url: Optional[str] = None
    source_urls: List[str] = Field(default_factory=list)
    confidence: Optional[float] = None
    verified_by: str = Field(default="nofi", description="'thor' | 'forge' | 'argus' | 'nofi'")


class RejectRequest(BaseModel):
    """Request body for POST /api/components/reject."""

    query: str = Field(..., description="The original free-text query.")
    candidate: Dict[str, Any] = Field(..., description="The candidate dict the operator rejected.")
    reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/verify")
def verify_component(req: VerifyRequest) -> Dict[str, Any]:
    """Record a verified component in the identity cache.

    On hit, the next time someone searches for the same query, the result
    comes back immediately with match_level='exact' and confidence=0.95.
    """
    if not (req.query or "").strip():
        raise HTTPException(status_code=400, detail="'query' is required")
    if not (req.canonical_name or "").strip():
        raise HTTPException(status_code=400, detail="'canonical_name' is required")
    row = identity_cache.put_verified(
        query=req.query,
        canonical_name=req.canonical_name,
        manufacturer=req.manufacturer,
        model_number=req.model_number,
        component_type=req.component_type,
        description=req.description,
        voltage=req.voltage,
        interfaces=req.interfaces,
        specs=req.specs,
        datasheet_url=req.datasheet_url,
        image_url=req.image_url,
        source_urls=req.source_urls,
        confidence=req.confidence,
        verified_by=req.verified_by,
    )
    return {
        "ok": True,
        "query_signature": identity_cache.query_signature(req.query),
        "verified_components": row,
    }


@router.post("/reject")
def reject_component(req: RejectRequest) -> Dict[str, Any]:
    """Record a rejection in the identity cache.

    The next time someone searches for the same query, this candidate will
    not be returned (it will be filtered out before ranking).
    """
    if not (req.query or "").strip():
        raise HTTPException(status_code=400, detail="'query' is required")
    if not req.candidate:
        raise HTTPException(status_code=400, detail="'candidate' is required")
    identity_cache.put_rejected(req.query, req.candidate, reason=req.reason or "")
    return {
        "ok": True,
        "query_signature": identity_cache.query_signature(req.query),
        "candidate_signature": identity_cache.candidate_signature(req.candidate),
    }
