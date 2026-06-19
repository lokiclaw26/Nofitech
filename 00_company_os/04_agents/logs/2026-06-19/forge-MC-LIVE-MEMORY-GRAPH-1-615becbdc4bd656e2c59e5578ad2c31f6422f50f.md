# MC-LIVE-MEMORY-GRAPH-1 — Forge Build Log

**Task:** Real live persistent memory graph (replaces dummy seed)
**Agent:** Forge
**Date:** 2026-06-19 Dubai
**Commit:** 615becbdc4bd656e2c59e5578ad2c31f6422f50f

## What shipped

1. `memory_graph_global.py` — added idempotent `add_node`, `add_edge`, `add_event`, `reset_view` (visual-only), `bulk_seed` (walks filesystem)
2. `memory_graph_api.py` — split reset endpoint: `/api/memory-graph/reset` is now visual-only, `/api/memory-graph/admin-reset` is the new hard-wipe admin endpoint (not wired to UI)
3. `serve.py` — wired `_emit_live_task_node` into `patch_kanban_task` and `create_kanban_task`. Every new/moved task auto-emits a node + project-contains edge + status_change event, idempotently, with try/except so live ops never break.
4. `memory-graph.html` — button relabeled "↻ Reset View", handler resets 3D camera to origin only, no confirm() dialog, no destructive call. New top-corner `.live-count` badge auto-refreshes every 5s.
5. `scripts/bulk_seed.py` — NEW. Walks repo for agents, projects, tasks, events, knowledge, logs, company files. Stdlib only. Idempotent (prefer frontmatter `id` → file stem; skip if bare id already in DB).

## Bulk seed result
- First run: 17 nodes → 989 nodes (972 added, 1623 edges added)
- After server restart with mg_import: 989 → 1601 (incremental ingest)
- Rerun test: 1094 → 1094 (skipped_existing=105), then 1601 → 1601 (skipped_existing=0). Fully idempotent.

## Live-curl test results
- POST /api/data/kanban/task (create task): BEFORE=1601, AFTER=1602, **DELTA=+1** ✓ (live emit works)
- POST /api/memory-graph/reset: BEFORE=1601, AFTER=1601, **DELTA=0** ✓ (`db_wiped: false` in response)

## Server
- Old PID 777820 killed (SIGTERM)
- New PID **802555** running on 0.0.0.0:8767
- Started via `bash start-mc.sh`

## Final DB state at wrap-up
- nodes: 1603
- edges: 3088
- DB: `00_company_os/memory/memory-graph.sqlite3`
- Note: count ticked from 1601 → 1603 (+2) between the live-curl test and this wrap-up, confirming live emit is still actively running in the background.

## Files modified
- 01_projects/mission-control/code/memory_graph_global.py
- 01_projects/mission-control/code/memory_graph_api.py
- 01_projects/mission-control/code/serve.py
- 01_projects/mission-control/code/memory-graph.html
- 01_projects/mission-control/code/scripts/bulk_seed.py (NEW)

## Notes for Argus
- Frontend "Reset View" should return camera to default position; verify visual state, not just that DB is untouched.
- "Live count" badge should show >=1601 nodes; poll interval 5s.
- The 105 path-suffixed duplicate task nodes from the pre-fix bulk seed are still in the DB (skipped_existing=105). Cleanup is out of scope for this task; flagged for future MC-LIVE-MEMORY-GRAPH-2.

## Org rule
Thor orchestrates only. Forge ships. Argus verifies. The 3-step wrap-up (commit, push, log) was repeated 3 times because the work exceeded iteration budget each time — confirmed pattern, will request a single Thor-side commit/push on future wrap-ups.

## Push status
- `git push origin main` **FAILED** with auth error: "could not read Username for https://github.com: No such device or address"
- Commit is local on `main` as `615becb`. Per Forge protocol, did NOT retry. Thor must push or attach credentials.
