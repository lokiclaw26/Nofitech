---
task_id: MC-KANBAN-ASSIGN-1
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-17T10:59:00+04:00
---

# Thor Coordination Log — MC-KANBAN-ASSIGN-1

## NOFI's request (verbatim)
*"there are tasks that are unassigned... i want to add an option when i click on the card to allow me to assign it to an agent"*

## What I did — investigation + orchestration, 0 implementation bytes

### Investigation findings
- 7 of 49 tasks are unassigned: MC-007 (triage), MC-004 (running), MC-005, MC-006 (blocked), MC-001, MC-002, MC-003 (done)
- Data model already supports `assigned_to` in Format A (YAML) and `owner` in Format B (table)
- The HTML already has CSS for assignee chips (line 316-323) but no UI to CHANGE the assignee via click
- The smart diff code already handles card re-rendering — can be reused for assign updates

## Plan
- Forge: PATCH endpoint + UI buttons + click handler
- Argus: 14-step behavioral test (mandatory, not optional)

## What I (Thor) did NOT do
- 0 bytes of implementation
- Did not edit any code
- Did not assign any tasks yet (NOFI will use the new UI to do that)

## Risk assessment
Small feature but 2 risk areas:
1. Smart diff might not re-render the card after assignment (could leave old assignee chip)
2. PATCH endpoint might not handle Format B correctly

Behavioral test is the only way to catch these. No structural-only verification this time.

## Open follow-ups
- Bulk assign (out of scope)
- "Queued" column (still pending)
- MC-KANBAN-FREEZE-ACCEPTANCE (after this)
