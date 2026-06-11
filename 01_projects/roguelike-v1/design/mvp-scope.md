# Dungeon Spark — MVP Scope (V1)

## In scope (this prototype ONLY)

### One room
- A single rectangular dungeon room
- Walls around the 4 edges
- Open floor in the middle
- No corridors, no doors, no other rooms

### One player
- A blue square (placeholder sprite OK)
- Spawns in one corner
- Has HP
- Cannot pass through walls
- Can move in 4 directions
- Can attack

### One enemy: the corrupted slime
- A red/purple square (placeholder sprite OK)
- Spawns in the opposite corner from the player (or center)
- Has HP
- Moves slowly toward the player
- Damages the player on contact
- Has NO ranged attack, NO projectiles, NO special abilities

### Combat
- Player attack: Space key, only when within range
- Enemy attack: on contact (when within range of player)
- Cooldown on player attack (prevents spam)
- No enemy attack cooldown (just on-contact damage)
- Damage values are small enough that the fight takes 3–8 exchanges (not 1-shot kills, not endless)

### UI
- Player HP number (top-left)
- Enemy HP number (top-right)
- Game state text (center): "DUNGEON SPARK — WASD/Arrows: move, Space: attack, R: restart"
- End-of-run text: "YOU WIN" (green) or "YOU DIED" (red)
- Restart prompt: "Press R to restart"

### Win/Lose
- Win: enemy HP = 0
- Lose: player HP = 0
- Either: show end text, wait for R

## Out of scope (NOT in V1)

| Excluded | Why |
|---|---|
| Procedural generation | Adds randomness that complicates testing. V1 is a fixed room. |
| Inventory | No items to collect. |
| Items / pickups | No loot in the room. |
| Shop | No economy. |
| Equipment | No weapons/armor. |
| Multiple enemies | One slime only. |
| Multiple rooms | One room only. |
| Multiple levels / floors | Single room. |
| Save / load | Single run, no persistence. |
| Sound / music | Silent prototype. |
| Complex animation | Squares only. |
| Full menu system | No main menu, no pause, no settings. |
| Story campaign | No narrative beyond the room. |
| Multiplayer | Single player. |
| Online features | None. |
| Mobile / touch export | Desktop browser only. |
| Procedural enemy variation | One slime type only. |

## Scope-gate rule (HARD)

If a feature is not explicitly listed under "In scope", it is **NOT** in V1. Adding it requires a new scope document, a new MVP version number (V2, V3, ...), and NOFI approval.

## Core loop (1 sentence)

Move around the room, attack the slime when close, avoid the slime, manage HP, win or lose, press R to restart.
