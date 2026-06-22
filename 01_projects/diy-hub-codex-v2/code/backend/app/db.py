"""SQLAlchemy engine + session for DIY Hub V1.

The DB file lives at <project_root>/data/diy-hub.db (relative to this file:
../../data/diy-hub.db). The directory is created on import so the backend can
boot cleanly on a fresh machine.
"""
from __future__ import annotations

import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# backend/app/db.py -> backend/app -> backend -> code -> project_root -> data
_PROJECT_ROOT = Path(__file__).resolve().parents[3]
_DATA_DIR = _PROJECT_ROOT / "data"
_IMAGES_DIR = _DATA_DIR / "images"
_DB_PATH = _DATA_DIR / "diy-hub.db"

# Make sure the directories exist on import. start-dev.sh will create
# data/images/.gitkeep; we just need the dir to be writable.
_DATA_DIR.mkdir(parents=True, exist_ok=True)
_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

DATABASE_URL = os.environ.get(
    "DIY_HUB_DB_URL",
    f"sqlite:///{_DB_PATH}",
)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    future=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db_path() -> str:
    """Return absolute path of the SQLite file (for logging/evidence)."""
    return str(_DB_PATH)


def get_images_dir() -> str:
    return str(_IMAGES_DIR)
