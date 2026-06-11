---
id: RG-007-WIN-LOSE-STATES
title: Roguelike V1 — Stage 7: Win/Lose States
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: complete
priority: high
created_at: "2026-06-12T02:50:00+00:00"
updated_at: "2026-06-12T03:15:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Add game state machine: 'playing' | 'win' | 'lose'. Slime.hp=0 → 'win' + 'YOU WIN' message. Player.hp=0 → 'lose' + 'YOU DIED' message. Both stop gameplay. HP clamped to 0. NO restart, NO R key, NO menu, NO new enemies. Game server must still run at http://192.168.0.29:8770/. Mission Control stays frozen at v1.15.0."
acceptance: "(1) state variable exists with values 'playing' | 'win' | 'lose', initialized to 'playing'. (2) When slime.hp reaches 0, state = 'win' (and stays 'win' even on further attacks). (3) When player.hp reaches 0, state = 'lose' (and stays 'lose' even on further damage). (4) HP clamped at 0: slime.hp = Math.max(0, slime.hp) / player.hp = Math.max(0, player.hp). (5) 'YOU WIN' message shown when state === 'win'. (6) 'YOU DIED' message shown when state === 'lose'. (7) Slime AI (setInterval) does nothing when state !== 'playing' (early return in slimeTick). (8) Slime contact damage does nothing when state !== 'playing' (early return in applyContactDamage). (9) Player attack does nothing when state !== 'playing' (early return in playerAttack). (10) Player movement does nothing when state !== 'playing' (early return in movePlayer). (11) HUD shows current state (e.g. 'State: playing' or colored pill). (12) Final scene stays visible after end. (13) R key still does NOTHING (no restart yet, that's Stage 8). (14) NO menu, NO new enemies, NO procedural, NO inventory, NO sound. (15) NO external deps. (16) Game still serves on :8770. (17) Mission Control still frozen, still healthy."
argus_result: pass
---

## Brief
Stage 7 introduces the simplest possible end-game. The game has 3 states: 'playing', 'win', 'lose'. When slime.hp reaches 0 → 'win' + 'YOU WIN'. When player.hp reaches 0 → 'lose' + 'YOU DIED'. Both states freeze the game (no more AI, no more damage, no more attacks, no more movement). HP clamped at 0. R still does nothing — that's Stage 8.

## Acceptance details

### State variable
- `var state = 'playing';` (initial)
- Allowed values: 'playing' | 'win' | 'lose'
- Used by every gameplay function as an early-return guard

### Clamp HP at 0
- After every `slime.hp -= 1` (in playerAttack): `if (slime.hp < 0) slime.hp = 0;` or use `slime.hp = Math.max(0, slime.hp - 1)`
- After every `player.hp -= 1` (in applyContactDamage): `if (player.hp < 0) player.hp = 0;` or use `player.hp = Math.max(0, player.hp - 1)`
- The clamp + state transition can happen in the same check:
  ```js
  slime.hp = Math.max(0, slime.hp - 1);
  if (slime.hp === 0 && state === 'playing') state = 'win';
  ```
  and
  ```js
  player.hp = Math.max(0, player.hp - 1);
  if (player.hp === 0 && state === 'playing') state = 'lose';
  ```

### Early-return guards
- `movePlayer(dx, dy)`: add `if (state !== 'playing') return;` at the top
- `playerAttack()`: add `if (state !== 'playing') return;` at the top
- `slimeTick()`: add `if (state !== 'playing') return;` at the top
- `applyContactDamage()`: add `if (state !== 'playing') return;` at the top (the existing `slime.hp <= 0` guard is still there too)

### Win/Lose message
- In render(), draw a centered message based on state:
  ```js
  if (state === 'win') {
    ctx.fillStyle = 'green';
    ctx.font = 'bold 32px monospace';
    ctx.fillText('YOU WIN', 220, 240);
    ctx.font = '16px monospace';
    ctx.fillStyle = 'white';
    ctx.fillText('Slime defeated. (Stage 8 will add restart.)', 130, 270);
  } else if (state === 'lose') {
    ctx.fillStyle = 'red';
    ctx.font = 'bold 32px monospace';
    ctx.fillText('YOU DIED', 230, 240);
    ctx.font = '16px monospace';
    ctx.fillStyle = 'white';
    ctx.fillText('The dungeon claims another. (Stage 8 will add restart.)', 80, 270);
  }
  ```
- The text overlays the room but the final scene is still visible behind it
- The "(Stage 8 will add restart.)" hint is OK and honest

### HUD state display
- In the existing HUD area, add a small line showing the current state:
  - "State: playing" (white)
  - "State: WIN" (green) when state === 'win'
  - "State: LOSE" (red) when state === 'lose'
- Position: top-center or below the "DUNGEON SPARK" title

### Final scene visible
- render() always runs (there's no animation loop; render is called on player move, attack, slime tick, damage)
- After state becomes 'win' or 'lose', the slime is still drawn at its last position (slime.hp = 0 doesn't hide the slime in V1)
- After 'win', the slime stops moving but its sprite is still visible at 0 HP
- After 'lose', the player is still drawn at their last tile

### R key
- DO NOT add an R key handler
- The brief explicitly excludes restart and R
- The existing HUD placeholder text mentioning "R: restart" can stay (it's just a hint)

### Forbidden
- NO restart logic
- NO R key handler
- NO menu, NO new enemies, NO extra rooms
- NO inventory, NO sound, NO procedural
- NO score, NO level transition
- NO requestAnimationFrame / setTimeout
- NO external deps
- DO NOT change the existing player movement, playerAttack, slimeTick, or applyContactDamage functions beyond adding the early-return guard at the top
- DO NOT change the existing yellow attackFlash or red playerFlash visuals

## Code structure suggestion
```js
// Add at top:
var state = 'playing';

// In playerAttack, add as the FIRST line:
if (state !== 'playing') return;

// In playerAttack, change slime.hp -= 1 to:
slime.hp = Math.max(0, slime.hp - 1);
if (slime.hp === 0 && state === 'playing') state = 'win';

// In applyContactDamage, add as the FIRST line (after the existing slime.hp <= 0 guard):
if (state !== 'playing') return;

// In applyContactDamage, change player.hp -= 1 to:
player.hp = Math.max(0, player.hp - 1);
if (player.hp === 0 && state === 'playing') state = 'lose';

// In slimeTick, add as the FIRST line:
if (state !== 'playing') return;

// In movePlayer, add as the FIRST line:
if (state !== 'playing') return;

// In render(), add at the END (after all other draws):
if (state === 'win') {
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = 'lime';
  ctx.font = 'bold 36px monospace';
  ctx.fillText('YOU WIN', 220, 240);
  ctx.font = '16px monospace';
  ctx.fillStyle = 'white';
  ctx.fillText('Slime defeated. (Stage 8 will add restart.)', 110, 270);
} else if (state === 'lose') {
  ctx.fillStyle = 'rgba(0,0,0,0.6)';
  ctx.fillRect(0, 0, W, H);
  ctx.fillStyle = 'red';
  ctx.font = 'bold 36px monospace';
  ctx.fillText('YOU DIED', 220, 240);
  ctx.font = '16px monospace';
  ctx.fillStyle = 'white';
  ctx.fillText('The dungeon claims another. (Stage 8 will add restart.)', 70, 270);
}
```

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 7 brief)
- No external dependencies
- No installs
- One stage at a time
- Don't touch Mission Control (frozen)
- Don't add restart, R key, menu, new enemies, extra rooms
- Don't refactor unrelated systems
- Keep code simple and readable
- Argus must verify: win/lose states, HP clamping, gameplay stops, no restart, R still does nothing
