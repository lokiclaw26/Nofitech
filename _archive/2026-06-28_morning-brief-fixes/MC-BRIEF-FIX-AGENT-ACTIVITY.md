---
id: MC-BRIEF-FIX-AGENT-ACTIVITY
title: Live agent last_activity updates in kanban scripts
project: mission-control
agent: forge
assigned_to: forge
status: triage
priority: P0
created: 2026-06-28
updated: 2026-06-28
description: Patch kanban cron scripts to update agent last_activity on every tick — currently frozen at 2026-06-17 (10 days stale)
blockers: ""
argus_result: pending
data_source: real
---

# MC-BRIEF-FIX-AGENT-ACTIVITY — Live agent last_activity updates

## Problem
`/home/nofidofi/NofiTech-Ind/00_company_os/04_agents/state.json` shows `last_activity` for all three agents frozen at `2026-06-17T12:01:00+04:00` — 10 days stale. The kanban crons run every minute but never update this file.

## Required fix
Add `last_activity` update to the kanban scripts in `/home/nofidofi/.hermes/scripts/`:

- `kanban-auto-process.sh` → update forge.last_activity when task moves to ready
- `kanban-auto-execute.sh` → update forge.last_activity when task completes
- `kanban-auto-done.sh` → update argus.last_activity when QA passes
- `kanban-auto-dispatch.sh` → update thor.last_activity when supervisor delegates

Pattern (use existing `kanban-set-state.sh` if available, else inline jq):
```bash
now=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
jq --arg now "$now" '.agents.<agent>.last_activity = $now' \
  /home/nofidofi/NofiTech-Ind/00_company_os/04_agents/state.json > tmp && mv tmp state.json
```

## Scope
- ≤4 files (4 kanban scripts)
- ≤40 LOC total
- Must not break existing script logic (add at end, exit 0 on success)

## Verification
- Trigger one kanban cycle (or wait 1m for next tick)
- Check `04_agents/state.json` → `forge.last_activity` should be < 60s old
- Re-run morning-brief cron → "AGENT STATUS" section should show real recent timestamps