"""Apply schema.sql on backend boot (idempotent — all CREATE TABLE IF NOT EXISTS)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .db import get_db_path, engine

_SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


def init_db() -> None:
    """Run the schema file against the SQLite DB. Safe to call repeatedly."""
    schema_sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    db_path = get_db_path()
    # Use a raw sqlite3 connection so multi-statement schema scripts work
    # cleanly (SQLAlchemy's execute() expects ORM/DDL objects, not multi-DDL SQL).
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_sql)
        conn.commit()
    # Touch the engine so SQLAlchemy opens/closes a connection once (no-op
    # beyond proving the engine works end-to-end).
    with engine.connect() as _:
        pass


# Apply on import — start-dev.sh runs uvicorn which imports app.main, which
# imports this module.
init_db()
