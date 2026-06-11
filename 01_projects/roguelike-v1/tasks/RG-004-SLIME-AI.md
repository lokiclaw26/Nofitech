---
id: RG-004-SLIME-AI
title: Roguelike V1 — Stage 4: Slime AI Movement
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: complete
priority: high
created_at: "2026-06-12T01:10:00+00:00"
updated_at: "2026-06-12T01:35:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Slime moves every 500ms toward the player using simple greedy Manhattan chase. One tile per tick. Walls + boundaries respected. NO combat, NO damage, NO attack, NO HP changes, NO win/lose, NO restart, NO extra enemies, NO pathfinding. Game server must still run at http://192.168.0.29:8770/. Mission Control stays frozen at v1.15.0."
acceptance: "(1) setInterval(slimeTick, 500) added to index.html. (2) slimeTick() picks a cardinal direction (up/down/left/right) that reduces Manhattan distance to the player. (3) Move is exactly 1 tile. (4) Wall/edge check: if next tile is out of bounds or is a wall, slime does NOT move (or picks another valid direction). (5) NO damage: even if slime.col === player.col && slime.row === player.row, no HP change. (6) NO Space handler added (no attack). (7) NO R handler (no restart). (8) NO win/lose state. (9) NO extra enemies. (10) NO pathfinding (just greedy Manhattan). (11) No setTimeout/0 in a loop. (12) NO external dependencies. (13) Game still serves on http://192.168.0.29:8770/. (14) Mission Control still frozen, still healthy."
argus_result: pass
---

## Brief
Stage 4 = the slime comes alive. Simple greedy Manhattan chase, 500ms tick, 1 tile per tick, walls block, boundaries block. NO combat — if the slime's next tile would put it on the player, it must NOT enter that tile (NO damage). NO attack, no HP changes, no win/lose, no restart, no extra enemies, no pathfinding, no animations beyond the position update.

## Acceptance details

### Slime AI tick
- 500ms interval, started ONCE at page load (clearable, but for V1 it just runs forever)
- A `slimeTick()` function that:
  1. Computes `dx = player.col - slime.col`, `dy = player.row - slime.row`
  2. Builds a list of candidate directions that REDUCE Manhattan distance:
     - If `dx > 0` and the tile to the right is in bounds and NOT a wall and NOT the player's tile → candidate "right"
     - If `dx < 0` and the tile to the left is in bounds and NOT a wall and NOT the player's tile → candidate "left"
     - If `dy > 0` and the tile below is in bounds and NOT a wall and NOT the player's tile → candidate "down"
     - If `dy < 0` and the tile above is in bounds and NOT a wall and NOT the player's tile → candidate "up"
  3. **CRITICAL**: if all candidates would put the slime ON the player, the slime does NOT move this tick (no contact yet — that's Stage 5+)
  4. If at least one candidate is valid, pick one (tie-breaking: prefer the direction matching the player's last move; if still tied, prefer up > right > down > left per technical-values.md)
  5. Update `slime.col`/`slime.row` and call `render()`

### Wall + boundary check
- The 4 walls are the edges (col 0, col 19, row 0, row 14). Interior (cols 1-18, rows 1-13) is all floor.
- For V1, the bounds check `1 <= nextCol <= 18 && 1 <= nextRow <= 13` IS the wall check (no inner walls in the V1 room).
- Combined with "not the player's tile" to keep the slime off the player for now.

### HUD optional
- The brief says "HUD can show 'Slime is chasing' or similar if simple"
- You may add a small line: "Slime is chasing..." in the center HUD area, OR leave the HUD unchanged
- **Recommended**: leave the HUD unchanged for this stage. The slime's position updating IS the visual feedback. Keep it simple.

### Forbidden features
- NO `player.hp = player.hp - 1` (no damage)
- NO `slime.hp = slime.hp - 1` (no enemy HP change)
- NO `state = 'win' | 'lose' | 'playing' | 'title'` (no state machine)
- NO Space handler (no attack)
- NO R handler (no restart)
- NO second slime or other enemy
- NO `setTimeout` recursive (only one `setInterval`)
- NO A* / BFS / Dijkstra (only greedy Manhattan)
- NO `requestAnimationFrame` (we don't need a render loop — the existing `render()` is fine, called only on slime tick and on player move)
- NO external deps

## Code structure suggestion
```js
var slime = { col: 17, row: 12, hp: 3 }; // NO LONGER const — slime is now mutable
var player = { col: 2, row: 2, facing: 'right', hp: 5, lastDir: 'right' };

function inBoundsAndFree(c, r) {
  return c >= 1 && c <= 18 && r >= 1 && r <= 13
      && !(c === player.col && r === player.row);
}

function slimeTick() {
  var dx = player.col - slime.col;
  var dy = player.row - slime.row;
  var candidates = [];
  if (dx > 0 && inBoundsAndFree(slime.col + 1, slime.row)) candidates.push({dc: 1, dr: 0, dir: 'right'});
  if (dx < 0 && inBoundsAndFree(slime.col - 1, slime.row)) candidates.push({dc: -1, dr: 0, dir: 'left'});
  if (dy > 0 && inBoundsAndFree(slime.col, slime.row + 1)) candidates.push({dc: 0, dr: 1, dir: 'down'});
  if (dy < 0 && inBoundsAndFree(slime.col, slime.row - 1)) candidates.push({dc: 0, dr: -1, dir: 'up'});
  if (candidates.length === 0) return; // blocked, do nothing this tick
  // pick candidate matching player.lastDir, else up > right > down > left
  var order = {up: 0, right: 1, down: 2, left: 3};
  var pick = candidates.sort(function(a, b) {
    return order[a.dir] - order[b.dir];
  })[0];
  // (simpler: always prefer up > right > down > left per technical-values.md, ignore lastDir for now)
  slime.col += pick.dc;
  slime.row += pick.dr;
  render();
}

setInterval(slimeTick, 500);
```

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 4 brief)
- No external dependencies
- No installs
- One stage at a time
- Don't touch Mission Control (frozen)
- Don't add combat/damage/attack/win/lose/restart
- Don't refactor unrelated systems (keep the existing player movement + render as-is)
- Keep code simple and readable
- Argus must verify: slime moves on 500ms tick, only 1 tile per tick, walls block, boundaries block, no damage, no attack, no HP changes, no win/lose/restart, no extra enemies
