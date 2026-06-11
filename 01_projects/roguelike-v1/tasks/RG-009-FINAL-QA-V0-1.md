---
id: RG-009-FINAL-QA-V0-1
title: Roguelike V1 — Stage 9: Final Playable QA Pass and v0.1 Prototype Checkpoint
project: roguelike-v1
created_by: nofi
assigned_to: thor
status: complete
priority: high
created_at: "2026-06-12T04:00:00+00:00"
updated_at: "2026-06-12T04:30:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Full end-to-end playable QA pass on the Dungeon Spark prototype. Argus runs the entire 32-check QA list. Only blocking bugs may be fixed (by Forge). Then tag the v0.1 prototype release. NO new features, NO new enemies, NO polish, NO menus, NO sound, NO save/load. Mission Control stays frozen at v1.15.0."
acceptance: "(1) Task file created before any work. (2) 4+ events appended before any change. (3) Argus runs all 32 QA checks and reports pass/fail per category. (4) If blocking bugs found: Forge fixes them and Argus re-verifies. (5) If no blocking bugs: NO gameplay code changes. (6) status.md updated to v0.1 prototype complete. (7) Git commit created. (8) Annotated tag 'roguelike-v1-v0.1-playable-prototype' created. (9) Mission Control still healthy and shows v0.1. (10) Game server still serving on :8770."
argus_result: pass
---

## Brief
Stage 9 is the final checkpoint for Dungeon Spark. Argus runs the complete 32-check QA list to verify the prototype is fully playable. If a blocking bug is found, Forge fixes it (and only it). After all checks pass, the project is tagged as v0.1 prototype complete.

## Acceptance details

### QA scope
- **Launch**: game loads at http://192.168.0.29:8770/, no console errors, canvas + HUD render
- **Movement**: WASD + Arrows work, 1 tile per press, walls block, cannot leave room
- **Slime AI**: 500ms tick, moves toward player, respects walls, stops after win/lose
- **Player attack**: Space attacks facing tile, no diagonal, no through walls, 1 damage, 400ms cooldown, yellow flash
- **Contact damage**: slime damages player on contact, 1 HP per 500ms tick, red flash, dead slime inert
- **Win path**: kill slime in 3 attacks → YOU WIN → frozen → R prompt
- **Lose path**: get hit 5 times → YOU DIED → frozen → R prompt
- **Restart**: R no-op during playing; R after win/lose resets everything
- **Scope control**: no procedural, no inventory, no extra enemies, no extra rooms, no sound, no menu, no save/load
- **Mission Control**: RG-009 visible, project progress = 100%, events appended, no fake progress

### Release checkpoint
After Argus passes:
- status.md → v0.1 prototype complete
- git commit
- annotated tag `roguelike-v1-v0.1-playable-prototype`

### BUG policy
- **Blocking bug**: prevents a core feature from working (e.g. WASD doesn't move, R doesn't reset, slime never moves)
  - Forge may fix it
  - Must be a minimal surgical fix
  - Argus must re-verify
- **Non-blocking bug**: visual nit, comment typo, edge case that doesn't break the loop
  - Log it but do NOT fix
  - Mentioned in the report under "Non-blocking"

### NO new features
- NO new gameplay
- NO new polish
- NO new enemies
- NO new rooms
- NO sound
- NO menus
- DO NOT change mechanics unless a confirmed blocking bug
- DO NOT build ahead

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 9 brief)
- No external dependencies
- No installs
- One stage at a time
- Don't touch Mission Control (frozen)
- Don't add new features
- Only fix blocking bugs
- Keep code simple and readable
- Argus must run the full 32-check QA
