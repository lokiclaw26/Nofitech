---
id: RG-005-PLAYER-ATTACK
title: Roguelike V1 — Stage 5: Basic Player Attack
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: done
priority: high
created_at: "2026-06-12T01:45:00+00:00"
updated_at: "2026-06-12T02:05:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Add Space key attack. Player attacks the adjacent tile in their facing direction. 1 damage to slime, 400ms cooldown, yellow square visual feedback. Slime HP can reach 0 but no win state. NO contact damage, NO player damage, NO win/lose/restart, NO extra enemies, NO inventory, NO sound, NO procedural generation. Game server must still run at http://192.168.0.29:8770/. Mission Control stays frozen at v1.15.0."
acceptance: "(1) Space key added to keydown handler. (2) player.facing is updated by every move (already in place from Stage 3). (3) Attack targets tile (player.col + dx, player.row + dy) where (dx, dy) comes from player.facing. (4) Attack hits ONLY the adjacent facing tile (no diagonal, no through-wall). (5) If slime is in that target tile, slime.hp -= 1. (6) 400ms cooldown: a setInterval checks elapsed time, or a simple 'now - lastAttack >= 400' guard in the handler. (7) Visual: draw a yellow square (TILE x TILE) on the target tile for the duration of the cooldown. (8) HUD 'Slime HP: 3' updates automatically as slime.hp changes (already wired). (9) Slime AI keeps running. (10) Player movement keeps working. (11) NO player.hp writes. (12) NO contact damage (slime does NOT damage player on tile overlap). (13) NO win/lose state machine. (14) NO R handler. (15) NO extra enemies. (16) NO inventory/sound/procedural. (17) NO external deps. (18) Game still serves on :8770. (19) Mission Control still frozen, still healthy."
argus_result: pass
---

## Brief
Stage 5 adds the player's attack. Space triggers a 1-damage swing in the player's facing direction, hits only the adjacent tile, has a 400ms cooldown, and shows a yellow square so the player can see the swing. The slime keeps chasing and can lose HP, but there's no win condition yet — if slime.hp reaches 0, the slime stays visible at 0 HP (no full win screen). Stage 6+ adds contact damage, win/lose, restart.

## Acceptance details

### Attack input
- Add Space to the existing keydown handler (or a new `if (e.key === ' ')` branch)
- `e.preventDefault()` to stop Space from scrolling the page
- Only triggers the attack if cooldown is ready

### Cooldown mechanism
Two options, both fine:
1. **Time-based guard**: `if (now - lastAttackTime < 400) return;` at the start of the attack function. Then `lastAttackTime = now;` after a successful attack. The simplest approach.
2. **Stale timestamp**: set `attackCooldownUntil = now + 400;` and check `now < attackCooldownUntil`.

Use option 1. The variable `lastAttackTime` is initialized to 0 (so the first attack is always ready).

### Attack target calculation
- Convert `player.facing` (a string: 'up'/'down'/'left'/'right') to a unit vector `(dx, dy)`:
  - 'right' → (1, 0)
  - 'left' → (-1, 0)
  - 'down' → (0, 1)
  - 'up' → (0, -1)
- Target tile: `(player.col + dx, player.row + dy)`

### Bounds + hit check
- If target tile is out of bounds (col<1, col>18, row<1, row>13) → wall, do nothing
- If `target.col === slime.col && target.row === slime.row` → hit: `slime.hp -= 1`
- Otherwise → miss, just play the visual

### Visual feedback
- Set a global `attackFlash` object: `{col: targetCol, row: targetRow, until: now + 400}`
- The render() function draws a yellow square on that tile (over the slime or empty) for the duration
- If `now < attackFlash.until`, draw; otherwise don't draw
- If a new attack happens during an existing flash, just overwrite `attackFlash` (last attack wins)
- Suggested: in the render() function, after drawing the slime, check `if (now < attackFlash.until) { ctx.fillStyle = 'yellow'; ctx.fillRect(attackFlash.col * TILE, attackFlash.row * TILE, TILE, TILE); }`

### HUD update
- The existing `'Slime HP: ' + slime.hp` fillText already shows the new value. No additional code needed for HUD updates — just by reading slime.hp, the next render shows the new value.

### Forbidden
- NO player.hp writes (no contact damage)
- NO state machine (`state = 'win'/'lose'/'playing'/'title'`)
- NO R handler
- NO second slime or other enemy
- NO inventory/sound/procedural
- NO external deps
- NO refactor of player movement, slime AI, or render beyond what's listed

## Code structure suggestion
```js
var lastAttackTime = 0;
var attackFlash = { col: -1, row: -1, until: 0 };

function facingToDir(f) {
  if (f === 'right') return { dx:  1, dy:  0 };
  if (f === 'left')  return { dx: -1, dy:  0 };
  if (f === 'down')  return { dx:  0, dy:  1 };
  if (f === 'up')    return { dx:  0, dy: -1 };
  return { dx: 0, dy: 0 };
}

function playerAttack() {
  var now = Date.now();
  if (now - lastAttackTime < 400) return; // cooldown
  lastAttackTime = now;
  var d = facingToDir(player.facing);
  var tc = player.col + d.dx;
  var tr = player.row + d.dy;
  // bounds = walls
  if (tc < 1 || tc > 18 || tr < 1 || tr > 13) {
    // attacked a wall — show flash on player's own tile? or no flash? pick one:
    // option A: no flash (clean)
    // option B: flash on player tile (still shows the swing)
    return; // option A
  }
  attackFlash = { col: tc, row: tr, until: now + 400 };
  // hit check
  if (tc === slime.col && tr === slime.row) {
    slime.hp -= 1;
  }
  render();
}

// In keydown handler, add:
else if (e.key === ' ') { e.preventDefault(); playerAttack(); }

// In render(), after drawing slime:
if (Date.now() < attackFlash.until) {
  ctx.fillStyle = 'yellow';
  ctx.fillRect(attackFlash.col * TILE, attackFlash.row * TILE, TILE, TILE);
}
```

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 5 brief)
- No external dependencies
- No installs
- One stage at a time
- Don't touch Mission Control (frozen)
- Don't add contact damage, win/lose, restart, extra enemies
- Don't refactor unrelated systems (preserve player movement, slime AI, render as-is, just add the new bits)
- Keep code simple and readable
- Argus must verify: Space triggers attack, facing-driven target, 1 damage, 400ms cooldown, yellow visual, HUD updates, no contact damage, no win/lose/restart
