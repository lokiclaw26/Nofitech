---
id: roguelike-v1
title: Roguelike V1 — Dungeon Spark
phase: build
status: v0.2-stage-11-shipped
progress_pct: 25%
approval_needed: true
next_action: "Stage 11 (Room Obstacles) complete. Awaiting NOFI approval to begin Stage 12 — Better Visual Style."
blocker: ""
data_source: real
created: 2026-06-11
updated: 2026-06-13
version: 0.2-dev
charter: 01_projects/roguelike-v1/charter.md
plan: 01_projects/roguelike-v1/plan.md
tasks: 01_projects/roguelike-v1/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-12/ 00_company_os/04_agents/logs/2026-06-13/
code: 01_projects/roguelike-v1/code/
---

# Project: Roguelike V1 — Dungeon Spark

**V0.1 PROTOTYPE SHIPPED 2026-06-12. V0.2 STAGE 11 SHIPPED 2026-06-13.**

## Current state
- **v0.1** — feature-complete, Argus QA pass 49/49, released as `roguelike-v1-v0.1-playable-prototype`
- **v0.2 dev** — Stage 11 shipped, 4 more build stages + 1 QA checkpoint remaining (12-16)
- 393 lines in single `code/index.html` (v0.1 was 357; +36 from Stage 11)
- Run: `python3 -m http.server 8770 --bind 0.0.0.0` (or `bash code/serve-game.sh`)
- Open: `http://192.168.0.29:8770/`

## V0.1 features (still working)
- Player movement: WASD or Arrows, 1 tile per press, walls block
- Slime enemy: greedy Manhattan chase, 500ms tick, 1 HP per contact tick
- Player attack: Space, 1 dmg, 400ms cooldown, yellow flash
- Win: 3 attacks to kill slime → YOU WIN → R to restart
- Lose: 5 hits from slime → YOU DIED → R to restart
- Restart: R key, only in win/lose state, resets all 12 fields
- HUD: Player HP, Slime HP, State indicator, controls hint
- No external deps, no installs, no auth, no sound, no menus, no save/load

## V0.2 features (Stage 11)
- 6 hand-authored obstacle tiles at (6,4), (12,3), (4,7), (14,7), (8,10), (15,9)
- Obstacles render as simple `#555` mid-gray stone blocks (no polish, no borders, no highlights)
- Player cannot walk through obstacles
- Slime cannot walk through obstacles
- Slime AI pathing around obstacles (greedy Manhattan + `inBoundsAndFree` obstacle check)
- Attack swing blocked by obstacles (no flash, no damage, identical to wall swing)
- 0 unreachable floor cells, BFS confirms slime can reach player in 25 steps
- 0 procedural generation, 0 new state objects except `OBSTACLES` const + `isObstacle` helper

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
- Stage 11 — Room Obstacles (6 pillars, 20/20 Argus PASS, 357→393 LOC)

## V0.2 plan (Stages 12-16, awaiting NOFI approval)
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
- NOFI must approve Stage 12 to continue v0.2 build
- 3 non-blocking cosmetic concerns from Stage 9 QA (stale caption, raw state string, stale comment)

## Git
- 11 stage tags: `roguelike-v1-stage-0` through `roguelike-v1-stage-11`
- Release tag: `roguelike-v1-v0.1-playable-prototype` (annotated)
- Stage 11 commit: pending
