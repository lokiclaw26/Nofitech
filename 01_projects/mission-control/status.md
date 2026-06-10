---
id: mission-control
title: NofiTech Mission Control
phase: live
status: active
progress_pct: 100%
approval_needed: false
next_action: "LAN deployment live at http://192.168.0.29:8767/ — awaiting next NOFI directive"
blocker: ""
data_source: real
created: 2026-06-10
updated: 2026-06-11
version: 1.8.0-live-data
charter: 01_projects/mission-control/charter.md
tasks: 01_projects/mission-control/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-10/
---

# Project: NofiTech Mission Control

Local-only dashboard for the 3-agent NofiTech Ind. (Thor / Forge / Argus).

## Current state
- **v1.8.0-live-data — LAN DEPLOYED**
- URL: http://192.168.0.29:8767/ (NOFI-approved simple LAN deployment)
- 6 panels: Overview, Agents, Tasks, Projects, Provider, Logs/Health
- 1 start script: `start-mc.sh` (idempotent, NO systemd, manual restart after reboot)
- Server bound to 0.0.0.0:8767, no auth, no token usage, real data only
- Demo data hidden from main view (`?include=demo` to opt-in)

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

## Open
- Future work tracked in `00_company_os/stage-12-plan.md` (3 workstreams: real project charter/plan, real LLM provider, autostart)
- Awaiting next NOFI directive
