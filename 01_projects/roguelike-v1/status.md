---
id: roguelike-v1
title: Roguelike V1 — Dungeon Spark
phase: paused
status: paused
progress_pct: 38%
approval_needed: false
next_action: "Project PAUSED 2026-06-13 per NOFI directive. Last shipped: Stage 12 (Better Visual Style). Game server still live at http://192.168.0.29:8770/. Awaiting NOFI new project brief (TBD)."
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

**PAUSED 2026-06-13 PER NOFI DIRECTIVE. NEW PROJECT BRIEF PENDING.**

## Current state
- **Status:** Paused. No further v0.2 work scheduled.
- **Last shipped:** Stage 12 — Better Visual Style (commit `7ad2638`, tag `roguelike-v1-stage-12`)
- **v0.1 release:** `roguelike-v1-v0.1-playable-prototype` (annotated, still valid)
- **Code baseline:** 477 lines in single `code/index.html` (UNCHANGED at pause)
- **Run:** `python3 -m http.server 8770 --bind 0.0.0.0` (server still running, PID 137327, HTTP 200)
- **Open:** http://192.168.0.29:8770/

## V0.1 features (shipped, still working)
- Player movement: WASD or Arrows, 1 tile per press, walls block
- Slime enemy: greedy Manhattan chase, 500ms tick, 1 HP per contact tick
- Player attack: Space, 1 dmg, 400ms cooldown, yellow flash
- Win: 3 attacks to kill slime → YOU WIN → R to restart
- Lose: 5 hits from slime → YOU DIED → R to restart
- Restart: R key, only in win/lose state

## V0.2 features shipped (Stages 11-12)
- 6 hand-authored obstacle tiles (pillars) at (6,4), (12,3), (4,7), (14,7), (8,10), (15,9)
- Floor: 2-tone checker, walls with stone inner highlight, carved pillars
- Slime: round blob (arc + shine highlight)
- Player: tiny knight (body + helmet + eye + sword in facing direction)
- HUD top bar: backdrop, HP rects, slime HP rects, "DUNGEON SPARK" title with shadow, state indicator
- HUD bottom bar: backdrop, controls text

## V0.2 stages NOT YET BUILT (paused before these)
- Stage 13 — Combat Feedback / Juice
- Stage 14 — Exit Door Objective
- Stage 15 — One Health Potion
- Stage 16 — v0.2 QA Checkpoint

## All completed stages
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
- Stage 11 — Room Obstacles (6 pillars, 20/20 Argus PASS)
- Stage 12 — Better Visual Style (8 visual changes, 31/31 Argus PASS)
- Stage 13 — RGV1 Freeze (state-change only, no code, no QA)

## Resume conditions
The project can be resumed by NOFI saying any of:
- "Resume RGV1 Stage 13" — picks up where Stage 12 left off
- "Resume RGV1 from v0.1" — discards the v0.2 work, reverts to the v0.1 prototype as the working baseline
- A completely different direction

## Hard constraints (locked, still apply on resume)
- HTML5 Canvas + vanilla JS only
- No external libraries, no new engine
- No procedural generation, no inventory, no complex art system
- No sound unless NOFI approves separately
- No multiplayer, no save/load, no mobile export

## Open
- Awaiting NOFI new project brief

## Git
- 13 stage tags: `roguelike-v1-stage-0` through `roguelike-v1-stage-13` (RG-013 is the freeze, machine-validated by `STATUS: complete` equivalent — events + commit + state.json)
- Release tag: `roguelike-v1-v0.1-playable-prototype` (annotated, still valid)
- Pause tag: `roguelike-v1-paused` (pending, annotated)
- Last code commit: `7ad2638` (Stage 12)
- Freeze commit: pending
