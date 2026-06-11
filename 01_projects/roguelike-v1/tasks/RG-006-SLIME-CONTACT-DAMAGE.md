---
id: RG-006-SLIME-CONTACT-DAMAGE
title: Roguelike V1 — Stage 6: Slime Contact Damage
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: complete
priority: high
created_at: "2026-06-12T02:15:00+00:00"
updated_at: "2026-06-12T02:40:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Slime damages the player on contact. 1 HP per 500ms tick when slime is adjacent (or would overlap with player). Red flash visual. Dead slime (hp <= 0) does NOT damage. NO win/lose, NO restart, NO game over, NO extra enemies, NO inventory, NO sound, NO procedural generation. Game server must still run at http://192.168.0.29:8770/. Mission Control stays frozen at v1.15.0."
acceptance: "(1) Slime damage fires from the slime AI tick (every 500ms), not faster. (2) Damage amount: exactly 1 HP per valid damage tick. (3) Damage condition: slime is adjacent to player (Manhattan distance == 1) OR slime attempted to enter the player's tile. (4) If slime.hp <= 0, slime does NOT damage player. (5) Red flash visual when player takes damage (e.g. ctx.fillStyle='red', ctx.fillRect on player's tile, lasts ~200ms). (6) HUD 'Player HP: 5' updates automatically. (7) Slime still chases the player. (8) Player attack from Stage 5 still works. (9) Slime CAN now enter the player's tile (inBoundsAndFree no longer excludes the player's tile), but only if the slime has HP > 0. (10) NO state machine. (11) NO R handler. (12) NO game over screen. (13) NO extra enemies. (14) NO inventory/sound/procedural. (15) NO external deps. (16) Game still serves on :8770. (17) Mission Control still frozen, still healthy."
argus_result: pass
---

## Brief
Stage 6 makes the slime dangerous. When the slime's Manhattan distance to the player is 1 (adjacent), or when the slime attempts to step into the player's tile, the player takes 1 HP. Damage fires from the slime AI tick (every 500ms), not faster. Dead slimes (HP ≤ 0) do not damage. A red flash provides visual feedback. NO win/lose, NO restart, NO game over, NO extra enemies.

## Acceptance details

### Damage trigger
- Computed inside `slimeTick()` (the 500ms interval), AFTER the slime has decided its move (or not moved)
- Damage condition (any of these triggers 1 damage):
  1. After the slime's attempted move, the slime is on the player's tile (slime.col === player.col && slime.row === player.row) — only if slime.hp > 0
  2. OR: slime is adjacent to player after the tick (Manhattan distance == 1) — only if slime.hp > 0
- For V1, the simpler rule: **after slimeTick decides the slime's new position, if `slime.hp > 0` AND the slime's tile is adjacent-or-equal to the player's tile, deal 1 damage**
- This naturally handles both "slime entered player's tile" and "slime is adjacent" with one check

### Slime can now enter the player's tile
- The existing `inBoundsAndFree(c, r)` from Stage 4 rejects the player's tile
- For V1 contact damage, we need the slime to BE ABLE to enter the player's tile (the slime has to "reach" the player)
- **Recommended**: instead of fully removing the player-tile guard, change `inBoundsAndFree` to allow the player's tile for the slime's AI movement but still reject out-of-bounds
- The simplest change: in `slimeTick`, when computing candidates, allow the slime to step onto the player's tile (so the slime's next position can be the player's). The damage logic happens AFTER the move.
- Alternative: keep the guard, but if the slime's next move is the player's tile, the slime still moves there (overrides the guard for the player's tile only). This is the cleanest.
- Even simpler: drop the `!== player.col/row` check from `inBoundsAndFree`. Then `inBoundsAndFree(c, r)` only checks bounds. The slime can now enter the player's tile, and damage is applied after.

### Damage amount + cooldown
- Exactly 1 HP per damage event
- Cooldown = 500ms (because the damage check is inside slimeTick, which runs every 500ms)
- If the slime is adjacent every tick, the player takes 1 damage every 500ms

### Damage feedback (red flash)
- Set a global `playerFlash = { col: player.col, row: player.row, until: now + 200 }` on each damage
- In render(), after drawing the player, check `if (Date.now() < playerFlash.until) { ctx.fillStyle = 'red'; ctx.fillRect(playerFlash.col * TILE, playerFlash.row * TILE, TILE, TILE); }` — drawn AFTER the player so the red overlays it
- 200ms is shorter than the 500ms tick, so the flash is visible between ticks
- Or alternatively, use a CSS body flash (red background briefly). The canvas-overlay approach is simpler and matches the existing yellow-flash pattern.

### Dead slime damage block
- At the top of the damage check: `if (slime.hp <= 0) return;` — slime with 0 HP cannot damage the player
- This means after the player kills the slime (3 attacks from Stage 5), the slime stops being a threat
- The slime still renders at 0 HP (no visual change yet — the player can still see it, just inert)

### Forbidden
- NO state machine (no `state = 'win'/'lose'/'playing'/'title'`)
- NO R handler
- NO game over screen
- NO "You died" text overlay
- NO second slime or other enemy
- NO inventory/sound/procedural
- NO requestAnimationFrame / setTimeout (the setInterval(500) for slimeTick is the only timer)
- NO external deps
- DO NOT change playerAttack from Stage 5
- DO NOT change the slime's HP initial value or any HUD reading

## Code structure suggestion
```js
// Add at top:
var playerFlash = { col: -1, row: -1, until: 0 };

// In slimeTick, AFTER the slime's move decision (or in a separate helper):
function applyContactDamage() {
  if (slime.hp <= 0) return; // dead slimes do not damage
  // After slime has moved (or not), check if slime is on or adjacent to player
  var dx = player.col - slime.col;
  var dy = player.row - slime.row;
  var dist = Math.abs(dx) + Math.abs(dy);
  if (dist <= 1) { // adjacent or same tile
    player.hp -= 1;
    playerFlash = { col: player.col, row: player.row, until: Date.now() + 200 };
  }
}

// Call applyContactDamage() at the end of slimeTick().

// In render(), after drawing the player:
if (Date.now() < playerFlash.until) {
  ctx.fillStyle = 'red';
  ctx.fillRect(playerFlash.col * TILE, playerFlash.row * TILE, TILE, TILE);
}
```

## About the inBoundsAndFree change
The cleanest change to `inBoundsAndFree`:
- Remove the `!(c === player.col && r === player.row)` check
- Now the slime can step onto the player's tile
- Damage is applied after the move, so the slime's position can equal the player's position

If you'd rather keep the guard, you can also do this: in `slimeTick`, if the chosen candidate is the player's tile, override the check and move there anyway. But removing the guard from `inBoundsAndFree` is simpler.

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 6 brief)
- No external dependencies
- No installs
- One stage at a time
- Don't touch Mission Control (frozen)
- Don't add win/lose, restart, game over
- Don't refactor unrelated systems
- Keep code simple and readable
- Argus must verify: contact damage works, 1 HP per tick, dead slime does not damage, red flash appears, HUD updates, no win/lose/restart/game-over
