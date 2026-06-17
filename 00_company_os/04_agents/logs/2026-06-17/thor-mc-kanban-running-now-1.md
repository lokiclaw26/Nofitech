---
task_id: MC-KANBAN-RUNNING-NOW-1
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-17T11:31:00+04:00
---

# Thor Coordination Log — MC-KANBAN-RUNNING-NOW-1

## NOFI's request (verbatim)
*"add a column called RUNNING NOW ... and only should show the task which is running and if the task is completed it should be moved to done ... in progress column is very confusing and the meaning is too vast... tasks which waiting for my order might stay there for days.. so it shouldnt be mixed with tasks which are MOMENTARILY being ran by the team.. if a task is pending or waiting that means its NOT RUNNING NOW ... keep that in mind ... ONLY AND ONLY TASKS WHICH ARE BEING PROCESSED AND WORKED ON BY ANY AGENT SHOULD BE IN THE RUNNING NOW COLUMN STRICTLY"*

## What I did — investigation + orchestration, 0 implementation bytes

### Investigation findings

Looked at the current "In Progress" column. It has 8 tasks:
- 6 MC-* tasks with `task_completed` events but `status: in_progress` (stale)
- DIY-011 (genuine in progress)
- MC-004-tasks-panel (legacy from June 10)

NOFI is right: "in progress" is too broad. The 6 stale tasks have all been completed but their status field was never updated, so they sit in this column indefinitely.

### Design decision (locked)

Keep the existing `running` column id but **change the label from "In Progress" to "Ready"**. Add a new `running_now` column with label "Running Now". Update the status mapping:
- `triage` → `triage`
- `todo` → `todo`
- `ready` / `in_progress` / `in-progress` → `ready` (column id, "Ready" label)
- `running_now` / `in_work` / `active` → `running_now` (column id, "Running Now" label)
- `blocked` → `blocked`
- `complete` / `done` → `done`

This way:
- 6 stale in_progress tasks naturally move from "In Progress" to "Ready" (correct — they're not being worked on, but they're not "in triage" either)
- Clean semantic split: Ready = waiting, Running Now = active
- 7 columns total

Plus clean up the 6 stale tasks by setting their status to `complete` so they land in Done.

### Plan
- Forge: parser + serve.py + 6 task cleanups + UI tweaks
- Argus: 10-step behavioral test

## What I (Thor) did NOT do
- 0 bytes of implementation
- Did not edit any parser, serve, html, or task files

## Risk assessment
- Renaming "In Progress" → "Ready" is a deliberate semantic change. If NOFI wanted "In Progress" to stay (just with a different default state), this is wrong. The wording "in progress column is very confusing" suggests this rename is correct.
- The 6 stale tasks are clean fix. They'll move to Done.

## Open follow-ups
- After this: MC-KANBAN-FREEZE-ACCEPTANCE
- Future: auto-detect "actively being worked on" via cron
