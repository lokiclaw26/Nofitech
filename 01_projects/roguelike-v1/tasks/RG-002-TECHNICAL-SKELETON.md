---
id: RG-002-TECHNICAL-SKELETON
title: Roguelike V1 — Stage 2: Technical Skeleton
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: done
priority: high
created_at: "2026-06-12T00:05:00+00:00"
updated_at: "2026-06-12T00:30:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "First runnable browser version of Dungeon Spark. VISUAL SKELETON ONLY. Renders: canvas, one dungeon room, walls, floor, player placeholder, slime placeholder, HUD. NO input, NO movement, NO attack, NO AI, NO win/lose, NO restart. Single index.html preferred. No external dependencies, no installs. Mission Control stays frozen at v1.15.0."
acceptance: "(1) /01_projects/roguelike-v1/code/index.html exists and is the runnable file. (2) Optionally: game.js and style.css if Forge finds them cleaner. (3) Optionally: serve-game.sh. (4) Renders: 640x480 canvas, 20x15 tile grid, walls on all 4 edges, floor interior, blue player at (2,2), red/purple slime at (17,12), HUD with Player HP=5 and Slime HP=3, state text 'DUNGEON SPARK', controls placeholder text. (5) NO input handlers, NO keydown listeners, NO movement, NO attack, NO AI, NO win/lose/restart. (6) Documented run command in code/README.md: `python3 -m http.server 8770 --bind 0.0.0.0`. (7) NO external dependencies, no <script src='cdn'>, no <link href='cdn'>. (8) Page loads without console errors. (9) Mission Control still frozen, still healthy."
argus_result: pass
---

## Brief
Stage 2 = visual skeleton. The player must see the room. They cannot interact with it. This stage proves: (a) the canvas + grid system works, (b) the visual style (blue player, red/purple slime, black walls) is correct, (c) the HUD text renders properly, (d) the run command works end-to-end. No input, no game logic, no animation, no game loop, no state machine. Just a static rendered scene.

## Acceptance details
- `code/index.html` is the entry point. Single file is fine. If you split into game.js and/or style.css, that's OK but keep it small.
- Canvas: 640×480, 32×32 tiles, 20×15 grid
- Walls: black (`#000` or `rgb(0,0,0)`), the 4 outer edges (col 0, col 19, row 0, row 14) — 66 wall tiles
- Floor: dark gray (`#333` or `rgb(50,50,50)`), interior (col 1-18, row 1-13) — 234 floor tiles
- Player: blue square at tile (2,2)
- Slime: red/purple square at tile (17,12)
- HUD: top-left "Player HP: 5", top-right "Slime HP: 3", center "DUNGEON SPARK"
- Controls placeholder: bottom of canvas: "WASD/Arrows: move | Space: attack | R: restart"
- All from technical-values.md, no TBDs

## Out of scope (NOT in Stage 2)
- No keydown/keyup listeners
- No requestAnimationFrame loop (a single static render is enough)
- No game state object that updates
- No setTimeout/setInterval
- No collision detection
- No attack
- No enemy AI
- No health changes
- No win/lose/restart logic
- No sound
- No images, no fonts, no external resources
- No multiple rooms, no extra enemies
- No Mission Control changes

## Files (Stage 2)
- `code/index.html` (required) — the full game file
- `code/game.js` (optional) — only if it makes index.html cleaner
- `code/style.css` (optional) — only if you want to put the body { margin: 0 } etc. there
- `code/README.md` (required) — how to run
- `code/serve-game.sh` (optional) — convenience wrapper, but not required since `python3 -m http.server` is the canonical run

## Constraints (LOCKED from memory 002, 010, and Stage 1 brief)
- No external dependencies (no CDN, no npm, no libraries)
- No installs
- No input handlers
- No animation
- No state machine logic
- One stage at a time
- Argus must verify: no input works, no movement, no attack, no AI, no win/lose/restart
