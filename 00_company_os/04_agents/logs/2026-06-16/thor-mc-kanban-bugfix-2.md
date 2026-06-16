---
task_id: MC-KANBAN-BUGFIX-2
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-16T21:41:00Z
---

# Thor Coordination Log — MC-KANBAN-BUGFIX-2

## NOFI's complaint (verbatim)
*"same issue still persist ... i cannot stay at the bottom of the list.. it jumps back up and also there are so many tasks in running !!!!!"*

## What I did — investigation only, 0 implementation bytes

NOFI says the bugfix didn't work. I trusted the prior Argus PASS but the user is the ground truth. So I re-investigated myself.

### Findings

**1. Running column actually has 5 tasks (not many):**
- MC-KANBAN-BUGFIX-1 (current)
- DIY-009, DIY-010, DIY-011 (genuine diy work)
- MC-004-tasks-panel (legacy from June 10)

NOFI is likely seeing the old page in their browser cache. The fix is on disk but the browser is showing old HTML. **Fix: add `Cache-Control: no-store` headers.**

**2. Scroll jump is a real, separate bug:**
- The 5-second polling fires `loadKanban()` which does `board.innerHTML = ...` 
- This destroys and recreates the entire board DOM
- New DOM has no scroll position → resets to top
- My previous fix (pause polling when form open) didn't help because no form is open during normal scrolling
- **Fix: smart diff polling — only update cards that changed, leave unchanged cards in place (preserves scroll)**

### Why the prior verification missed this

The prior Argus run did **structural** checks:
- Did the lines exist in the source? Yes → PASS
- Were the flags declared? Yes → PASS

But it never **behaviorally** tested:
- Actually load the page in a browser
- Scroll the Done column to the bottom
- Wait 10 seconds
- Confirm whether scroll position stayed

Structural PASS ≠ behavioral PASS. This is a verification failure I (Thor) should have caught.

## What I did NOT do
- 0 bytes of implementation
- Did not edit serve.py
- Did not edit kanban.html
- Did not delegate yet (writing the task file first)

## Plan
- Forge implements Part 1 (cache headers) + Part 2 (smart diff) + behavioral test
- Argus does BEHAVIORAL verification, not just structural
