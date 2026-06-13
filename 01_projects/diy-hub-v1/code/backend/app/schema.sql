-- DIY Hub V1 — initial schema (Stage 1, empty tables, no business logic)
-- Stage 5: added 7 columns for live-source provenance + confidence.
-- Applied idempotently on backend boot via init_db.py.
-- (ALTER TABLE statements for the new columns are in init_db.py so the
-- table can grow without a destructive migration.)

CREATE TABLE IF NOT EXISTS components (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  category TEXT,
  quantity INTEGER NOT NULL DEFAULT 1,
  location TEXT,
  notes TEXT,
  image_path TEXT,
  -- Stage 5: live-source provenance. All nullable. When null, the field
  -- was unknown to every live source at the time of lookup.
  wikidata_id TEXT,
  commons_filename TEXT,
  source_url TEXT,
  manufacturer TEXT,
  release_year TEXT,
  confidence REAL,
  datasheet_url TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS ideas (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  title TEXT NOT NULL,
  description TEXT,
  status TEXT NOT NULL DEFAULT 'draft',
  components_needed TEXT,
  created_at TEXT NOT NULL,
  updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS tags (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL UNIQUE,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS component_tags (
  component_id INTEGER NOT NULL,
  tag_id INTEGER NOT NULL,
  PRIMARY KEY (component_id, tag_id),
  FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE,
  FOREIGN KEY (tag_id) REFERENCES tags(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS images (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  file_path TEXT NOT NULL,
  original_name TEXT,
  mime_type TEXT,
  size_bytes INTEGER,
  created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS settings (
  key TEXT PRIMARY KEY,
  value TEXT,
  updated_at TEXT NOT NULL
);
