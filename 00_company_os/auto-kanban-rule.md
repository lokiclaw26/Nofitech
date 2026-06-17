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

## ARGUS MANDATORY BEFORE "SHIPPED" (locked 2026-06-18, addendum 1)

**No "shipped ✓" without an Argus log file. Period.**

NOFI caught Thor shipping MC-LIVE-DASHBOARD-1 and MC-LIVE-REFRESH-1 with self-test only
(curl + unittest), no Argus Playwright verification. Argus's last log was 9 hours stale.
That is a quality failure.

### The rule
Before claiming any task is "shipped ✓" in chat, Thor MUST have:

1. **A real Argus log file** in `00_company_os/04_agents/logs/YYYY-MM-DD/argus-*.md`
   - Filename MUST contain the commit hash or task id
   - Content MUST include: commit hash, list of what was verified, test pass/fail per item, any defects found
2. **The Argus log written AFTER the code commit**, not before. If the log is older
   than the commit, it's not verification — it's stale.
3. **The task file's `## Shipped` section** MUST reference the Argus log path
   (e.g. `Argus verified: 00_company_os/04_agents/logs/2026-06-18/argus-MC-LIVE-REFRESH-1-abc1234.md`)

### How to dispatch Argus
```python
# When you have code ready to ship, before committing "shipped":
from ondemand import dispatch  # or use delegate_task
res = dispatch(
    topic="MC-<id>: Argus QA on commit <hash> — verify <list of things to check>",
    agent="argus",
    source="thor-pre-ship",
    priority="urgent"
)
# WAIT for Argus to complete. Read its log file. THEN mark task done.
```

### When Argus finds defects
- If Argus finds bugs: do NOT mark shipped. Add a new task for the fixes, dispatch
  to Forge, loop until Argus passes.
- If Argus is unavailable (model down, busy, blocked): explicitly say so in chat
  with the reason. Do NOT silently self-verify.

### What counts as "Argus verified"
- A Playwright test that hits the live page or a side-port test server
- OR a thorough manual smoke test with screenshot evidence (file path in log)
- OR a complete re-read of the code against the spec with line-by-line pass/fail

### What does NOT count
- "I ran the unit tests" — that's Thor's job
- "The code looks right to me" — Thor self-attestation, not verification
- An Argus log older than the commit it's verifying

### Self-test alone is allowed ONLY for:
- Trivial fixes (< 10 lines, well-specified, like the auto-kanban rule itself)
- Emergency hotfixes when Argus is blocked AND NOFI has explicitly approved
  self-verify for that specific case (verbatim "NOFI approves self-verify")

## Out of scope (do NOT auto-touch)
- Tasks in `blocked` with a non-empty blocker reason
- Tasks already in `done` or `archived`
- Tasks whose `approval_status == "pending"` and require NOFI's verbatim gate phrase

## Why this exists
NOFI had to ask three times: "why is the kanban not responsive?" The answer was: nothing auto-starts work when a card appears. This rule fixes that permanently.

The Argus addendum exists because Thor was self-attesting "shipped" and Argus's
last activity went 9 hours stale. NOFI caught it. The dashboard fix was real,
but the *process* was broken. This rule fixes the process.

## Files
- `01_projects/mission-control/code/ondemand.py` — dispatch() function
- `01_projects/mission-control/code/serve.py` — PATCH /api/data/kanban/task/:id
- `00_company_os/auto-kanban-rule.md` — this file

## Violation consequences
- Future sessions that violate this rule are wasting NOFI's time.
- If you (Thor) skip the auto-loop, you must explicitly note it in your reply.
- If you ship without Argus, you must explicitly say "self-verified, no Argus"
  in the chat reply and explain why (Argus blocked, trivial fix, NOFI approved).
- If a real reason prevents dispatch (server down, token missing, etc.), say so.
