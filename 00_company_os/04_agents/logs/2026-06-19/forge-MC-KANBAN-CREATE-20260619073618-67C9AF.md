# Forge — MC-KANBAN-CREATE-20260619073618-67C9AF

**Task:** Add an "Archive" button inside expanded DONE cards on the Kanban that hides the card, with a "show archived" toolbar toggle to reveal it again.

**Dispatched:** 2026-06-19T12:03:27+04:00 by kanban-auto-execute.

## Finding

The feature was already shipped as **MC-KANBAN-ARCHIVE-1** in a previous session. All four layers are in place:

| Layer | Where | What |
|---|---|---|
| Parser | `code/kanban_parser.py:54,72,603-662` | `archived` is an allowed status, has its own column, `build_board(include_archived=...)` filters by default |
| Service | `code/kanban_service.py:29,49-51` | `data_kanban(include_archived=False)` passes through |
| Server | `code/serve.py:1600,2148-2149` | `GET /api/data/kanban?include_archived=true` is the toggle; PATCH endpoint validates against the allowed-status tuple at line 2327 |
| UI | `code/kanban.html:301,477-523,665-686,1365-1369,1649-1678` | `.kanban-card.status-archived` style, `.card-archive-actions` block, "show archived" checkbox, 🗄 Archive button (or ↩ Unarchive when already archived), click handler that calls `moveCardTo` |

The expanded-card-body archive-actions row toggles `display:flex` when the card is expanded, matching the card-body behavior (line 1226-1229).

## End-to-end test (the three-layer verification rule)

**Setup:** live server at `http://127.0.0.1:8767`, used target `MC-AUTO-20260618103911-AA8A1F` (a real DONE card).

| Step | Expected | Got |
|---|---|---|
| 1. Default view of Done column before | 77 tasks, target at top | 77 tasks, target at top ✓ |
| 2. PATCH target → `archived` | `ok:true`, target moves to archived column, done count 77→76, archived 6→7 | ✓ exact match |
| 3. GET `?include_archived=true` | archived column has 7 entries, target present, `kanban_status: archived` on disk | ✓ |
| 4. PATCH target → `done` (round-trip) | `ok:true`, done count back to 77, archived back to 6 | ✓ |
| 5. Disk frontmatter | `kanban_status: done` | ✓ |

**Layer 1 (data):** disk + API agree, PATCH is idempotent.
**Layer 2 (delivery):** PATCH response includes the fresh board; UI polls every 5s.
**Layer 3 (visibility):** the 🗄 Archive button renders inside `.card-archive-actions` (flex on expand), the "show archived" checkbox controls the column appearance. The class `.kanban-card.status-archived` is set on the card element so the grey/dashed border style applies.

## What I did NOT change

Nothing. The feature already shipped; I only verified it end-to-end with the live server and a real PATCH round-trip. Re-implementing would have been wasted work and risked regressing a working feature.

## Acceptance

Task title: *"in Kanban, when a task completed and moved to DONE state, i want to have a button in the card when its expanded called ARCHIVE... so basically it hides it, and shows only if show archived is selected."*

- [x] Button appears in expanded DONE card → `.card-archive-actions` row, line 1365, toggles to flex when card opens
- [x] Button called "Archive" → "🗄 Archive" (line 1368)
- [x] Clicking it hides the card → PATCH `status: archived`, parser filters it out of default view
- [x] "Show archived" toolbar toggle → checkbox `#kanban-show-archived` (line 675), wires `_kanbanIncludeArchived` and re-fetches with `?include_archived=true`
- [x] Toggle reveals archived cards → archived column appears (7th column) and `.status-archived` style is applied

result: success
