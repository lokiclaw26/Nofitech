# Dungeon Spark — Technical Values (V1)

All values are concrete. No ranges. No TBD. These are the numbers Forge will use in Stage 2 (technical skeleton).

## Render

| Value | Number |
|---|---|
| Canvas size | **640 × 480** pixels |
| Tile size | **32 × 32** pixels |
| Grid dimensions | **20 × 15** tiles (640÷32 = 20, 480÷32 = 15) |
| Render target | `<canvas id="game">` in `01_projects/roguelike-v1/code/index.html` |
| Render style | `fillRect` only (no images, no sprites, no paths) |
| Frame rate target | 60 fps via `requestAnimationFrame` |

## Map (the single room)

| Value | Number |
|---|---|
| Room shape | Rectangle, walls on the 4 edges |
| Floor tiles | All interior tiles (cols 1-18, rows 1-13) are floor |
| Wall tiles | All edge tiles (col 0, col 19, row 0, row 14) are walls |
| Inner walls | NONE (one open room) |
| Player spawn tile | **(2, 2)** — top-left area |
| Slime spawn tile | **(17, 12)** — bottom-right area |
| Total tiles | 20 × 15 = 300 tiles (40 wall + 260 floor) |

## Player

| Value | Number |
|---|---|
| Visual | Blue square (`fillStyle = "blue"`, 32×32) |
| Starting HP | **5** |
| Default facing direction | right |
| Movement | Discrete, one tile per WASD/Arrow key press |
| Move cooldown | None (player can press again immediately) |
| Damage taken per slime contact | **1** HP |
| HP displayed as | Integer (5, 4, 3, 2, 1, 0) |
| Death | At HP = 0 → state = "lose" |

## Enemy (corrupted slime)

| Value | Number |
|---|---|
| Visual | Red/purple square (`fillStyle = "rgb(180,40,180)"`, 32×32) |
| Starting HP | **3** |
| Movement tick | **500 ms** (2 ticks per second) |
| Movement AI | Greedy: pick the N/S/E/W direction that minimizes Manhattan distance to the player, move 1 tile (if floor) |
| Tie-breaking | When 2+ directions are equally close, prefer the one that moves in the player's last-moved direction; if still tied, prefer N, then E, then S, then W (deterministic) |
| Damage on contact | 1 HP per tick (if same tile as player at end of tick) |
| Death | At HP = 0 → state = "win" |

## Combat

| Value | Number |
|---|---|
| Attack key | Space |
| Attack range | **1 tile in the player's facing direction** |
| Attack damage | **1 HP** (per hit) |
| Attack cooldown | **400 ms** (0.4 seconds) |
| Attack visual | A small yellow square appears in the attack direction for the duration of the cooldown (so the player can see the swing) |
| Slime attack | On contact (see Enemy), no separate cooldown beyond the tick rate |
| No friendly fire | Slime doesn't damage itself |
| No invincibility frames | V1 has no i-frames; if the slime is in your tile, you take damage each tick |

## Game state

| State | Entered when | Displayed text (centered) | Accepts input |
|---|---|---|---|
| `title` | Page load | "DUNGEON SPARK — WASD/Arrows: move, Space: attack, R: restart — Press any key" | Any key → `playing` |
| `playing` | From `title` (any key) or from `win`/`lose` (R) | (empty or minimal HUD) | WASD/Arrows, Space |
| `win` | Slime HP = 0 | "YOU WIN — Slime defeated. Press R to restart." | R only |
| `lose` | Player HP = 0 | "YOU DIED — The dungeon claims another. Press R to restart." | R only |

## HUD (top of canvas)

- Top-left: `Player HP: 5` (updates on damage)
- Top-right: `Slime HP: 3` (updates on attack)
- Use `<canvas>` text rendering (`fillText`, font `16px monospace`)

## Restart behavior

- Trigger: R key in `win` or `lose` state
- Resets: player HP=5, slime HP=3, positions to spawn, state=`playing`, attack cooldown=0
- Resets: nothing else (no animation, no transition)
- Pressing R in `playing` state = no-op (ignored)
- Pressing R in `title` state = no-op (page just loaded)

## Run loop

```
init() → state = "title"
loop() (60fps):
  if state == "playing":
    handleInput()  // process queued key events
    updateSlime()  // every 500ms: slime AI tick
    checkCollisions()  // contact damage
    checkWinLose()
  render()  // always: draw room, entities, HUD, state text
```

## Files (Stage 2 will create)

- `01_projects/roguelike-v1/code/index.html` — the full game (HTML + JS in one file, no separate JS file for V1)
- `01_projects/roguelike-v1/code/README.md` — how to run it
- The HTML loads no external resources. No images, no fonts, no libraries. Pure stdlib Canvas API.

## Out of scope (NOT in V1)

- Delta time / fixed timestep
- Sprite loading or asset pipeline
- Audio (no AudioContext, no <audio>)
- Multiplayer / WebSocket
- Save/load (localStorage not used)
- Settings menu
- Frame rate counter
- Debug overlay
- Mobile / touch events
- Responsive scaling (canvas is fixed 640×480)
- High-DPI / devicePixelRatio handling
