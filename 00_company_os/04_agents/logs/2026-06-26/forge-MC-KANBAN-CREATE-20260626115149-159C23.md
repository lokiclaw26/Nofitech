# forge log — MC-KANBAN-CREATE-20260626115149-159C23

**Task:** check the Memory graph if working properly as i dont see new memories being bright shining star
**Dispatched:** 2026-06-26T16:12:52+04:00 (Dubai) via Hermes cron (kanban-auto-execute)
**Agent:** forge

## Diagnosis

Inspected the memory graph pipeline end-to-end:

1. **API endpoint** `GET /api/memory-graph` was working and returning 1772 nodes / 3451 edges.
2. **`pickLatestNodeId`** (frontend, in memory-graph.html) was actually correctly selecting the newest node — verified that it picked `event:MC-KANBAN-CREATE-20260626115149-159C23` (this very task) as the bright-shining-star target.
3. **Footer "Last updated" was STALE: `2026-06-17T16:30:00+04:00`** — 8 days behind reality. This made the graph *look* frozen even though new nodes were being written.
4. **Live top-corner counter (lc-nodes / lc-edges)** was rendering live counts correctly, but the footer timestamp gave the strong impression nothing was happening.
5. **Root cause** (`memory_graph_global.py`):
   - `last_updated()` used `SELECT MAX(updated) FROM nodes`.
   - The kanban-bridge ingests nodes without setting `updated`, so `updated` was NULL on those rows.
   - `MAX(updated)` therefore returned 2026-06-17 (last time the file-importer upserted with `updated` set), even though 472 nodes from 2026-06-26 were present.
   - `pickLatestNodeId` was unaffected (it uses `created || updated`), but the user-visible "Last updated" indicator was 8 days frozen, and the green pulse never animated because the timestamp never moved.

## Fixes applied

1. **`memory_graph_global.py` :: `MemoryGraphGlobalStore.last_updated()`** — now falls back to `MAX(created)` when `MAX(updated)` is empty/stale, returning whichever ISO timestamp is newer. Both columns are ISO 8601 so lexicographic compare is correct.
2. **`memory_graph_global.py` :: `MemoryGraphGlobalStore.upsert_node()`** — when the caller does not pass `updated`, default it to the same value as `created` so that future `MAX(updated)` queries reflect real ingest activity without the bridge having to thread a separate timestamp.
3. **DB backfill** — ran a one-shot SQL backfill against `00_company_os/memory/memory-graph.sqlite3` setting `updated = created` for all 1749 rows where `updated` was NULL/empty. This makes the change immediately visible without waiting for new writes.
4. **Server restart** — killed stale `serve.py` (PID 498779, 2-day uptime) and restarted via `start-mc.sh` so the patched module is loaded. New PID 2385142, listening on :8767, served 1774 nodes / 3457 edges after initial incremental ingest.

## Verification

```
$ curl http://127.0.0.1:8767/api/memory-graph?scope=all
node_count: 1774
edge_count: 3457
last_updated: 2026-06-26T15:54:52+04:00      ← was 2026-06-17T16:30:00+04:00
nodes from 2026-06-26: 472
```

Browser visual confirmation (after fix):
- Footer "Last updated": `2026-06-26T15:54:52+04:00` ✓
- Top-right "Latest" banner: `⭐ event:MC-KANBAN-CREATE-20260626115149-159C23` ✓
- Live counter (top-right): `nodes 1774 · edges 3457` with green pulse ✓
- Bright shining star node visible in the 3D cluster (top-center) ✓
- Connection indicator: green / "polling 5s" ✓

## Files modified

- `/home/nofidofi/NofiTech-Ind/01_projects/mission-control/code/memory_graph_global.py` — `last_updated()` + `upsert_node()` patches
- `/home/nofidofi/NofiTech-Ind/00_company_os/memory/memory-graph.sqlite3` — in-place UPDATE of `updated` column (1749 rows)

## Notes

- The "shining star" rendering itself (3D node highlighting, camera fly-to on `shiningNodeId`) was already wired and working — the issue was strictly the stale `last_updated` timestamp making the graph *appear* frozen.
- No browser/UI changes needed; the data side was the entire fix.
- Server was running with 2-day uptime so a restart was required to pick up the module change; `start-mc.sh` made this idempotent and safe.

result: success
