---
id: MC-BRIEF-FIX-SCHEMA
title: Restore state.json schema fields for morning brief
project: mission-control
agent: forge
assigned_to: forge
status: triage
priority: P0
created: 2026-06-28
updated: 2026-06-28
description: Re-add `pending_orders`, `app_health`, `warnings` to state.json so morning brief shows real numbers instead of "no field present"
blockers: ""
argus_result: pending
data_source: real
---

# MC-BRIEF-FIX-SCHEMA — Restore state.json schema for morning brief

## Problem
`/home/nofidofi/NofiTech-Ind/00_company_os/state.json` is missing the fields the morning brief reads:
- `pending_orders` (count of open orders)
- `app_health` (current app health status)
- `warnings` (list of current warnings)

Result: morning-brief cron reports "no field present" three times in a row.

## Required fields
Add these keys to state.json (top-level) with sensible defaults:

```json
"pending_orders": <int count of tasks with status='in_progress'>,
"app_health": "ok" | "degraded" | "down",
"warnings": <list of warning strings>,
```

## Derivation rules
- `pending_orders`: count of tasks in `tasks` dict where `status == 'in_progress'`
- `app_health`: "ok" if no warnings, "degraded" if 1-3 warnings, "down" if >3 warnings or any critical
- `warnings`: auto-populate from `mc_event.py` errors / `logs/errors.log` recent entries

## Scope
- 1 file: `/home/nofidofi/NofiTech-Ind/00_company_os/state.json`
- ≤30 LOC change
- Must not break existing `agents` / `tasks` / `updated` keys

## Verification
- `python3 -c "import json; s=json.load(open('00_company_os/state.json')); print(s['pending_orders'], s['app_health'], len(s['warnings']))"` works
- Re-run morning-brief cron: `cronjob action=run job_id=8691521f5597` should show real numbers