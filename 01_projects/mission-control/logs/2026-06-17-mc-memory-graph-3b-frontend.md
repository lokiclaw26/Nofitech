# MC-MEMORY-GRAPH-3B-FRONTEND — Implementation Log

**Date:** 2026-06-17
**Agent:** Forge
**Task:** Fix memory-graph.html — eliminate the 5s simulation reset, preserve selected node, add resize observer, responsive layout, clean inspector, filter UX.

## Files touched

- `code/memory-graph.html` — patched (257 → ~470 lines).

No backend files touched. No new vendor files. No new frameworks.

## Changes

### Fix 1 — Stop the 5s reset (PRIMARY)
- `applyFilters()` now computes `filteredNodes` and `filteredEdges`, then compares the **id set** of the new filtered nodes against `Graph.graphData().nodes` using `Set` equality.
- **If sets are equal: do NOT call `graphData()`** — this is the primary fix. The simulation keeps ticking from its current positions; no snap-back.
- If sets differ: build `prevById` from the existing nodes, carry `x/y/z/vx/vy/vz` forward for surviving nodes, then call `Graph.graphData({nodes: enriched, links: filteredEdges})`.
- `Graph.d3ReheatSimulation()` is invoked **only when new nodes were actually added** (not on identity-stable updates).

### Fix 2 — Preserve selected node across polls
- After computing `filteredNodes`, check if `selectedNode` is still present.
- If filtered out: clear `selectedNode = null`, reset `lastRenderedNodeJson`, render empty inspector.
- If still present: keep the reference. Inspector only re-renders when the **clean diff key** (label/id/kind/summary/status/importance/confidence/tags/dates/project/path/url/source) actually changes — `lastRenderedNodeJson` tracking prevents inspector DOM churn on every poll.

### Fix 3 — Canvas resize
- `setGraphSize()` helper reads `.graph-container` `clientWidth/clientHeight` and calls `Graph.width(...).height(...)`.
- Called once immediately after `ForceGraph3D()(...)` to fix initial size.
- `ResizeObserver` wired on `.graph-container`, debounced 200ms. Falls back to `window.resize` if `ResizeObserver` is unavailable.

### Fix 4 — Responsive layout
- Added `<button class="hamburger" id="hamburger">☰</button>` to the header (hidden on desktop, visible on mobile).
- Hamburger click toggles `.open` class on `.controls` and `.right-panel`.
- `@media (max-width: 900px)`:
  - `body` switches to column flex.
  - `.sidebar` hidden (top-bar only).
  - `.layout` column flex; controls order 2 (max-height 200px), graph order 1 (min-height 400px), right-panel order 3 (max-height 250px).
- `@media (max-width: 600px)`:
  - `.controls` and `.right-panel` hidden by default.
  - `.controls.open` and `.right-panel.open` shown when hamburger toggles them.
  - header h1 condensed.

### Fix 5 — Clean inspector
- Removed `<pre>JSON.stringify(node)</pre>`.
- Inspector now built entirely with `document.createElement` + `textContent`:
  - `<h2>` label (gold).
  - `insp-id` (mono gray) id line.
  - `insp-kind` badge with kind color from `KIND_HEX`.
  - `insp-summary` paragraph.
  - `insp-row` rows for status / importance / confidence.
  - `insp-tag` chips for tags.
  - `insp-section-title` + rows for created/updated (formatted `YYYY-MM-DD HH:MM:SS UTC`).
  - Optional project / path / url rows.
  - `insp-source` mono line.
- Explicitly never renders `__threeObj`, `x/y/z`, `vx/vy/vz`, `geometry`, `material`. The diff key omits them so even if a node object carries them, they never reach the DOM.

### Fix 6 — Filtering UX
- Footer now reads `Nodes: <strong id="node-count">0</strong> / <span class="total" id="node-total">0</span>` (and same for edges).
- `applyFilters()` updates filtered count and total count separately.
- Empty-state overlay (`#empty-state`) toggles to `display: flex` when `filteredNodes.length === 0`, hidden otherwise.
- Clears `selectedNode` if filtered out (covered by Fix 2).

## Verification

1. ✅ Structural check: `ResizeObserver`, `d3ReheatSimulation`, `@media` present; no `JSON.stringify` in inspector render path.
2. ✅ `python3 -m py_compile code/*.py` — OK.
3. ✅ `python3 -m unittest discover` — 65/65 tests pass.
4. ✅ File saved.
5. ✅ Server returns HTTP 200 at `http://localhost:8767/memory-graph` with new HTML (25,794 bytes).
6. ✅ Server NOT restarted — fresh fetch served from disk.

## Notes

- `KIND_HEX` added (parallel to `KIND_COLORS`) for CSS-friendly hex strings used by the inspector badge.
- `events` feed `li` items also switched from `innerHTML` to `createElement` for consistency (no user-data HTML injection).
- Server (PID 284019, port 8767) left running as instructed.

## Out of scope (not changed)

- Backend (`memory_graph_api.py`, `memory_graph_store.py`, `serve.py`) — untouched.
- Vendor libraries — untouched.
- `start-mc.sh` — untouched.

## Status

Implementation complete. Ready for Argus Playwright verification (open /memory-graph, wait 20s no jump; click node; resize to 390x844; etc.).