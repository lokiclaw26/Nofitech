---
id: RG-008-RESTART
title: Roguelike V1 — Stage 8: Restart
project: roguelike-v1
created_by: nofi
assigned_to: forge
status: complete
priority: high
created_at: "2026-06-12T03:25:00+00:00"
updated_at: "2026-06-12T03:50:00+00:00"
current_stage: ship
blocker: ""
data_source: real
description: "Add R key restart. resetGame() resets everything to starting state. R only works in 'win' or 'lose' state (no-op during 'playing'). 'Press R to restart' hint on win/lose overlays. NO menu, NO new enemies, NO new rooms, NO scoring, NO sound, NO polish, NO save/load. Game server must still run at http://192.168.0.29:8770/. Mission Control stays frozen at v1.15.0."
acceptance: "(1) resetGame() function exists. (2) R key handler added to keydown; if (state === 'win' || state === 'lose') { e.preventDefault(); resetGame(); } — R during 'playing' is a no-op. (3) resetGame() sets: state = 'playing', player.hp = 5, player.col = 2, player.row = 2, player.facing = 'right', slime.hp = 3, slime.col = 17, slime.row = 12, lastAttackTime = 0, attackFlash = {col:-1,row:-1,until:0}, playerFlash = {col:-1,row:-1,until:0}. (4) Calls render() at the end so the new state is visible. (5) 'Press R to restart' hint added to both YOU WIN and YOU DIED overlays. (6) Existing keydown handler still works for WASD/Arrows/Space. (7) NO new gameplay, NO new enemies, NO menu, NO scoring, NO sound, NO save/load, NO new polish. (8) NO external deps. (9) Game still serves on :8770. (10) Mission Control still frozen, still healthy."
argus_result: pass
kanban_status: done
---

## Brief
Stage 8 wires the R key to a `resetGame()` function. The function is only callable from 'win' or 'lose' states (R during 'playing' does nothing). On reset, every gameplay variable returns to its starting value. After reset, all previous gameplay (movement, slime AI, attack, contact damage) works again. The YOU WIN / YOU DIED overlays get a simple "Press R to restart" hint. This is the final functional stage — no new gameplay, no new features, just the reset.

## Acceptance details

### resetGame() function
```js
function resetGame() {
  state = 'playing';
  player.hp = 5;
  player.col = 2;
  player.row = 2;
  player.facing = 'right';
  slime.hp = 3;
  slime.col = 17;
  slime.row = 12;
  lastAttackTime = 0;
  attackFlash = { col: -1, row: -1, until: 0 };
  playerFlash = { col: -1, row: -1, until: 0 };
  render();
}
```

### R key handler
- Add to the existing keydown handler (after the Space branch):
  ```js
  } else if (e.key === 'r' || e.key === 'R') {
    if (state === 'win' || state === 'lose') {
      e.preventDefault();
      resetGame();
    }
  }
  ```
- If state === 'playing' → the handler is a no-op (no preventDefault, no resetGame, nothing happens)
- If state is something else (shouldn't happen) → also no-op

### "Press R to restart" hint
- Modify the existing YOU WIN overlay in render() to include the hint:
  ```js
  ctx.fillText('Slime defeated. Press R to restart.', 100, 270);
  ```
  (replacing the old "Slime defeated. (Stage 8 will add restart.)")
- Modify the existing YOU DIED overlay similarly:
  ```js
  ctx.fillText('The dungeon claims another. Press R to restart.', 60, 270);
  ```

### Forbidden
- NO new gameplay (no new weapons, no new player abilities, no new slime types)
- NO new enemies
- NO new rooms
- NO menu
- NO scoring
- NO sound
- NO save/load
- NO visual polish (no animations, no fade-ins, no fancy transitions)
- NO state machine additions (state is still 'playing'/'win'/'lose')
- NO setTimeout/0 in a loop (the existing setInterval for slimeTick keeps running; it just early-returns when state !== 'playing')
- NO requestAnimationFrame
- NO external deps
- DO NOT change the existing player movement, playerAttack, slimeTick, or applyContactDamage functions

## Code structure suggestion
```js
// Add resetGame() function near the other top-level functions (after applyContactDamage):

function resetGame() {
  state = 'playing';
  player.hp = 5;
  player.col = 2;
  player.row = 2;
  player.facing = 'right';
  slime.hp = 3;
  slime.col = 17;
  slime.row = 12;
  lastAttackTime = 0;
  attackFlash = { col: -1, row: -1, until: 0 };
  playerFlash = { col: -1, row: -1, until: 0 };
  render();
}

// In the keydown handler, AFTER the Space branch:
} else if (e.key === 'r' || e.key === 'R') {
  if (state === 'win' || state === 'lose') {
    e.preventDefault();
    resetGame();
  }
}

// In render(), update the YOU WIN and YOU DIED overlays' hint lines:
// YOU WIN: replace "Slime defeated. (Stage 8 will add restart.)" with "Slime defeated. Press R to restart."
// YOU DIED: replace "The dungeon claims another. (Stage 8 will add restart.)" with "The dungeon claims another. Press R to restart."
```

## Constraints (LOCKED from memory 002, 010, and NOFI Stage 8 brief)
- No external dependencies
- No installs
- One stage at a time
- Don't touch Mission Control (frozen)
- Don't add new gameplay, new enemies, new rooms, menu, scoring, sound, save/load, polish
- Don't refactor unrelated systems
- Keep code simple and readable
- Argus must verify: R works only in win/lose, resetGame() resets everything, hint appears, gameplay resumes after reset, no new features
