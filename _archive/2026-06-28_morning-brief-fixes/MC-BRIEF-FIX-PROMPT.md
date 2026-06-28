---
id: MC-BRIEF-FIX-PROMPT
title: Rewrite morning-brief cron prompt to fail loud on bad data
project: mission-control
agent: forge
assigned_to: forge
status: triage
priority: P0
created: 2026-06-28
updated: 2026-06-28
description: Fix two bugs: (1) model outputs tool-call JSON as plain text → file never read, (2) prompt looks for wrong event types — kanban emits auto_process_* not task_assigned/work_started
blockers: ""
argus_result: pending
data_source: real
---

# MC-BRIEF-FIX-PROMPT — Rewrite morning-brief cron prompt

## Problem
Two distinct failure modes observed in 2026-06-27 + 2026-06-28 morning briefs:

1. **06-28 run**: model output tool-call JSON as plain text instead of executing tools → file never read → empty brief delivered to user. Cron status="ok" but actual deliverable was garbage.

2. **06-27 run**: brief printed but referenced WRONG event types (`task_assigned`/`work_started`) — kanban actually emits `auto_process_started`/`auto_process_moved_to_ready`/`auto_process_completed`/`task_dispatched`/`result_recorded`/`auto_process_moved_to_done`. Result: "No active in-flight tasks identified" even when kanban is actively churning.

## Required prompt changes

### A. Anchor "now" to current time, NOT to last event ts
Old: "Use the file's most recent event timestamp as the 'now' anchor"
New: "Use `date -u +'%Y-%m-%dT%H:%M:%SZ'` as `now`. If most recent event ts is > 1 hour old, FLAG STALE."

### B. Real event types
Replace `task_assigned`/`work_started` references with:
- `auto_process_started`
- `auto_process_moved_to_ready`
- `auto_process_dispatched`
- `task_dispatched`
- `work_started`

In-flight = any of these WITHOUT a matching completion event for the same `task_id`.

### C. Fail loud on missing data
If a read_file returns empty / file missing, print:
```
[BRIEF FAILED: <file> missing or empty — fixing required]
```
Do NOT silently produce an empty brief. Do NOT say "SILENT" unless EVERYTHING is genuinely normal.

### D. Force tool execution
Add to prompt start:
```
STEP 0 — EXECUTE the read_file tool calls below BEFORE producing any output.
Do NOT print tool call JSON as text. Actually call the tools.
```

### E. Stale agent flag
If any agent's `last_activity` > 7 days old, prefix that agent's status line with `[STALE]`.

## Scope
- 1 file: cron prompt stored in `~/.hermes/cron/jobs/8691521f5597.json` (or wherever the prompt lives)
- ≤80 LOC of prompt text changes
- No new dependencies

## Verification
- `cronjob action=run job_id=8691521f5597` should produce a 5-section brief with REAL numbers
- Confirm tool calls are actually executed (check `~/.hermes/cron/output/8691521f5597/<date>.md` for "ToolResult" entries, not just plain text JSON)
- Confirm in-flight section lists real running tasks, not "No active tasks identified"