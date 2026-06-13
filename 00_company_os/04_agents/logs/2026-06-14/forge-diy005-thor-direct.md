# DIY-005 Forge Report (Thor-direct)

## Mode
Thor-direct (not dispatched as a subagent). The Forge subagent's 600s
ceiling has been hit on the last 2 stages (Stage 1, Stage 3), and the
spec for Stage 5 is fully verified end-to-end, so applying directly
with full audit trail is faster and safer.

## Files changed
- NEW: `code/backend/app/live_search.py` (29,348 bytes) — 5 live HTTP clients, parallel fetch, merge, confidence
- MODIFIED: `code/backend/app/mock_data.py` — OFFLINE FALLBACK header (catalog kept for explicit fallback only)
- MODIFIED: `code/backend/app/routes/components.py` — added /search (live), /detail, /mock-fallback; /api/components accepts 7 new fields
- MODIFIED: `code/backend/app/schema.sql` — 7 new columns (wikidata_id, commons_filename, source_url, manufacturer, release_year, confidence, datasheet_url)
- MODIFIED: `code/backend/app/init_db.py` — idempotent ALTER TABLE for new columns
- DELETED: `code/backend/app/parser.py` — replaced by live_search.py
- NEW: `code/frontend/src/components/ui/card.tsx` — Shadcn Card (for picker)
- MODIFIED: `code/frontend/src/pages/AddComponent.tsx` — full state machine rewrite, live lookup, mock fallback, confidence badge, ADD TO DATABASE button

## Self-test results (5/5 live sources reachable)
- Wikimedia Commons: HTTP 200 (image search returns real photos)
- Wikidata: HTTP 200 (Q31275763 = Wemos D1 Mini)
- Wikipedia REST: HTTP 200 (mostly 404 for niche boards, that's expected)
- PlatformIO: HTTP 200 (SPA, page-found-as-source pattern)
- GitHub: HTTP 200 (filter for query-word relevance)

## End-to-end test
- query "Wemos D1 Mini" -> 10 real candidates from 4 sources
- Pick Wemos D1 Mini Pro (Commons image) -> saved as ID 18
- Real 180,407 byte PNG downloaded to data/images/, magic bytes 89504e47
- All 7 Stage 5 fields persisted to DB

## Known limitations (parked for Stage 6+)
- Wikipedia returns 404 for niche boards (most don't have articles)
- PlatformIO is a SPA so we can't parse spec table from HTML
- GitHub returns noise for short queries; relevance filter helps
- Candidates from different sources are NOT pre-merged (the user picks)
- No image_alternates UI yet (multi-photo boards show only first)
