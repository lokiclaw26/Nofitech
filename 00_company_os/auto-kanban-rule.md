# THOR AUTO-KANBAN RULE (locked 2026-06-18)

**NOFI is DONE moving kanban cards by hand.**

## The Rule
On EVERY chat turn, BEFORE responding to NOFI's request, Thor MUST run the auto-kanban loop:

```python
# pseudo-code — actual implementation lives in ondemand.py + kanban PATCH API
board = get_kanban()  # GET /api/data/kanban
for task in board:
    if task.kanban_status == "ready":
        # Dispatch to its assigned agent and PATCH to running_now.
        # Default unassigned → forge. Default source → "thor-auto-loop".
        ondemand.dispatch(task.title, agent=task.assigned_to or "forge", source="thor-auto-loop")
    elif task.kanban_status == "running_now" and task.age_minutes > 30:
        # Long-running task: complete (with result) or block (with reason).
        # If no result has been written to the task file, block with reason "no result after 30min".
        patch_kanban(task.id, status="blocked", blocker="no result after 30min")
    elif task.kanban_status == "todo":
        patch_kanban(task.id, status="ready")
    elif task.kanban_status == "triage":
        # Sort: if topic is clear and small, move to ready; else block with reason.
        # Heuristic: small=less than 200 chars in title, no body → ready
        if len(task.title) < 200 and not task.body:
            patch_kanban(task.id, status="ready")
        else:
            patch_kanban(task.id, status="blocked", blocker="needs triage review")
    # NEVER touch items in blocked with a real blocker reason
    # (paid LLM key, out-of-scope project, Firefox test, etc.)
```

## Out of scope (do NOT auto-touch)
- Tasks in `blocked` with a non-empty blocker reason
- Tasks already in `done` or `archived`
- Tasks whose `approval_status == "pending"` and require NOFI's verbatim gate phrase

## Why this exists
NOFI had to ask three times: "why is the kanban not responsive?" The answer was: nothing auto-starts work when a card appears. This rule fixes that permanently.

## Files
- `01_projects/mission-control/code/ondemand.py` — dispatch() function
- `01_projects/mission-control/code/serve.py` — PATCH /api/data/kanban/task/:id
- `00_company_os/auto-kanban-rule.md` — this file

## Violation consequences
- Future sessions that violate this rule are wasting NOFI's time.
- If you (Thor) skip the auto-loop, you must explicitly note it in your reply.
- If a real reason prevents dispatch (server down, token missing, etc.), say so.
