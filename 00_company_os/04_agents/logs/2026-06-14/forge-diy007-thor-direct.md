# DIY-007 Forge Report (Thor-direct)

## Mode
Thor-direct. Forge subagent's 600s ceiling has been hit on Stages 1, 3, 5.
Stage 7 is mostly frontend (Inventory rewrite + manual form modal). I
verified the spec end-to-end with curl before writing code.

## Files changed
- MODIFIED: code/backend/app/routes/components.py (+27 -4 LOC)
  - _row_to_dict() now parses the notes JSON blob and promotes source,
    voltage, interfaces, key_specs, tags, description to top level so
    the Inventory page can render them directly.
- MODIFIED: code/frontend/src/pages/Inventory.tsx (full rewrite, +300 LOC)
  - Loads /api/components on mount
  - 12-column responsive grid of InventoryCard components
  - Search bar (filter by name, model, tag, location, notes, description)
  - Category filter dropdown
  - Loading/Error/Empty states
  - Source badge + confidence badge overlay
- MODIFIED: code/frontend/src/pages/AddComponent.tsx (+270 LOC)
  - Added 13 useState hooks for manual form fields
  - Added resetManualForm() helper
  - Added handleManualSave() async handler
  - Empty-state dialog now has 3 buttons: Try offline mock fallback,
    Enter manually, Cancel (was 2)
  - New manual entry dialog with 12 fields per NOFI brief
- NEW: code/frontend/src/lib/categories.ts (1KB)
  - Canonical category list (matches _CATEGORY_HINTS in live_search.py)
  - categoryColor map for chip styling
- NEW: code/frontend/src/lib/sources.ts (2.2KB)
  - sourceBadge() function: maps source value -> human label + color
  - confidenceBadge() function: color-codes by 0.7/0.4 thresholds

## End-to-end tests (5/5 PASS)
1. GET /api/components returns 24 records (20 live + 4 manual/regression test)
2. Manual save: POST /api/components with source: "manual" -> 201, ID 21
3. Manual save with image_url: 180,407 byte PNG downloaded
4. Validation: empty name -> 400, empty model -> 400, qty < 1 -> 400
5. Regression: source: "live" still works, source: "mock_fallback" still works

## Hard rules (verified by grep)
- 0 new hits for googleapis, duckduckgo, octopart
- 0 PUT/DELETE endpoints added
- 0 Idea Lab references in new files
- Mission Control + RGV1 untouched
- 1 vendor rule kept: Stage 5/6 live search is FROZEN, no new sources added
- Manual save calls existing /api/components endpoint (no new backend endpoints)

## Out-of-scope confirmation
- NO edit UI (no PUT endpoint)
- NO delete UI (no DELETE endpoint)
- NO Idea Lab
- NO new live search source
- NO tweak to existing live search code
