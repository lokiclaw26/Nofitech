---
id: roguelike-v1
title: Roguelike V1 — Dungeon Spark
phase: build
status: v0.2-stage-12-shipped
progress_pct: 38%
approval_needed: true
next_action: "Stage 12 (Better Visual Style) complete. Awaiting NOFI approval to begin Stage 13 — Combat Feedback / Juice."
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

**V0.1 PROTOTYPE SHIPPED 2026-06-12. V0.2 STAGES 11-12 SHIPPED 2026-06-13.**

## Current state
- **v0.1** — feature-complete, Argus QA pass 49/49, released as `roguelike-v1-v0.1-playable-prototype`
- **v0.2 dev** — Stages 11 (obstacles) + 12 (visuals) shipped, 3 more build stages + 1 QA checkpoint remaining (13-16)
- 477 lines in single `code/index.html` (v0.1 was 357; v0.2 +120)
- Run: `python3 -m http.server 8770 --bind 0.0.0.0` (or `bash code/serve-game.sh`)
- Open: `http://192.168.0.29:8770/`

## V0.1 features (still working)
- Player movement: WASD or Arrows, 1 tile per press, walls block
- Slime enemy: greedy Manhattan chase, 500ms tick, 1 HP per contact tick
- Player attack: Space, 1 dmg, 400ms cooldown, yellow flash
- Win: 3 attacks to kill slime → YOU WIN → R to restart
- Lose: 5 hits from slime → YOU DIED → R to restart
- Restart: R key, only in win/lose state, resets all 12 fields
- No external deps, no installs, no auth, no sound, no menus, no save/load

## V0.2 features (Stages 11-12)
- 6 hand-authored obstacle tiles (pillars) at (6,4), (12,3), (4,7), (14,7), (8,10), (15,9)
- Floor: 2-tone checker `#2a2a2a`/`#3a3a3a`
- Walls: base `#1a1a1a` + 1px `#333` inner-edge highlight
- Pillars: base `#555` + 24x24 `#444` carved inset
- Slime: round blob (arc + shine highlight)
- Player: tiny knight (body + helmet + eye + sword in facing direction)
- HUD top bar: backdrop, HP rects, slime HP rects, "DUNGEON SPARK" title with shadow, state indicator
- HUD bottom bar: backdrop, controls text
- All v0.1 + Stage 11 mechanics byte-identical to Stage 11 (movePlayer, playerAttack, slimeTick, inBoundsAndFree, applyContactDamage, resetGame, keydown, setInterval, OBSTACLES, isObstacle, win condition, lose condition, overlays)

## Completed stages
- Stage 0 — Project setup + stack confirmation
- Stage 1 — Game Concept and MVP Scope (4 design docs)
- Stage 2 — Technical Skeleton (canvas + room + walls + player + slime + HUD)
- Stage 3 — Player Movement
- Stage 4 — Slime AI Movement
- Stage 5 — Basic Player Attack
- Stage 6 — Slime Contact Damage
- Stage 7 — Win/Lose States
- Stage 8 — Restart
- Stage 9 — Final Playable QA Pass + v0.1 Prototype Checkpoint (49/49 PASS)
- Stage 10 — Fun and Visual Upgrade Plan (planning only)
- Stage 11 — Room Obstacles (6 pillars, 20/20 Argus PASS, 357→393 LOC)
- Stage 12 — Better Visual Style (8 visual changes, 31/31 Argus PASS, 393→477 LOC)

## V0.2 plan (Stages 13-16, awaiting NOFI approval)
- Stage 13 — Combat Feedback / Juice (slime hit flash, sword slash arc, "-1" damage numbers, screen shake — no animation loop)
- Stage 14 — Exit Door Objective (replaces Stage 7 win condition)
- Stage 15 — One Health Potion
- Stage 16 — v0.2 QA Checkpoint

## Hard constraints (locked)
- HTML5 Canvas + vanilla JS only
- No external libraries, no new engine
- No procedural generation, no inventory, no complex art system
- No sound unless NOFI approves separately
- No multiplayer, no save/load, no mobile export

## Open
- NOFI must approve Stage 13 to continue v0.2 build
- 3 non-blocking cosmetic concerns from Stage 9 QA (stale caption, raw state string, stale comment) — 1 already addressed in Stage 12 (raw "State: playing" → formatted "PLAYING")

## Git
- 12 stage tags: `roguelike-v1-stage-0` through `roguelike-v1-stage-12`
- Release tag: `roguelike-v1-v0.1-playable-prototype` (annotated)
- Stage 12 commit: pending
