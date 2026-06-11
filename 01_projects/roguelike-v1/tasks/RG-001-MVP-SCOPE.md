---
id: RG-001-MVP-SCOPE
title: Roguelike V1 — Stage 1: Game Concept and MVP Scope
project: roguelike-v1
created_by: nofi
assigned_to: thor
status: complete
priority: high
created_at: "2026-06-11T23:15:00+00:00"
updated_at: "2026-06-11T23:55:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Define the exact first playable prototype of Dungeon Spark before any code is written. NO gameplay code. NO Mission Control changes (frozen at v1.15.0). NO Stage 2 work. Thor coordinates. Forge confirms HTML5 Canvas + JS technical feasibility + defines basic technical values. Argus verifies scope is small, testable, not overbuilt."
acceptance: "(1) design/game-concept.md, design/mvp-scope.md, design/controls.md, design/technical-values.md all exist with concrete values (not 'TBD'). (2) Argus must block any feature from the excluded list: procedural generation, inventory, multiple rooms/levels, complex AI, complex art, sound/music, save/load, menus, extra enemies. (3) All 14 frontmatter fields present in RG-001. (4) events.jsonl has task_created, task_assigned, work_started, forge_reported, argus_started, argus_passed, task_completed. (5) Mission Control still healthy and shows RG-001 in dashboard."
argus_result: pass
---

## Brief
Stage 1 of Dungeon Spark. The deliverable is 4 design documents that nail down what V1 IS and what it ISN'T. After this stage, NOFI approves Stage 2 (technical skeleton) which writes the actual HTML/JS.

## Acceptance details
- game-concept.md: theme, mood, what makes the prototype feel like a real dungeon, the player fantasy in 1 sentence, win/lose narrative
- mvp-scope.md: explicit "in" list, explicit "out" list, core loop in 1-2 sentences, scope-gate rules (anything not in the "in" list = not V1)
- controls.md: input mapping table, what each key does, restart behavior, edge cases
- technical-values.md: concrete numbers (not ranges, not TBD) for canvas, tile, grid, HP, speed, attack range, attack cooldown, damage, enemy behavior state, win/lose trigger, restart trigger

## Constraints (LOCKED from memory 002, 010, and the NOFI Stage 1 brief)
- NO gameplay code in this stage
- NO Stage 2 work
- NO Mission Control changes (frozen)
- NO installs
- One stage at a time
- Argus must block any feature from the excluded list
- Forge: confirm HTML5 Canvas + JS technical feasibility
