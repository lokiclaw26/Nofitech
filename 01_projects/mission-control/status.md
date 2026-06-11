---
id: mission-control
title: NofiTech Mission Control
phase: verify
status: active
progress_pct: "100% code / audit in progress"
approval_needed: false
next_action: "Stage 15.2 data-source audit — backfilling real task files, then handing to Argus for full verification"
blocker: ""
data_source: real
created: 2026-06-10
updated: 2026-06-11
version: 1.10.1-live-version
charter: 01_projects/mission-control/charter.md
tasks: 01_projects/mission-control/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-11/
---

# Project: NofiTech Mission Control

Local-only dashboard for the 3-agent NofiTech Ind. (Thor / Forge / Argus).

## Current state
- **v1.10.1-live-version — LIVE on LAN, version + commit rendered live**
- URL: http://127.0.0.1:8767/ (local) and http://192.168.0.29:8767/ (LAN)
- 6 panels: Overview, Agents, Tasks, Projects, Provider, Logs/Health
- 1 start script: `start-mc.sh` (idempotent, NO systemd, manual restart after reboot)
- Server bound to 0.0.0.0:8767, no auth, no token usage, real data only
- Demo data hidden from main view (`?include=demo` to opt-in)
- **Stage 15.2 — in audit phase**: data sources and task surface being verified
  end-to-end. Forge is backfilling the four task files (MC-013..MC-015-1) that
  document work shipped since Stage 12, plus one new task for this stage
  (MC-015-2-DATA-AUDIT). Once backfill lands, Argus runs a full data-source
  audit and either passes or pushes back.

## Completed stages
- Stage 1 — Discovery: archive audited
- Stage 2 — MVP definition: 6 sections + build order locked
- Stage 3 — App shell shipped + verified (v1.0.0)
- Stage 4 — Overview panel shipped (v1.1.0)
- Stage 5 — Agents panel shipped (v1.2.0)
- Stage 6 — Tasks panel shipped (v1.3.0)
- Stage 7 — Projects panel shipped (v1.4.0)
- Stage 8 — Provider/Model panel shipped (v1.5.0)
- Stage 9 — Logs/Health panel shipped (v1.6.0)
- Stage 10 — Full QA: 18/18 PASS, 0 blocking (v1.7.0)
- Stage 11 — Stabilization: git init, .gitignore, _detect_lan_ip (v1.7.0 MVP tag)
- Stage 12 — Live data: demo hidden, strict log levels, no fake values (v1.8.0-live-data)
- LAN deployment — NOFI approved
- Stage 13 — Inbox triage and 3-agent charter finalization (MC-013-INBOX-TRIAGE, complete)
- Stage 14 — Automatic task and event wiring (MC-014-AUTO-WIRING, complete)
- Stage 15 — Mission Control UI/UX upgrade (MC-015-UI-UX, complete)
- Stage 15.1 — Make version and commit live (MC-015-1-LIVE-VERSION, complete, v1.10.1-live-version)
- Stage 15.2 — Full data-source audit and backfill (MC-015-2-DATA-AUDIT, in_progress)

## Open
- Stage 15.2 audit: verify all real tasks are visible, all events surface,
  all state.json fields reflect current activity, no key leaks, demo data
  still hidden by default.
- Future work tracked in `00_company_os/stage-12-plan.md` (3 workstreams:
  real project charter/plan, real LLM provider, autostart).
