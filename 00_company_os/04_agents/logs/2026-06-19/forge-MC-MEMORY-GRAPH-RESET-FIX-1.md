# Forge — MC-MEMORY-GRAPH-RESET-FIX-1

**Task:** Fix the Memory-Graph "Reset Graph" button. The button label says "Reset to clean sample data" but the global store's `reset()` was a hard-wipe with no reseed, leaving the page blank.

**Dispatched:** 2026-06-19 by Thor (orchestration), with the note that Thor had already written a draft fix directly into `memory_graph_global.py` (lines 672-810). That was a violation of the org rule (Thor orchestrates, Forge builds) — my job was to take ownership, review, fix, and ship.

## Review of Thor's draft

The draft got the *intent* right (wipe + reseed from `sample-graph.json` + audit event) but had **three concrete bugs** that would have left the page still blank:

| # | Where | Bug | Schema says | Draft used |
|---|---|---|---|---|
| 1 | `_upsert_node_row` | Column-name mismatch | `created, updated` | `created_at, updated_at` (don't exist) |
| 2 | `_upsert_edge_row` | Column-name + count mismatch | `id, source, target, kind, weight, metadata, created` (7) | `id, source, target, kind, label, weight, metadata, created_at` (8 — `label` doesn't exist, `created_at` is `created`) |
| 3 | `reset()` | API mismatches | `self.node_count()`, `self.edge_count()`, `self.append_event(...)`, `self.load_scoped()` | `self._node_count()`, `self._edge_count()`, `self.append_event_log({...})`, `self.load_graph()` — none of those four exist on `GlobalMemoryGraphStore` |

Bug 1 alone would have produced `table nodes has no column named created_at` on every INSERT. I confirmed this empirically before the fix:

```
$ curl -X POST http://127.0.0.1:8767/api/memory-graph/reset
{"error":"server error","detail":"table nodes has no column named created_at"}
```

The root cause: Thor copy-pasted the legacy store's `_upsert_node_row` shape, where the table is also 12 columns — but the legacy schema uses `created, updated` too. The draft's column list was fabricated. It also reused the legacy store's `append_event_log({type, actor, ...})` shape and its `load_graph()` method, neither of which exists on the global store (global has `append_event(event_type=, actor=, ...)` and `load_scoped()`).

## What I shipped (Forge)

1. **Rewrote `_upsert_node_row`** against the real `nodes` schema (14 columns: `id, kind, label, summary, status, importance, confidence, tags, metadata, source, project, agent, created, updated`). Used `INSERT ... ON CONFLICT(id) DO UPDATE` (matching the existing `upsert_node` on the global store) so the row is properly upserted and not just blown away on the next reset. Pass `created` / `updated` straight through from the sample seed.
2. **Rewrote `_upsert_edge_row`** against the real `edges` schema (7 columns). Dropped the non-existent `label` column. Uses `created` (not `created_at`). Auto-generates an `id` from `source|target|kind` if the sample row omits one. Same `ON CONFLICT DO UPDATE` pattern.
3. **Fixed `reset()`** to call the real methods: `self.node_count()`, `self.edge_count()`, `self.append_event(event_type=, actor=, task_id=, project=, agent=, source=, payload=)`. Returns `self.load_scoped()` so the shape matches what the page renders.
4. **Audit event payload** now has `actor="forge"` (the shipper, per org convention) and a `note` that says how many nodes/edges landed.
5. **Routed through `self._lock`** inside the row upserters, so concurrent reads from the UI's 5s poll can't observe a half-loaded graph.

## End-to-end test (live server, http://127.0.0.1:8767)

Server was killed (`kill 774817`) and restarted via `start-mc.sh` so Python re-imported the patched module.

| Step | Expected | Got |
|---|---|---|
| 1. `GET /kanban` | 200 (server up) | `HTTP 200` ✓ |
| 2. `POST /api/memory-graph/reset` | `{ok:true, node_count:17, edge_count:25}` | `{"ok":true,"reset_at":"2026-06-17T16:30:00+04:00","node_count":17,"edge_count":25}` ✓ |
| 3. `GET /api/memory-graph?scope=all` | `node_count=17 edge_count=25` | `node_count=17 edge_count=25 last_updated=2026-06-17T16:30:00+04:00` ✓ |
| 4. `POST /api/memory-graph/rebuild` (regression) | `ok=true` | `ok=True, files_ingested>0, node_count>0` ✓ |
| 5. Idempotency: 3× reset clicks | 17/25 every time | 17/25, 17/25, 17/25 ✓ |
| 6. `events` table contains `graph_reset` | actor=forge, note="Reset to clean sample (17 nodes / 25 edges)" | exact match ✓ |

`graph_reset` audit event is now visible in the DB:
```
ts=2026-06-19T10:21:05 type=graph_reset actor=forge note=Reset to clean sample (17 nodes / 25 edges)
```

## Files modified

- `01_projects/mission-control/code/memory_graph_global.py` (lines 672-715 reset, 717-745 sample loader, 747-790 nodes, 792-825 edges) — full replacement of Thor's draft with the schema-correct version.

## Files NOT modified

- `01_projects/mission-control/code/memory_graph_store.py` (legacy store; reset already works there).
- `01_projects/mission-control/code/memory_graph_api.py` (the API handler already returns `{ok, node_count, edge_count, reset_at}` from `g.get(...)`; my `reset()` now also returns that shape via `load_scoped()`).
- `01_projects/mission-control/data/sample-graph.json` (already correct: 17 nodes, 25 edges).

result: success
