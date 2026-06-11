---
id: RG-003-PLAYER-MOVEMENT
title: Roguelike V1 — Stage 3: Player Movement
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: complete
priority: high
created_at: "2026-06-12T00:35:00+00:00"
updated_at: "2026-06-12T01:00:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Add keyboard input and grid-based player movement. WASD or Arrow keys move the player 1 tile per key press. Wall collision: cannot enter wall tiles. Player facing direction updates. NO attack, NO enemy AI, NO win/lose, NO restart. Mission Control stays frozen at v1.15.0."
acceptance: "(1) keydown listener on window for W/A/S/D and Arrow Up/Left/Down/Right. (2) Each press moves the player exactly 1 tile in the corresponding direction. (3) Wall collision: pressing a key into a wall = no movement. (4) Player facing direction (used by HUD/attack later) updates on every move. (5) NO Space handling (attack is Stage 5). (6) NO R handling (restart is Stage 6+). (7) NO slime movement. (8) NO damage. (9) Slime stays at (17,12), does not react. (10) The static render function becomes a re-render function called after each move. (11) Game still uses single index.html (or split into game.js if cleaner). (12) NO external dependencies. (13) page loads without console errors. (14) Mission Control still frozen, still healthy."
argus_result: pass
---

## Brief
Stage 3 adds the only interaction in this stage: the player can move around the room. Movement is grid-based, discrete, 1 tile per key press. Walls block movement. The slime is still a static decoration. The attack key (Space) does nothing yet. The restart key (R) does nothing yet. There is no win or lose state. The game is "playing" by default.

## Acceptance details

### Input (per design/controls.md)
- `keydown` listener on `window`
- Keys (case-insensitive): `w`, `a`, `s`, `d`, `ArrowUp`, `ArrowLeft`, `ArrowDown`, `ArrowRight`
- Default key behavior on these keys is **preventDefault()**'d so the page doesn't scroll on arrow keys
- Other keys are NOT prevented
- Each press = exactly 1 move attempt

### Movement logic
- The player has a `(col, row)` position (start at `(2, 2)`)
- On a directional key press:
  - Compute `next = {col: player.col + dx, row: player.row + dy}` where `(dx, dy)` is the unit direction
  - If `next.col < 1 || next.col > 18 || next.row < 1 || next.row > 13` → out of bounds, do nothing
  - Otherwise, the wall check: in this room, the only walls are the 4 edges (cols 0/19, rows 0/14). Since the bounds check already excludes edges, any tile inside the bounds is a floor tile. So the bounds check IS the wall check for V1.
  - If valid, set `player.col = next.col; player.row = next.row`
  - Update `player.facing = direction` (one of `'up' | 'left' | 'down' | 'right'`, default `'right'`)

### Render after move
- After each move, the canvas must re-render with the new player position
- The slime position is still hard-coded to `(17, 12)` and does not change
- Re-render must be fast (a single `fillRect` clear + redraw) — no flicker

### Out of scope (NOT in Stage 3)
- NO Space handling (no attack)
- NO R handling (no restart)
- NO slime movement, no slime AI, no slime tick
- NO damage, no health changes
- NO win/lose states
- NO animation between moves
- NO diagonal movement
- NO simultaneous key handling (1 key per move attempt, no held-key repeat)
- NO facing-direction visual on the player (the player is still a plain blue square; facing is stored in code only, used in Stage 5 for attack direction)
- NO Mission Control changes

### Code organization
- Keep it readable. Single `index.html` is fine.
- Suggestion: extract the render function so it can be called on demand, e.g.
  ```js
  function render() {
    // ... clear, floor, walls, slime, player, HUD, state text, controls
  }
  function movePlayer(dx, dy) {
    // ... bounds check, update position, update facing, call render()
  }
  document.addEventListener('keydown', (e) => {
    const k = e.key;
    if (k === 'w' || k === 'W' || k === 'ArrowUp')    { e.preventDefault(); movePlayer(0, -1); }
    else if (k === 's' || k === 'S' || k === 'ArrowDown')  { e.preventDefault(); movePlayer(0, 1); }
    else if (k === 'a' || k === 'A' || k === 'ArrowLeft')  { e.preventDefault(); movePlayer(-1, 0); }
    else if (k === 'd' || k === 'D' || k === 'ArrowRight') { e.preventDefault(); movePlayer(1, 0); }
  });
  render(); // initial draw
  ```
- Adapt to your own style. The structure is what matters.

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 3 brief)
- No external dependencies
- No installs
- No new files needed (single index.html)
- Update README.md if the run command changes (it should NOT — same `python3 -m http.server 8770 --bind 0.0.0.0`)
- One stage at a time
- Argus must verify: movement works, walls block, slime doesn't move, no attack, no AI, no win/lose
