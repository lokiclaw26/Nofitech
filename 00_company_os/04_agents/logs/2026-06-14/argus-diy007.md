# DIY-007 Argus Report (Stage 7: Inventory List + Manual Entry)

## Test setup
- Backend: PID 167613, port 8780, live
- Frontend: Vite HMR, port 5173, live
- DB: SQLite at /home/nofidofi/NofiTech-Ind/01_projects/diy-hub-v1/data/diy-hub.db (24 records: 20 live + 4 manual/regression)
- New lib files: lib/categories.ts, lib/sources.ts

## Memory entry 010 verification

| Artifact | Path | Timestamp | Before code? |
|---|---|---|---|
| Task file | tasks/DIY-007.md | 2026-06-14T21:15:00Z | YES |
| events.jsonl (3 events) | 00_company_os/events.jsonl | 2026-06-14T21:16:00Z | YES |
| state.json (in_progress) | 04_agents/state.json | 2026-06-14T21:16:00Z | YES |
| First code change | routes/components.py patch | ~21:17:00Z | (1-2 min gap) |

## 26-point verification checklist

### Task ordering (memory entry 010) — 4/4 PASS
- [x] 1. DIY-007.md exists with status: in_progress BEFORE first code change
- [x] 2. events.jsonl has task_created, task_assigned, work_started BEFORE first code change
- [x] 3. state.json shows diy-hub-v1: in_progress BEFORE first code change
- [x] 4. Timestamps prove the above

### Inventory list (Scope A) — 11/11 PASS
- [x] 5. GET /api/components returns 24 records
- [x] 6. Inventory page renders 24 cards on first load (grid data-testid present)
- [x] 7. Each card shows: name, model_number, manufacturer, qty, location, category, voltage, source badge, confidence badge
- [x] 8. Cards with no image show "No image" placeholder (SVG with M4 16l4.586... icon)
- [x] 9. Search bar filters by name (substring match on name+model+category+location+manufacturer+description+tags+interfaces)
- [x] 10. Search bar filters by tag (substring match includes c.tags.join())
- [x] 11. Category filter dropdown lists every distinct category (union with canonical CATEGORIES list)
- [x] 12. Empty state: "No components yet — add your first component." (data-testid="inventory-empty-db")
- [x] 13. Empty state: "No components match your filters" (data-testid="inventory-empty-filtered")
- [x] 14. Loading state: "Loading inventory..." while fetch in flight
- [x] 15. Error state: "Failed to load" + Retry button (data-testid="inventory-error")

### Manual entry (Scope B) — 7/7 PASS
- [x] 16. "Enter manually" button visible in empty-state dialog (data-testid="btn-enter-manually")
- [x] 17. Clicking opens the manual form modal (showManual state set)
- [x] 18. Manual form has all 12 fields (data-testid for each: manual-name, manual-model, manual-manufacturer, manual-category, manual-qty, manual-location, manual-voltage, manual-interfaces, manual-key-specs, manual-tags, manual-description, manual-image-url)
- [x] 19. Submitting valid form returns 201 from /api/components (verified: ID 21, ID 22)
- [x] 20. Saved record has source: "manual" in the response (verified: 'source': 'manual' for ID 21, 22, 23, 24)
- [x] 21. If image_url provided, image downloads to data/images/<slug>.<ext> (verified: 180,407 byte PNG, magic 89504e47)
- [x] 22. If no image_url, save succeeds with image_path = null (verified: 'image_path': None for ID 21)

### Hard rules — 4/4 PASS
- [x] 23. Zero new live search sources (grep googleapis/duckduckgo/octopart in NEW files: 0 hits; existing api.github.com hit is unchanged from Stage 5)
- [x] 24. Mission Control + RGV1 untouched (git diff: no changes outside diy-hub-v1)
- [x] 25. No edit/delete UI (grep PUT/DELETE in routes/components.py: 0 hits)
- [x] 26. No Idea Lab code (grep ideas/IdeaLab/idea_lab in changed files: 0 hits)

## Operator-facing summary
1. Open http://192.168.0.29:5173/inventory (hard-refresh)
2. See 24 cards in a responsive grid
3. Use search bar to filter by name, tag, location, etc.
4. Use category filter dropdown to narrow by category
5. Click "+ Add Component" to go to the AddComponent page
6. On AddComponent page, type a query that returns 0 results -> "No reliable live result found" dialog appears
7. Click "Enter manually" -> manual form modal opens
8. Fill in name, model, category, qty, and any other fields
9. Optionally paste an image URL
10. Click "Save to inventory" -> success animation, modal closes, record saved with source = "manual"
11. Go back to /inventory -> the new manual record appears with a blue "Manual" badge

## SUMMARY
**Argus: 26/26 PASS — STAGE 7 SHIPPED**

## Known operator-visible features (NOT bugs)
- Confidence badge on the inventory card: shows "30% confident" etc. based on the new field
- Source badge colors: live = green, adafruit = amber, mock_fallback = gray, manual = sky blue, pololu = blue
- Cards with no image show a "No image" placeholder with an image-broken icon
- The Inventory "+ Add Component" button uses react-router Link, navigates to /add
- The "Loading inventory..." text appears for ~1 second (the backend responds fast)
