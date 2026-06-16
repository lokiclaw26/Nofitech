---
task_id: MC-KANBAN-1
title: Kanban tab in Mission Control — 3-agent board (Thor/Forge/Argus)
agent: forge
officer: forge
level: info
status: done
created: 2026-06-16T19:16:00+00:00
---

# Forge — MC-KANBAN-1 — Kanban tab in Mission Control

**Status: DONE (ready for Argus verification)**

## Summary
Implemented the full Kanban tab in Mission Control per spec. 3 new endpoints
on serve.py, 1 new parser module, 1 new section (Section 10) in
mission-control.html. All 12 existing endpoints still return 200. No
regressions. No external kanban.db, no pip installs.

## What was built

### 1. `01_projects/mission-control/code/kanban_parser.py` (NEW, 404 LOC)
- `build_board(company_root, include_archived)` — scans
  `01_projects/*/tasks/*.md` and `00_company_os/*/tasks/*.md` (no company
  task dir exists yet, so only the project paths are scanned), parses
  frontmatter, returns the full 6-column dict + 3-agent summary.
- `update_task_status(task_id, new_status, company_root)` — finds the task
  file by `task_id` (or filename) and rewrites the frontmatter `status:`
  line in-place, preserving the rest of the frontmatter and the body.
- `create_task_file(task_id, title, assignee, priority, company_root)` —
  writes a new task file at `01_projects/mission-control/tasks/<id>.md`
  with the standard frontmatter.
- Status mapping (per spec): in_progress→running, complete/done→done,
  pending/approved→ready, blocked→blocked, archived→archived, triage→triage.
  Also handles legacy/edge cases: assigned→ready, open→todo, verification→running,
  failed→blocked.
- Pure stdlib (no pip deps).

### 2. `01_projects/mission-control/code/serve.py` (+168 LOC)
- `data_kanban(include_archived)` — wraps `kanban_parser.build_board` + adds
  `last_updated` timestamp and empty `errors` list.
- `patch_kanban_task(task_id, new_status)` — validates status against
  `kanban_parser.ALLOWED_STATUSES`, calls the parser, returns 200 with the
  full updated board, 400 on bad status, 404 on unknown task_id.
- `create_kanban_task(payload)` — generates `MC-KANBAN-CREATE-<ts>-<rand>` id,
  calls the parser, returns 201 with new card + updated board.
- New `do_PATCH` method on the Handler class.
- New routes:
    - GET `/api/data/kanban?include_archived=true` (optional query)
    - GET `/api/data/kanban/task/:id` → 405 (PATCH only)
    - PATCH `/api/data/kanban/task/:id` → 200/400/404
    - POST `/api/data/kanban/task` → 201/400
- `kanban_parser` is imported next to the existing imports (top of file).

### 3. `01_projects/mission-control/code/mission-control.html` (+588 LOC)
- **CSS** (~220 LOC) — all kanban styles added to the existing `<style>`
  block. Uses existing dark-theme vars (`--bg`, `--panel-2`, `--line`,
  `--text`, `--text2`, `--text3`, `--green`, `--amber`, `--red`, `--cyan`,
  `--blue`, `--yellow`) plus 3 NEW color vars:
  - `--thor-color:  #d29922` (amber)
  - `--forge-color: #58a6ff` (cyan)
  - `--argus-color: #f778ba` (pink)
  - `--font-mono: ui-monospace, ...`
- **Section 10 HTML** (~25 LOC) — `<section id="section-kanban">` with
  summary chips, toolbar (search + 2 toggles + refresh stamp), and a
  6-column board container. Inserted between Section 9 (GitHub) and the
  footer as required.
- **JS** (~340 LOC) — `loadKanban()`, `renderKanban()`, `renderKanbanColumn()`,
  `renderKanbanCard()`, `moveCardTo()`, `toggleCreateForm()`,
  `submitCreateTask()`, `startKanbanPolling()`, `stopKanbanPolling()`, plus
  the toolbar wire-up IIFE. Uses HTML5 native dragstart/dragover/drop.
  `setInterval(loadKanban, 5000)` polls every 5s. Click card toggles inline
  body expansion (no modal). + button shows inline form. Form POSTs to
  /api/data/kanban/task with {title, assignee, priority}. After a successful
  PATCH or POST, the board refreshes immediately (not waiting for the 5s
  poll) to give the user instant feedback.

## Verification (done by Forge, before handoff to Argus)

```
=== HTTP smoke test (all 12 endpoints) ===
200  /api/health
200  /api/version
200  /api/data/overview
200  /api/data/agents
200  /api/data/tasks
200  /api/data/projects
200  /api/data/logs
200  /api/data/events
200  /api/data/orders
200  /api/data/github
200  /api/data/provider
200  /api/data/kanban   ← new

=== /api/data/kanban shape ===
columns:  [triage, todo, ready, running, blocked, done]
agents:   [thor, forge, argus]
summary:  {total: 2, by_status: {triage:0, todo:0, ready:0, running:2, blocked:0, done:0, archived:0},
           by_assignee: {thor: 0, forge: 2, argus: 0}}
running.lanes: [thor(0), forge(2), argus(0)]
last_updated: 2026-06-16T19:15:04+00:00

=== PATCH round-trip ===
PATCH /api/data/kanban/task/MC-KANBAN-1 {"status":"ready"} → 200, ok:true, new_status:ready
PATCH ... {"status":"running"} → 200, ok:true, new_status:running  (restored)
PATCH ... {"status":"bogus"} → 400, "unknown status: 'bogus'"
PATCH /api/data/kanban/task/DOES-NOT-EXIST → 404, "task_id not found"

=== POST create + cleanup ===
POST /api/data/kanban/task {title:"Test from kanban UI", assignee:"argus", priority:"medium"}
  → 201, ok:true, task_id: MC-KANBAN-CREATE-20260616191504-3ED205, card.status:triage, card.assignee:argus
  Test file removed after verification (kept the tasks dir clean).

=== HTML markers in page ===
section-kanban: 1
renderKanban:   9
draggable="true" on cards: 1 (the card template)
kanban-lanes-by-profile toggle: 2
add-btn (+ button): 4
setInterval (polling): 2 (loadAll 30s + loadKanban 5s)
kanban/task/ in JS: 2 (PATCH + check)
method:"POST" in JS: 2
```

## Side effects / honest disclosures

- The PATCH endpoint writes the **kanban status** (e.g. `running`) to the
  file's frontmatter, not the **project status** (e.g. `in_progress`). This
  is per spec ("Update its frontmatter `status` field with the new value")
  but means an in_progress task moved on the board becomes `status: running`
  in the file. The parser still maps `running` back to the running column
  on the next read, so the round-trip is stable. The previous values
  (`in_progress`) and the new values (`running`) both render in the
  "Running" column. I left MC-KANBAN-1.md at its original `in_progress`
  status (manually restored after my PATCH test) to keep the task file's
  historical state intact.

- Inline create always lands in the **triage** column regardless of which
  + button was clicked. This is per spec: "Frontmatter: ... status: triage".
  The column the + button is in is irrelevant to the new task's status.

- The parser uses manual YAML frontmatter manipulation in the PATCH path
  (find `status:` line, replace the value, write back) instead of pyyaml/
  ruamel. This is because: (a) pyyaml would re-serialize the whole file and
  potentially lose comments / order / quoting, and (b) the parser is on the
  hot path for 5s polling. The stdlib manual approach preserves the file
  exactly except for the `status:` line.

- The MC-KANBAN-1.md task file was created by Thor (untracked in git);
  I did not commit it. That is Thor's responsibility per the work split.

## Files touched

| Path | Action | LOC |
|---|---|---|
| `01_projects/mission-control/code/kanban_parser.py` | NEW | +404 |
| `01_projects/mission-control/code/serve.py` | MODIFY | +168 |
| `01_projects/mission-control/code/mission-control.html` | MODIFY | +588 |
| `01_projects/mission-control/code/backups/pre-mc-kanban-1-2026-06-16/` | NEW (backup) | — |

**Total new code: 1160 LOC** (404 parser + 168 server + 588 UI).

## Git
- Commit: `462422b` on `main`
- Pushed: `69bcc3c..462422b main -> main` ✅

## Argus checklist (handoff)

Argus should verify:
1. `curl -s http://127.0.0.1:8767/api/data/kanban | python3 -m json.tool` —
   confirm 6 columns, 3 agents, by_status with 7 keys, by_assignee with 3 keys,
   running.lanes with 3 sub-groups.
2. `curl -sX PATCH http://127.0.0.1:8767/api/data/kanban/task/MC-GITHUB-PANEL-1
    -H "Content-Type: application/json" -d '{"status":"ready"}'`
   — confirm 200, then revert to original status.
3. `curl -s http://127.0.0.1:8767/ | grep -c "section-kanban"` ≥ 1
4. `curl -s http://127.0.0.1:8767/ | grep -c "renderKanban"` ≥ 3
5. Verify `draggable="true"` exists on cards.
6. Verify `kanban-lanes-by-profile` toggle + `kanban-show-archived` toggle exist.
7. Verify `setInterval(loadKanban, 5000)` is in the page.
8. Verify all 11 pre-existing endpoints still 200.
9. (Optional) Open the page in a browser, click the + button on Triage, fill
   the form, submit — verify a new task appears in Triage column.
10. Write argus log with PASS/FAIL counts.
