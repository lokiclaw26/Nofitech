"""Apply schema.sql on backend boot (idempotent — all CREATE TABLE IF NOT EXISTS)."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from .db import get_db_path, engine

_SCHEMA_FILE = Path(__file__).resolve().parent / "schema.sql"


# Stage 5: ALTER TABLE statements for the 7 new live-source provenance
# columns. SQLite has no "ADD COLUMN IF NOT EXISTS", so we introspect
# first and only add what's missing. Safe to run on every boot.
_STAGE5_ALTERS: tuple[tuple[str, str], ...] = (
    ("wikidata_id", "TEXT"),
    ("commons_filename", "TEXT"),
    ("source_url", "TEXT"),
    ("manufacturer", "TEXT"),
    ("release_year", "TEXT"),
    ("confidence", "REAL"),
    ("datasheet_url", "TEXT"),
)


def _add_missing_columns(conn: sqlite3.Connection) -> None:
    """Add Stage 5 columns to ``components`` if they aren't there yet."""
    existing = {
        row["name"]
        for row in conn.execute("PRAGMA table_info(components)").fetchall()
    }
    for col_name, col_type in _STAGE5_ALTERS:
        if col_name not in existing:
            conn.execute(
                f'ALTER TABLE components ADD COLUMN "{col_name}" {col_type}'
            )


def init_db() -> None:
    """Run the schema file against the SQLite DB. Safe to call repeatedly."""
    schema_sql = _SCHEMA_FILE.read_text(encoding="utf-8")
    db_path = get_db_path()
    # Use a raw sqlite3 connection so multi-statement schema scripts work
    # cleanly (SQLAlchemy's execute() expects ORM/DDL objects, not multi-DDL SQL).
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.executescript(schema_sql)
        _add_missing_columns(conn)
        conn.commit()
    # Touch the engine so SQLAlchemy opens/closes a connection once (no-op
    # beyond proving the engine works end-to-end).
    with engine.connect() as _:
        pass


# Apply on import — start-dev.sh runs uvicorn which imports app.main, which
# imports this module.
init_db()
