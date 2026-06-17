# Thor Final Log: MC-KANBAN-4-WIRE-PROTOCOL

**Date:** 2026-06-17 ~13:15 Dubai (UTC+4)
**Task:** MC-KANBAN-4 — Wire the explicit-running-now protocol into Thor's actual delegation flow
**Thor role:** orchestrator only

## Root cause (the actual bug NOFI caught)

Thor had to remember TWO separate actions:
1. Set `kanban_status: running_now`
2. Call `delegate_task()`

That's fragile. Thor forgot. The `running_now` column sat empty the entire time MC-KANBAN-3A was being worked on (12:30-12:45 Dubai). The task jumped straight from `ready` → `done`.

## What was built

### Wrapper script
- **Path:** `/home/nofidofi/.hermes/scripts/kanban-delegate.sh`
- **Repo copy:** `01_projects/mission-control/scripts/kanban-delegate.sh`
- **Validates:** task file exists, assignee ∈ {thor, forge, argus}
- **Sets:** `kanban_status: running_now`, `assignee: <agent>`
- **Appends:** `work_started` event with actor=thor, assignee=agent, Dubai timestamp
- **Output:** clear block ending with "Now safe to call delegate_task for this task."
- **Exit codes:** 2=bad args, 3=bad assignee, 4=bad task, 5=HTTP fail
- **No silent half-state:** rejection leaves task file and events.jsonl untouched

### Skill (the rule doc)
- **Path:** `/home/nofirofi/.hermes/skills/thor-delegation-protocol/SKILL.md`
- **Repo copy:** `01_projects/mission-control/skills/thor-delegation-protocol-SKILL.md`
- **Rule:** Normal delegation = `kanban-delegate.sh <TASK> <AGENT> "<note>"` THEN `delegate_task(goal=..., context=...)`. Never two separate steps.

### Existing kanban-set-state.sh
- **Untouched.** Still works for one-off transitions (done, blocked, etc.).
- The wrapper is for the specific "about to delegate" case. The two have different semantics.

## Verification

### Forge: 5 spec tests + 4 bonus — all PASS
- Happy path with the actual MC-KANBAN-4 task: exit 0, success block printed
- Task file frontmatter updated: `kanban_status: running_now` (was `ready`), `assignee: forge`
- API shows task in `running_now` column
- Invalid assignee `bob`: REJECTED, exit 3, no state change
- Invalid task `MC-DOES-NOT-EXIST`: REJECTED, exit 4, no state change
- Bonus: event appended, no orphan events from rejected calls, `running_now` count stayed at 1, existing `kanban-set-state.sh` still works

### Argus: 14/14 checks PASS
- Wrapper exists, executable
- Validates task ID, assignee
- Sets `kanban_status: running_now`, assignee correctly
- Appends required event
- Output is clear
- Mission Control Kanban shows task in running_now
- PATCH still preserves lifecycle status (other fields untouched)
- Parser still reads YAML and legacy markdown-table
- Mission Control still loads
- No cron, no auto-demotion, no auto-promotion, no UI feature added
- **Live test:** created MC-ARGUS-TEST-1, ran wrapper, saw it appear in running_now, moved to done, removed test task. Evidence trail in events.jsonl.

### Minor deviation noted by Argus
The spec used Playwright selector `[data-column-id="running_now"]` but the actual DOM uses `id="kanban-col-running_now"`. Test-script bug in the spec, not a wrapper bug. Future behavioral tests should use the correct selector.

## Behavioral evidence
- Screenshot: `/tmp/mc-kanban-4-argus.png` (shows running_now=1, done=48)
- Forge log: `00_company_os/04_agents/logs/2026-06-17/forge-mc-kanban-4-wire-protocol.md`
- Argus log: `00_company_os/04_agents/logs/2026-06-17/argus-mc-kanban-4-wire-protocol.md`
- Wrapper ran live on MC-ARGUS-TEST-1 — proof of working end-to-end

## Git
- Commit `6ac12d1b` on local main (the wrapper + skill)
- 2 more local commits pending: this log + final task file update
- **Push to origin blocked** — no GitHub credentials (auto-sync cron will flush)

## FINAL RULE (locked)
**Normal delegation must use the wrapper.** Do not manually split Kanban state and sub-agent delegation.

Sequence:
```bash
bash /home/nofidofi/.hermes/scripts/kanban-delegate.sh <TASK_ID> <AGENT> "<note>"
delegate_task(goal="...", context="...", toolsets=[...])
# After sub-agent returns:
bash /home/nofidofi/.hermes/scripts/kanban-set-state.sh <TASK_ID> done "" ""
# Or if blocked:
bash /home/nofidofi/.hermes/scripts/kanban-set-state.sh <TASK_ID> blocked "" "<reason>"
```

## NEXT
The wrapper is live. Thor will use it for ALL future delegation. Ready to resume real project work using the wrapper.

## Done. Awaiting next directive.
