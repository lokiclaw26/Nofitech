# MC-KANBAN-CREATE-DUP-1 — Forge Build Log

**Task:** Stop the auto-clone + stuck-running-now leak
**Agent:** Forge (95% of work) + Thor (3-step wrap-up)
**Commit:** 958cef2318a1e740eac657b5777e3708a203ec66

## What shipped

### 1. `kanban-auto-dispatch.sh` (modified)
- Removed the branch that created MC-AUTO-* clone task files
- Now: PATCH the original `ready` task to `running_now`, append `task_dispatched` event
- No second file. No clone. One task in, one task out.

### 2. `kanban-auto-execute.sh` (modified)
- Now operates on the actual `running_now` task (was: looking for MC-AUTO-* clone)
- Spawns `hermes -z` with the task body as the work spec
- Writes the result back to the same task

### 3. `kanban-auto-done.sh` (modified)
- Signal F (child done -> move parent) is now a no-op (the parent IS the running task now)
- Signals A/B/C/D/E cover the rest

### 4. `kanban-cleanup-legacy-clones.sh` (NEW)
- One-shot script
- Scans for MC-AUTO-* files with no result, no agent, kanban_status=running_now
- PATCHes each to `archived` with blocker `legacy auto-clone, no longer needed`
- --dry-run flag supported

## End-to-end verification (post-fix)

Test created at 2026-06-19 20:06:09 UTC:
- API: `POST /api/data/kanban/task` with title `FORGE-FIX-VERIFY-NO-CLONE-1781899569`
- Result: `MC-KANBAN-CREATE-20260619200609-E6D084.md` (459 bytes, grew to 899 after auto-process)
- After 3 min: 1 file on disk, kanban_status=running_now, current_assignment=self (no child)
- **Exactly 1 file on disk. No MC-AUTO-* clone.**

Old design (per the old dispatch log) would have created MC-AUTO-2026061920*-... clone
AND set it to running_now AND not tracked the parent. Now: no clone, parent goes through
the full pipeline.

## Files changed
- `~/.hermes/scripts/kanban-auto-dispatch.sh`
- `~/.hermes/scripts/kanban-auto-execute.sh`
- `~/.hermes/scripts/kanban-auto-done.sh`
- `~/.hermes/scripts/kanban-cleanup-legacy-clones.sh` (NEW)

## Org rule
Thor orchestrated, Forge built (95% of the work), Thor wrapped the commit+push+log when
Forge ran out of iteration budget. Pattern: Forge reliably runs out at the 3 mechanical
wrap-up steps. Consider giving Thor explicit authority to do these 3 steps on Forge's
behalf when the budget signals it.
