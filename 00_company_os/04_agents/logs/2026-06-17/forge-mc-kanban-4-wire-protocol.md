# Forge log — MC-KANBAN-4-WIRE-PROTOCOL

**Date:** 2026-06-17 Dubai
**Agent:** Forge (builder)
**Task:** MC-KANBAN-4-WIRE-PROTOCOL
**Spec:** `01_projects/mission-control/tasks/MC-KANBAN-4-WIRE-PROTOCOL.md`

## Summary

Built the `kanban-delegate.sh` wrapper and the `thor-delegation-protocol` skill
to fix the bug NOFI reported: the RUNNING NOW column never showed what Thor
was actively working on, because Thor had to remember TWO separate actions
(set `running_now` + call `delegate_task`) and was forgetting the first.

The wrapper fuses the two into one atomic op. Thor cannot legitimately call
`delegate_task` without first invoking the wrapper and getting the
"Now safe to call delegate_task" line.

## Files created

| Path | Purpose |
|---|---|
| `/home/nofidofi/.hermes/scripts/kanban-delegate.sh` | Atomic delegation wrapper (executable, 4514 bytes) |
| `/home/nofidofi/.hermes/skills/thor-delegation-protocol/SKILL.md` | Skill documenting the new protocol |
| `/home/nofidofi/NofiTech-Ind/00_company_os/04_agents/logs/2026-06-17/forge-mc-kanban-4-wire-protocol.md` | This log |

## Files NOT touched (out of scope)

- `/home/nofidofi/.hermes/scripts/kanban-set-state.sh` — semantics preserved; still used for terminal states (done, blocked)
- `01_projects/mission-control/tasks/MC-KANBAN-4-WIRE-PROTOCOL.md` frontmatter — only the `kanban_status` and `assignee` lines were updated by the wrapper itself, not edited by hand
- No cron, no auto-promotion/demotion, no new UI

## Wrapper design

Inputs: `<TASK_ID> <assignee> [note]`
- `assignee` must be one of `thor|forge|argus`
- `TASK_ID` must resolve to a file under `01_projects/*/tasks/<TASK_ID>.md`

Atomic sequence:
1. Validate inputs (assignee allow-list, task file existence). Exit 2/3/4 on failure. No state change on rejection.
2. PATCH `http://192.168.0.29:8767/api/data/kanban/task/<TASK_ID>` with `{status: running_now, assignee: <agent>}`. Exit 5 on HTTP failure.
3. Update task file frontmatter (`kanban_status`, `assignee`). Best-effort; the server is the source of truth.
4. Append `work_started` event to `00_company_os/04_agents/events.jsonl` (Dubai TZ ISO timestamp, schema: `event_type/task_id/actor/assignee/timestamp/note`).
5. Print a clear "Now safe to call delegate_task" block.

## Verification (5 spec tests + 4 bonus)

### Test 1 — happy path (assignee=forge)
```
$ bash /home/nofidofi/.hermes/scripts/kanban-delegate.sh MC-KANBAN-4-WIRE-PROTOCOL forge "testing wrapper for MC-KANBAN-4"
kanban-delegate: MC-KANBAN-4-WIRE-PROTOCOL
  kanban_status: running_now (was ready)
  assignee: forge (was forge)
  event: work_started appended to 04_agents/events.jsonl
  task file: /home/nofidofi/NofiTech-Ind/01_projects/mission-control/tasks/MC-KANBAN-4-WIRE-PROTOCOL.md

Now safe to call delegate_task for this task.
$ echo $?
0
```
**PASS**

### Test 2 — task file frontmatter updated
```
$ head -15 .../MC-KANBAN-4-WIRE-PROTOCOL.md
---
task_id: MC-KANBAN-4-WIRE-PROTOCOL
title: Wire the explicit-running-now protocol into Thor's actual delegation flow
type: bugfix
priority: high
status: in_progress
kanban_status: running_now      <-- was: ready
assignee: forge                  <-- unchanged
created: 2026-06-17T12:50:00+04:00
...
```
**PASS**

### Test 3 — kanban API shows the task in running_now
```
$ curl -s http://192.168.0.29:8767/api/data/kanban | python3 -c "..."
running_now count: 1
 - MC-KANBAN-4-WIRE-PROTOCOL | running_now | in_progress
```
**PASS**

### Test 4 — invalid assignee rejected
```
$ bash .../kanban-delegate.sh MC-FAKE-TASK bob "test"
kanban-delegate: REJECTED assignee='bob'
  allowed: thor forge argus
  no state change performed
$ echo $?
3
```
**PASS** — no state change, non-zero exit

### Test 5 — invalid task rejected
```
$ bash .../kanban-delegate.sh MC-DOES-NOT-EXIST forge "test"
kanban-delegate: REJECTED task_id='MC-DOES-NOT-EXIST' (no task file found under 01_projects/*/tasks/)
$ echo $?
4
```
**PASS** — no state change, non-zero exit

### Bonus checks

- **Event appended:** tail of `04_agents/events.jsonl` contains the new `work_started` record with Dubai timestamp `2026-06-17T15:11:28.715963+04:00`.
- **No orphan events from rejected calls:** `grep -c "MC-FAKE-TASK\|MC-DOES-NOT-EXIST" events.jsonl` returns `0`. The wrapper did not write an event for any rejected call.
- **`running_now` count is exactly 1** (only MC-KANBAN-4) after all 5 tests.
- **Existing `kanban-set-state.sh` unchanged** — still works for terminal states (done, blocked, etc.). Its `--help` style usage line still prints correctly.

## Skill

Created `/home/nofidofi/.hermes/skills/thor-delegation-protocol/SKILL.md` with:

- The rule: delegation = wrapper + delegate_task, not two separate ops
- Why it exists (NOFI bug, root cause)
- Canonical sequence with code blocks
- Completion/blocked sequence (use `kanban-set-state.sh` for terminal states)
- What the wrapper guarantees
- What NOT to do (skip the wrapper, hand-edit state, etc.)
- Failure recovery with exit-code reference
- Related references

## Final kanban state after wrapper run

`MC-KANBAN-4-WIRE-PROTOCOL`:
- disk: `kanban_status: running_now`, `assignee: forge`, `status: in_progress`
- server: column `running_now` count=1, task present
- event log: `work_started` event appended with assignee=forge
- handoff: leave in `running_now`; await Argus behavioral verification, then move to `done`

## Git

Pending: commit and push. See commit message in the agent run summary.
