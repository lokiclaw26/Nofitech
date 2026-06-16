---
task_id: MC-KANBAN-BUGFIX-1
agent: thor
role: CEO / Orchestrator
project: mission-control
status: complete
created: 2026-06-16T21:30:00Z
---

# Thor Coordination Log — MC-KANBAN-BUGFIX-1 (FINAL)

## NOFI's bug report (verbatim)
*"THERE ARE 2 ISSUES ... FIRST there are so many tasks in RUNNING and still there saying IN PROGRESS .. since all the process has stoped this is not true .... so why we have so many tasks in running section .. second issue is that when i scroll down to the bottom of the list ... the scroll jumps back up for some wierd reason .... also if i wanna add a new task the pop up disappears and seems like the kanban section is reseted .. why is that fix it"*

(3 issues, not 2 — NOFI's casual numbering didn't include the create form issue but it was clearly described.)

## What I (Thor) did — investigation + orchestration only, 0 implementation bytes

### Investigation (root cause analysis)

**Bug 1 — Stale tasks in running column:**
- 10 tasks in running, 6 are stale (work was done, `task_completed` events fired, but the task file's `status:` field was never updated)
- The 6 stale tasks: MC-KANBAN-MOVE-1, MC-KANBAN-2, MC-KANBAN-1, MC-AGENT-LOG-FIX-1, MC-GITHUB-PANEL-1, MC-GITHUB-REPO-SETUP-1
- The 4 truly-in-progress: DIY-009, DIY-010, DIY-011 (genuine) + MC-004 (legacy from June 10, out of scope)
- **Root cause: my own pattern** — Thor-direct task creation marks files `status: in_progress` and never updates them when work is done. The events.jsonl has `task_completed` entries, but the source-of-truth YAML frontmatter is stale.
- **Long-term fix (out of scope for this task):** add a post-task hook that auto-updates the file status when `task_completed` fires. This would prevent recurrence. Note in open follow-ups.

**Bug 2 — Scroll jumps back up:**
- Existing per-column `dragover` handler at line 543 calls `e.preventDefault()` but only inside column bodies
- No global handler on document, so when cursor is in the gap between columns, browser default `dragover` triggers auto-scroll-to-center → scrolls to top on long pages
- **Fix:** 2 lines: `document.addEventListener('dragover', e => e.preventDefault())` + same for `drop`

**Bug 3 — Create form disappears:**
- `setInterval(loadKanban, 5000)` (line 785) fires every 5s
- `loadKanban()` does `board.innerHTML = ...` which REPLACES the entire board, including any open inline-create form
- After 5s of typing, polling fires, form is wiped out
- **Fix:** add `_kanbanCreateFormOpen` flag, set true when form opens, false when closed/submitted, skip re-render in polling when true

### Orchestration

1. **Wrote the task file** at `01_projects/mission-control/tasks/MC-KANBAN-BUGFIX-1.md` with 3 parts + acceptance criteria + explicit out-of-scope list
2. **Logged 4 events** to events.jsonl
3. **Updated state.json** for all 3 agents
4. **Delegated to Forge** (sub-agent, 37 calls, 278s, hit time/complexity but completed all parts)
5. **Forge discovered an extra fix:** MC-KANBAN-2-DUAL-FORMAT-PARSER had a separate stale `kanban_status: running` field (written by PATCH when work started, never moved to `done`). Forge fixed that too. Without this fix, the card would have stayed in the running column.
6. **Delegated to Argus** (sub-agent, 23 calls, 155s, PASS 24/24)

## Final state (live verified)

**Running column:** 5 tasks (was 10)
- MC-KANBAN-BUGFIX-1 (this task, correctly in_progress)
- DIY-009, DIY-010, DIY-011 (genuine, from diy-hub-v1)
- MC-004-tasks-panel (legacy from June 10, NOT touched per scope)

**Done column:** 36 tasks (was 30) — 6 new entries from the 6 stale tasks being correctly reclassified

**Total tasks:** 45 (was 44, +1 = MC-KANBAN-BUGFIX-1 itself)

**Bug 2 fix (scroll):** `document.addEventListener('dragover', ...)` and `addEventListener('drop', ...)` at lines 35-37 of the script (top of script block). Verified working.

**Bug 3 fix (form):** `_kanbanCreateFormOpen` flag with 6 references in kanban.html. Polling now pauses when form is open. Verified working.

**Endpoints:** 10/10 spec'd endpoints 200, /+/kanban both 200. No regressions.

**Git:**
- `ec41dd9` Forge: 6 task file updates + kanban.html edits
- `30339cb` Argus: verification + state.json update

## What I (Thor) did NOT do
- 0 bytes of implementation
- Did not edit any task file
- Did not edit kanban.html
- Did not restart the server

## SOUL rule honored
"THOR IS NOT ALLOWED TO PERFORM ANY TASK. ONLY ORCHESTRATE. NEVER PERFORM A TASK."

This task involved 2 sub-agent invocations:
1. Forge (37 calls, 278s) — complete
2. Argus (23 calls, 155s) — PASS 24/24

Total wall clock: ~7 minutes. Total Thor implementation bytes: 0.

## Open follow-ups (for the next tasks)

1. **MC-004-tasks-panel** — old task from June 10 with `status: in-progress` (note: hyphen, not underscore). NOFI didn't ask to clean it up. Recommend removing from the kanban or marking complete if it's actually done. Out of scope for this task.

2. **Post-task hook** — write a script that watches events.jsonl for `task_completed` events and auto-updates the source task file's `status:` field. This would prevent the Bug 1 pattern from recurring. Out of scope for this task but worth scheduling.

3. **MC-KANBAN-FREEZE-ACCEPTANCE** — after this bugfix verified. The kanban is in its final shape: page split done, dual-format parser done, PATCH data-loss fix done, 3 bugs fixed. Time to freeze.

## Self-reflection

This bug report came from NOFI after I had just shipped MC-KANBAN-MOVE-1. The bugs existed in the previous kanban code (MC-KANBAN-1) but NOFI didn't notice them until after the move (probably because the move changed the page layout, making the issues more obvious). 

I should have caught Bug 1 during MC-KANBAN-2 verification — Argus ran there, but his verification was about parser correctness, not whether the task files themselves were accurate. A more thorough Argus pass would have flagged the 6 stale task files. Lesson: when verifying, also check whether the DATA matches reality, not just whether the CODE matches the data.
