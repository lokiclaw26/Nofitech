---
id: roguelike-v1
title: Roguelike V1 — Dungeon Spark
phase: ship
status: complete
progress_pct: 100%
approval_needed: false
next_action: "V0.1 PROTOTYPE COMPLETE — 9 stages, 357 lines, full Argus QA pass. Awaiting NOFI decision: freeze v0.1 or plan v0.2."
blocker: ""
data_source: real
created: 2026-06-11
updated: 2026-06-12
version: 0.1
charter: 01_projects/roguelike-v1/charter.md
plan: 01_projects/roguelike-v1/plan.md
tasks: 01_projects/roguelike-v1/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-12/
code: 01_projects/roguelike-v1/code/
---

# Project: Roguelike V1 — Dungeon Spark

**V0.1 PROTOTYPE COMPLETE.** First playable roguelike prototype, shipped 2026-06-12.

## Current state
- **v0.1** — feature-complete, Argus QA pass 49/49
- 357 lines in single `code/index.html`
- 9 stages shipped: Stage 0 (setup), Stage 1 (scope), Stage 2 (skeleton), Stage 3 (move), Stage 4 (slime AI), Stage 5 (attack), Stage 6 (contact damage), Stage 7 (win/lose), Stage 8 (restart), Stage 9 (final QA)
- 0 blocking bugs, 3 non-blocking cosmetic concerns
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

## Open (post-v0.1)
- Awaiting NOFI decision: freeze v0.1 or plan v0.2 improvements
- 3 non-blocking cosmetic concerns from Stage 9 QA (stale caption, raw state string, stale comment)

## Git
- 9 stage tags: `roguelike-v1-stage-0` through `roguelike-v1-stage-8`
- Release tag: `roguelike-v1-v0.1-playable-prototype` (annotated)
- Total commits in this run: 9 (one per stage) + closure commits
