---
task_id: MC-KANBAN-BUGFIX-3
agent: forge
role: Builder / Engineer / DevOps
project: mission-control
status: complete
created: 2026-06-17T11:00:00+04:00
---

# Forge Build Log — MC-KANBAN-BUGFIX-3

## TL;DR
- PART 1 (lane selector fix): DONE — 1 line changed in kanban.html
- PART 2 (rename Running → In Progress): DONE — 1 label changed in kanban_parser.py
- PART 3 (backup + restart + test + commit + push): DONE
- BEHAVIORAL TEST: **PASS** ✅
  - Initial lane count: **4** (thor, forge, argus, unassigned)
  - After 30s (6 polling cycles): still **4** (no duplication)
  - Column header: **"In Progress"** (was "Running")
- Commit: `81917e5` — pushed to main

## What I did

### Part 1 — Lane selector fix (kanban.html line 645)
Found 2 occurrences of `:scope > .kanban-lane` in kanban.html:
- Line 645: `colEl.querySelectorAll(":scope > .kanban-lane")` — **BUG** (changed to `body.querySelectorAll`)
- Line 684: `body.querySelectorAll(":scope > .kanban-lane")` — already correct (left alone)

The DOM structure is: `<colEl> > <body.kanban-col-body> > <lane.kanban-lane>`. Lane divs
are direct children of `body`, not of `colEl`. The buggy selector at line 645 returned
nothing every poll, so new lane divs were created and never reused. After 4 minutes
(48 polls at 5s each), 192 lane divs piled up — only 16 visible due to max-height.

Diff:
```diff
-      for (const laneEl of colEl.querySelectorAll(":scope > .kanban-lane")) {
+      for (const laneEl of body.querySelectorAll(":scope > .kanban-lane")) {
         lanesByAssignee.set(laneEl.dataset.lane, laneEl);
       }
```

### Part 2 — Rename "Running" to "In Progress" (kanban_parser.py line 518)
Changed the `label` for the `running` column. Column `id` stays `running` (changing IDs
would break column mapping in the UI, JS, and API).

Diff:
```diff
-        "running": {"id": "running", "label": "Running"},
+        "running": {"id": "running", "label": "In Progress"},
```

API verification after server restart:
```json
[{"triage":"Triage"},{"todo":"Todo"},{"ready":"Ready"},
 {"running":"In Progress"},{"blocked":"Blocked"},{"done":"Done"}]
```

Checked for other "Running" column labels in non-backup files:
- `serve.py:1284` — code comment ("swimlanes inside Running"). Leave alone.
- `kanban.html:247, 419, 463` — CSS / JS comments referring to the column. Leave alone.
- `kanban.html:540, 575, 714, 917` — JS using `col.id === "running"` (the ID, not label). Leave alone.

No other column labels needed updating.

### Part 3 — Backup, restart, test, commit, push

**A. Backup:** `01_projects/mission-control/code/backups/pre-mc-kanban-bugfix-3-2026-06-17/`
- Recovered pre-patch content from `git show HEAD:...` (initial cp -r tried to recurse into
  the same dir, so I rebuilt from git's pre-commit version)
- Backup contents: kanban.html, kanban_parser.py, serve.py, mission-control.html, start-mc.sh

**B. Server restart:**
- Old PIDs: 207356, 207425 (killed with SIGTERM)
- New PID: 222517 (`python3 serve.py` running)
- Curl checks: `main: 200`, `kanban: 200`
- Log: `/tmp/mc-serve.log` clean

**C. BEHAVIORAL TEST (Playwright + headless Chrome):**
- Script: `/tmp/kanban-bugfix-3-test.js`
- Chrome: `/home/nofidofi/.agent-browser/browsers/chrome-149.0.7827.54/chrome`
- Playwright: `/tmp/pw/node_modules/playwright-core`
- Screenshots: `/tmp/kanban-bugfix-3-before.png`, `/tmp/kanban-bugfix-3-after.png`

```
After 3s:  lane count = 4  names: ["thor","forge","argus","unassigned"]
After 30s: lane count = 4  names: ["thor","forge","argus","unassigned"]
Column header: In Progress
RESULT_JSON:{"initial":4,"after30s":4,"header":"In Progress","passed":true}
OVERALL: PASS
```

The 30s wait covers 6 polling cycles (5s each). Lane count stays at exactly 4 — confirming
the fix works and the duplicate-lanes bug is gone.

**D. Commit + push:**
- Commit SHA: `81917e5`
- Message: "MC-KANBAN-BUGFIX-3: fix lane selector + rename Running to In Progress"
- Files committed:
  - `01_projects/mission-control/code/kanban.html` (1 line)
  - `01_projects/mission-control/code/kanban_parser.py` (1 label)
  - `01_projects/mission-control/tasks/MC-KANBAN-BUGFIX-3.md` (the task spec)
- Pushed: `66d9755..81917e5 main -> main` ✅
- **NOT committed (per hard rules):** state.json, events.jsonl, other agent logs, .env.github

## Files modified

| File | Change | Lines |
|------|--------|-------|
| `01_projects/mission-control/code/kanban.html` | `colEl` → `body` on line 645 | 1 |
| `01_projects/mission-control/code/kanban_parser.py` | `"Running"` → `"In Progress"` on line 518 | 1 |

## What I did NOT do (per hard rules)
- Did not touch any task file (other than the MC-KANBAN-BUGFIX-3.md that the spec told me to commit)
- Did not touch events.jsonl
- Did not touch state.json
- Did not touch other agent logs
- Did not touch .env.github
- Did not touch other projects
- Did not add new Kanban features
- Did not change column IDs (only the `running` label)
- Did not run the behavioral test before the fix (only after — Thor's analysis was unambiguous)

## Self-criticism / what I learned
- The backup step was awkward: `cp -r code/ code/backups/.../` fails because the destination
  is inside the source. Had to use git as the source of pre-patch content. Next time I'll
  use a tmpdir + rsync pattern from the start.
- The 5s polling in the kanban page means bugs accumulate fast: 4 lane divs/poll → 48 lanes
  in 1 minute → 192 lanes in 4 minutes. A single wrong selector had this much blast radius
  because there's no upper bound check.
- The behavioral test took ~33s to run (3s + 30s wait + browser launch). Worth it. Would have
  shipped the fix blind without it.

## Open follow-ups (for Argus / Thor)
- Argus: please re-verify with a fresh Playwright run and confirm. The test result is in
  this log + screenshots at `/tmp/kanban-bugfix-3-{before,after}.png`.
- The "Queued" column semantic (Option B/C in Thor's analysis) is still pending NOFI decision.
- Behavioral test suite for kanban — write tests for the other 4 known bugs so we catch regressions.

## REPORT BACK

```
DONE: yes
LANE_SELECTOR_FIXED: yes
COLUMN_LABEL_CHANGED: yes
BEHAVIORAL_TEST_RESULT: PASS
LANE_COUNT_INITIAL: 4
LANE_COUNT_AFTER_30S: 4
HEADER_TEXT: In Progress
COMMIT: 81917e5
PUSHED: yes
ARGUS_NEEDED: yes — for re-verification
BLOCKERS: none
```
