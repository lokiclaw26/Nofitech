---
id: roguelike-v1
title: Roguelike V1 — Dungeon Spark
phase: plan
status: v0.2-planning
progress_pct: 12%
approval_needed: true
next_action: "Stage 10 (v0.2 plan) complete. Awaiting NOFI approval to begin Stage 11 — Room Obstacles."
blocker: ""
data_source: real
created: 2026-06-11
updated: 2026-06-13
version: 0.1
charter: 01_projects/roguelike-v1/charter.md
plan: 01_projects/roguelike-v1/plan.md
tasks: 01_projects/roguelike-v1/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-12/ 00_company_os/04_agents/logs/2026-06-13/
code: 01_projects/roguelike-v1/code/
---

# Project: Roguelike V1 — Dungeon Spark

**V0.1 PROTOTYPE SHIPPED 2026-06-12. V0.2 PLAN COMPLETE 2026-06-13.**

## Current state
- **v0.1** — feature-complete, Argus QA pass 49/49, released as `roguelike-v1-v0.1-playable-prototype`
- **v0.2 plan** — Stage 10 complete, 6 stages proposed (11–16)
- 357 lines in single `code/index.html` (v0.1 baseline; v0.2 estimated +150–230 LOC)
- Run: `python3 -m http.server 8770 --bind 0.0.0.0` (or `bash code/serve-game.sh`)
- Open: `http://192.168.0.29:8770/`

## Features (V0.1)
- Player movement: WASD or Arrows, 1 tile per press, walls block
- Slime enemy: greedy Manhattan chase, 500ms tick, 1 HP per contact tick
- Player attack: Space, 1 dmg, 400ms cooldown, yellow flash
- Win: 3 attacks to kill slime → YOU WIN → R to restart
- Lose: 5 hits from slime → YOU DIED → R to restart
- Restart: R key, only in win/lose state, resets all 12 fields
- HUD: Player HP, Slime HP, State indicator, controls hint
- No external deps, no installs, no auth, no sound, no menus, no save/load

## Completed stages
- Stage 0 — Project setup + stack confirmation
- Stage 1 — Game Concept and MVP Scope (4 design docs)
- Stage 2 — Technical Skeleton (canvas + room + walls + player + slime + HUD)
- Stage 3 — Player Movement (WASD/Arrows, wall collision)
- Stage 4 — Slime AI Movement (greedy Manhattan, 500ms tick)
- Stage 5 — Basic Player Attack (Space, 400ms cooldown, yellow flash)
- Stage 6 — Slime Contact Damage (1 HP per 500ms tick, red flash, dead slime inert)
- Stage 7 — Win/Lose States (state machine, YOU WIN / YOU DIED overlays)
- Stage 8 — Restart (R key, resetGame function)
- Stage 9 — Final Playable QA Pass + v0.1 Prototype Checkpoint (49/49 PASS)
- Stage 10 — Fun and Visual Upgrade Plan (5 candidates, 6-stage v0.2 plan, 0 code)

## V0.2 plan (proposed, awaiting NOFI approval)
- Stage 11 — Room Obstacles (static pillars, hand-authored `OBSTACLES` constant)
- Stage 12 — Better Visual Style (fillRect knight + arc blob, dungeon floor pattern, HUD polish)
- Stage 13 — Combat Feedback / Juice (slime hit flash, sword slash arc, "-1" numbers, screen shake — no animation loop)
- Stage 14 — Exit Door Objective (replaces Stage 7 win condition: kill slime → door unlocks → step on door → win)
- Stage 15 — One Health Potion (one-shot +1 HP pickup, no inventory)
- Stage 16 — v0.2 QA Checkpoint (full regression against v0.1 features + new v0.2 surfaces)

## Hard constraints (locked)
- HTML5 Canvas + vanilla JS only
- No external libraries, no new engine
- No procedural generation, no inventory, no complex art system
- No sound unless NOFI approves separately
- No multiplayer, no save/load, no mobile export

## Open
- NOFI must approve Stage 11 to begin v0.2 build
- 3 non-blocking cosmetic concerns from Stage 9 QA (stale caption, raw state string, stale comment)

## Git
- 10 stage tags: `roguelike-v1-stage-0` through `roguelike-v1-stage-10`
- Release tag: `roguelike-v1-v0.1-playable-prototype` (annotated)
- Stage 10 commit: `d48f329`
