# Dungeon Spark — Controls

## Input map

| Key | Action | When |
|---|---|---|
| **W** | Move up | Playing state only |
| **A** | Move left | Playing state only |
| **S** | Move down | Playing state only |
| **D** | Move right | Playing state only |
| **↑** | Move up | Playing state only (alias for W) |
| **←** | Move left | Playing state only (alias for A) |
| **↓** | Move down | Playing state only (alias for S) |
| **→** | Move right | Playing state only (alias for D) |
| **Space** | Attack (sword swing) | Playing state only, after attack cooldown |
| **R** | Restart | After win or lose state |

## Movement

- **Grid-based, discrete movement**: player moves one tile per key press
- Not free-form pixel movement
- Pressing a direction key moves the player one tile in that direction, if the destination is a floor tile (not a wall)
- Pressing a direction key into a wall = no movement (the player stays put, the input is consumed)
- Diagonal movement: NOT supported (use one axis at a time)

## Attack

- Press Space to swing the sword
- The attack hits if the slime is within the player's attack range (1 tile in the direction the player is facing)
- The attack has a cooldown of 0.4 seconds — pressing Space during cooldown does nothing
- The attack cooldown starts when the attack is initiated (regardless of hit/miss)
- The player has a "facing direction" (last movement direction or default right). The attack only hits in that direction. (Simpler than omnidirectional melee; matches the "one tile in front" model.)

## Enemy behavior

- The slime moves every 0.5 seconds (its own tick rate, separate from player)
- On each tick, the slime picks the direction (N/S/E/W) that brings it closest to the player, and moves one tile in that direction (if the destination is floor; otherwise the slime picks the next-best direction; if all blocked, the slime stays put)
- The slime damages the player on contact: at the end of each slime tick, if the slime's tile equals the player's tile, the player takes 1 damage
- The slime has no cooldown (its tick is its cycle)

## Restart

- R is only active in the "win" or "lose" end state
- Pressing R resets: player HP to full, slime HP to full, player position to start tile, slime position to start tile, state back to "playing"
- R during "playing" is a no-op (ignored) — prevents accidental restarts mid-fight

## Edge cases

- **Simultaneous key presses**: only the most recent direction is honored per tick (no diagonal)
- **Window not focused**: keys are released; no movement happens; game pauses logically until refocus
- **Space held down**: only fires once per cooldown (not auto-repeat)
- **Attack during cooldown**: silently ignored, no visual feedback needed for V1
- **Attack when no slime in range**: still costs the cooldown (so you can't spam)

## Out of scope (NOT in V1)

- Diagonal movement
- Dash / dodge
- Mouse / touch input
- Controller / gamepad
- Key remapping
- Pause key (P)
- Confirmation dialogs for restart
- Mute / volume controls
