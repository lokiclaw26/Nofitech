---
id: RG-000-PROJECT-SETUP
title: Roguelike V1 — Stage 0: Project setup + stack confirmation
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: done
priority: high
created_at: "2026-06-11T18:45:00+00:00"
updated_at: "2026-06-11T23:10:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Stage 0 of Roguelike V1 — Dungeon Spark. NOFI approved: build a tiny 2D top-down roguelike prototype step by step. Stage 0 only: project structure + stack confirmation. NO gameplay code yet. NO Stage 1 work. NO Mission Control changes (frozen at v1.15.0)."
acceptance: "(1) /home/nofidofi/NofiTech-Ind/01_projects/roguelike-v1/ exists with charter.md, status.md, plan.md, tasks/, logs/, evidence/, qa/, design/, code/. (2) /home/nofidofi/NofiTech-Ind/01_projects/roguelike-v1/tasks/RG-000-PROJECT-SETUP.md exists with all 14 frontmatter fields. (3) events.jsonl has 4 new events: project_created, task_created, task_assigned, work_started. (4) state.json shows forge/thor/argus on RG-000. (5) Forge report on stack: HTML5 Canvas + JS, served by `python3 -m http.server 8770 --bind 0.0.0.0`, NO install required. (6) NO gameplay code written. (7) Mission Control dashboard still healthy (warnings=0, pending=0, app_health=ok) and now shows the new roguelike-v1 project + RG-000 task. (8) Argus verifies everything."
argus_result: pass
---

## Brief
The first real NofiTech project. Mission Control is frozen at v1.15.0 and is now just a monitor for this new project. Stage 0 = structure only. NO GAMEPLAY. NO STAGE 1. Stack: HTML5 Canvas + JS, run via `python3 -m http.server 8770 --bind 0.0.0.0`, open at `http://192.168.0.29:8770/`.

## Acceptance details
- folder: /home/nofidofi/NofiTech-Ind/01_projects/roguelike-v1/
- charter.md: short (≤30 lines) — concept, V1 scope, technology preference, excluded features
- status.md: frontmatter per template; phase=build, status=active, progress_pct=0%, next_action="Stage 1 — concept + MVP scope, awaiting NOFI approval"
- plan.md: ordered stage list (Stage 0 done, Stage 1 + ... to be defined by NOFI)
- tasks/: directory (empty for now, will hold RG-XXX files)
- logs/: empty dir
- evidence/: empty dir
- qa/: empty dir
- design/: empty dir (art/notes will go here later)
- code/: empty dir (the actual HTML/JS game goes here in Stage 1+)

## Stack confirmation (Forge)
- HTML5 Canvas + JavaScript: confirm browser support, no library needed
- Python `http.server` for serving: confirm `python3 -m http.server 8770 --bind 0.0.0.0` works on this host
- No installs required
- Risk: low (just static files + Python stdlib)

## Constraints (LOCKED from memory entries 002, 010)
- NO hero mode: task file FIRST (this file), events.jsonl FIRST, state.json FIRST, THEN code/structure
- NO gameplay code in Stage 0
- NO Stage 1 work
- NO Mission Control changes (frozen)
- NO installs, NO external libs, NO public internet
- No fake progress
- One stage at a time
