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

-- DIY-012 (Stage 12): Component Identity Engine verified cache.
-- When the operator confirms a component, NOFI -> save, the row goes here.
-- Future searches consult this table BEFORE hitting the network. A hit
-- returns immediately with match_level='exact' and high confidence.
CREATE TABLE IF NOT EXISTS verified_components (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query_signature TEXT UNIQUE NOT NULL,
  canonical_name TEXT NOT NULL,
  manufacturer TEXT,
  model_number TEXT,
  component_type TEXT,
  description TEXT,
  voltage TEXT,
  interfaces TEXT,    -- JSON list
  specs TEXT,         -- JSON object
  datasheet_url TEXT,
  image_url TEXT,
  source_urls TEXT,   -- JSON list
  confidence REAL,
  verified_at TEXT NOT NULL,
  verified_by TEXT    -- 'thor' | 'forge' | 'argus' | 'nofi'
);

-- DIY-012: rejected components. When the operator clicks "Wrong result" on
-- a candidate, we record (query_signature, candidate_signature) here.
-- Future searches for the same query never return the same candidate.
CREATE TABLE IF NOT EXISTS rejected_components (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  query_signature TEXT NOT NULL,
  candidate_signature TEXT NOT NULL,
  reason TEXT,
  rejected_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_verified_signature
  ON verified_components(query_signature);
CREATE INDEX IF NOT EXISTS idx_rejected_lookup
  ON rejected_components(query_signature, candidate_signature);
