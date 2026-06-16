---
task_id: MC-KANBAN-BUGFIX-1
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-16T21:11:00Z
---

# Thor Coordination Log — MC-KANBAN-BUGFIX-1

## NOFI's bug report (verbatim)
*"THERE ARE 2 ISSUES ... FIRST there are so many tasks in RUNNING and still there saying IN PROGRESS .. since all the process has stoped this is not true .... so why we have so many tasks in running section .. second issue is that when i scroll down to the bottom of the list ... the scroll jumps back up for some wierd reason .... also if i wanna add a new task the pop up disappears and seems like the kanban section is reseted .. why is that fix it"*

## What I (Thor) did — investigation only, 0 implementation bytes

1. **Investigated the 3 root causes** via curl + grep + read_file:

**Bug 1 (stale tasks):** 
- 10 tasks in running column
- 6 are MC-* tasks I (Thor) created with `status: in_progress` in frontmatter, but the work was completed and `task_completed` events were logged
- 4 are truly in progress: DIY-009, DIY-010, DIY-011 (genuine) + MC-004 (legacy from June 10)
- The kanban parser correctly maps `in_progress → running` so the board shows them as running
- The data is technically correct, but it's stale. NOFI is right to be confused.

**Bug 2 (scroll jump):**
- Existing per-column `dragover` handler (line 543) calls `e.preventDefault()` — but only inside column bodies
- No global handler on document, so when cursor is between columns or above/below the board, browser default `dragover` behavior takes over → triggers auto-scroll-to-center → on a long page this can scroll to top
- Fix: 2 lines on document: `addEventListener('dragover', e => e.preventDefault())` + same for `drop`

**Bug 3 (form disappears):**
- `loadKanban()` is called every 5s via `setInterval(loadKanban, 5000)` (line 785)
- It does `board.innerHTML = columns.map(...).join("")` (line 535) which REPLACES the entire board including any open inline-create forms
- User opens form, types 5s, polling fires, form is wiped out, board re-renders
- Fix: add `_kanbanCreateFormOpen` flag, set true when form opens, false when closed, skip re-render in polling when true

2. **Wrote the task file** at `01_projects/mission-control/tasks/MC-KANBAN-BUGFIX-1.md` with 3 parts + acceptance criteria
3. **Logged 4 events** to events.jsonl
4. **Updated state.json** for all 3 agents
5. **Will not fix any code myself** (SOUL rule)

## What I (Thor) did NOT do
- 0 bytes of implementation
- Did not edit any of the 6 task files
- Did not edit kanban.html
- Did not restart the server

## Open follow-ups
- MC-004-tasks-panel: should be cleaned up but NOFI didn't ask. Out of scope.
- MC-KANBAN-FREEZE-ACCEPTANCE: after this bugfix verified.
- Then: MC-022-ON-DEMAND-1 or NOFI's pick.

## Self-reflection
This is the first time I've had to flag my own mistakes so directly. Bug 1 is a consequence of Thor-direct task creation (the very behavior the SOUL rule was meant to prevent). If Forge/Argus created the tasks, they would have updated status to `complete` when they finished. The hero-mode pattern is fragile.

The fix for THIS task is small (6 file edits). The fix for the PATTERN is bigger: I need a post-task hook that, when a `task_completed` event is logged, automatically updates the source task file's `status:` field. That would prevent this from recurring. Out of scope for this task, but worth noting.
