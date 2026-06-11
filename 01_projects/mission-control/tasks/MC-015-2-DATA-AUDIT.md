---
id: MC-015-2-DATA-AUDIT
title: "Stage 15.2 — Full data-source audit and backfill"
project: mission-control
created_by: nofi
assigned_to: forge
status: in_progress
priority: normal
created_at: "2026-06-11T11:22:38+00:00"
updated_at: "2026-06-11T11:22:38+00:00"
current_stage: verify
blocker: ""
data_source: real
description: Stage 15.2 audits the Mission Control data surface end to end. Forge is backfilling the four real task files (MC-013, MC-014, MC-015, MC-015-1) that document work shipped since Stage 12, refreshing project status.md to reflect v1.10.1-live-version and the audit phase, and appending events to events.jsonl. Then Argus runs a full data-source audit (no key leaks, demo hidden, schema valid, all 14 frontmatter fields present, events count correct, state.json current).
acceptance: Five new real task files present (MC-013..MC-015-2); all 14 frontmatter fields per file; events.jsonl count grows by at least 13 lines; state.json reflects Stage 15.2 assignments; no `sk-` / `api_key` / `password` / `secret` strings in any new file; demo data still hidden by default; Argus issues pass/fail verdict on the full audit.
argus_result: pending
---

## Brief
Stage 15.2 is the data-source audit. Before Argus can do a clean read of
the dashboard, Forge has to backfill the four task files (MC-013..MC-015-1)
that describe work already shipped, plus this one (MC-015-2-DATA-AUDIT) for
the audit work itself. The companion deliverables are:

1. `01_projects/mission-control/status.md` — updated to v1.10.1-live-version
   with `phase: verify` and a `next_action` that names the audit.
2. `00_company_os/events.jsonl` — appended events for the five tasks
   (task_created, task_assigned, work_started, argus_passed for the four
   complete ones; no argus_passed for this task until Argus signs off).
3. `00_company_os/04_agents/state.json` — all three agents pointing at the
   new Stage 15.2 assignment.

## Acceptance
- Five new real task files present (MC-013..MC-015-2).
- All 14 frontmatter fields present per file.
- events.jsonl count grows by at least 13 lines (3 per task × 4 done
  + 3 for this one, plus optional `forge_reported` for the audit handoff).
- state.json reflects Stage 15.2 assignments for forge / thor / argus.
- No `sk-` / `api_key` / `password` / `secret` strings in any new file.
- Demo data still hidden by default.
- Argus issues pass/fail verdict on the full audit.

## Notes
- `status: in_progress` — this task is the work being done right now.
- `current_stage: verify` — the stage is in the audit / verification phase,
  not a new build phase.
- `argus_result: pending` — Argus has not run on this stage yet.
- Forged by Forge; verified by Argus (forthcoming).
