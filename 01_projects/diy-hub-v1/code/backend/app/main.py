"""DIY Hub V1 — FastAPI backend.

Stage 1 scope: just health + pages endpoints + CORS. NO CRUD, NO business
logic. Stage 2+ will add the actual component/idea routes.
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Importing init_db applies the schema on boot (idempotent).
from . import init_db  # noqa: F401
from .db import get_db_path, get_images_dir
from .routes import components  # noqa: F401  # Stage 2: Add Component flow

PAGES = ["Dashboard", "Add Component", "Inventory", "Idea Lab", "Settings"]

app = FastAPI(
    title="DIY Hub V1 — API",
    version="0.2.0",
    description="Stage 2: navigable shell + Add Component flow.",
)

# Stage 2: Add Component flow (search, save, list).
app.include_router(components.router)

# CORS — Vite dev server is on http://127.0.0.1:5173 (and :5173 on the LAN).
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        # LAN IPs are dynamic; cover the common private ranges. Tighten in prod.
        "http://10.0.0.0/8",
        "http://192.168.0.0/16",
        "http://172.16.0.0/12",
    ],
    allow_origin_regex=r"http://(127\.0\.0\.1|localhost|10\.\d+\.\d+\.\d+|192\.168\.\d+\.\d+|172\.(1[6-9]|2\d|3[0-1])\.\d+\.\d+):5173",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health")
def health() -> dict:
    """Liveness probe used by the Dashboard page to prove end-to-end wiring."""
    return {"status": "ok"}


@app.get("/api/pages")
def pages() -> list[str]:
    """The 5 page names — exposed so the nav can be data-driven later."""
    return PAGES


@app.get("/api/info")
def info() -> dict:
    """Debug endpoint — surfaces DB + image paths so the developer can confirm
    Stage 1 wired the right files. Not used by the UI yet."""
    return {
        "status": "ok",
        "version": "0.1.0",
        "stage": "stage-1-in-progress",
        "db_path": get_db_path(),
        "images_dir": get_images_dir(),
        "pages": PAGES,
    }
