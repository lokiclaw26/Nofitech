---
task_id: MC-KANBAN-BUGFIX-3
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-17T10:51:00+04:00
---

# Thor Coordination Log — MC-KANBAN-BUGFIX-3

## NOFI's bug report (verbatim)
*"There is a bug in kanban page ... I see tasks running which are actually not currently running and they are on stand by waiting for next updates ... and also what the fuck is this with all the names going down as attached in the image"*

## What I did — investigation only, 0 implementation bytes

### Investigation findings

1. **Lane duplication** — read the smartRenderKanban function in kanban.html. Found the bug at line 645: the selector `colEl.querySelectorAll(":scope > .kanban-lane")` looks for lane divs as direct children of `colEl`, but they're actually direct children of `body` (the `.kanban-col-body` div). So the query returns nothing every poll, and the code creates new lane divs without removing the old ones. After 4 minutes, 16+ lanes pile up.

2. **"Tasks in running that are on stand by"** — confirmed by looking at the running column. 7 tasks, all with `status: in_progress` (or similar). These are tasks that were moved to in_progress by either:
   - Thor-direct task creation (the 5 stale MC-* tasks I cleaned up in MC-KANBAN-BUGFIX-1)
   - The auto-process cron (which moves triage → in_progress but doesn't actually do the work)
   - Genuinely in-progress DIY work (3 tasks)
   
   None of these are "actively being worked on right now" by anyone. They're "queued for processing" or "claimed but not started".

## Decisions made

For this task:
- **Fix the lane duplication** (1 line in kanban.html)
- **Rename "Running" to "In Progress"** to better match the actual semantic (cosmetic)
- **DO NOT add a "Queued" column** — that's a bigger change, needs NOFI approval

## Plan
- Forge: 1-line selector fix + column label change + behavioral test
- Argus: behavioral test with Playwright (no structural-only verification this time)

## Self-criticism

This is the 5th bug I've shipped that structural verification missed. The pattern:
1. I write code (or have a sub-agent write code)
2. Argus verifies structurally (lines exist, functions called)
3. User reports bug
4. I re-investigate and find the real issue

**Fix going forward:** every task acceptance criteria must include a behavioral test (Playwright + Chrome screenshot), not just structural grep.

## What I (Thor) did NOT do
- 0 bytes of implementation
- Did not edit kanban.html
- Did not edit kanban_parser.py

## Open follow-ups
- "Queued" column semantic — pending NOFI decision
- Behavioral test suite for kanban — write tests for the 5 known bugs
