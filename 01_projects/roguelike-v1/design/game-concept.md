# Dungeon Spark — Game Concept

## Theme
A lone explorer trapped in a corrupted dungeon room. The walls are damp, the floor is cracked stone, and a corrupted slime pulses in the center of the chamber. The explorer must fight or be consumed.

## Player fantasy
"You are alone, hurt, and cornered. Beat the slime or be absorbed."

## Mood
- Tense and intimate (one room, one enemy, no distractions)
- Old-school dungeon crawl (no fancy art — colored squares are fine)
- Quick loop (a run takes 30–90 seconds)

## Narrative arc (within the prototype)
- **Start**: explorer trapped in the room. Slime stirs in the center. Player HP at full. Slime HP at full.
- **Mid**: player and slime maneuver around the room. Walls block movement. Combat happens in close range. HP ticks down on hit.
- **End**: one of two outcomes — slime defeated (win) or explorer defeated (lose). Press R to restart in the same room with full HP.

## What makes it feel like a real dungeon (not a tech demo)
- **Walls that block movement** (collision). The room must feel enclosed.
- **An enemy that responds to your position** (the slime chases). Without this, it's a target dummy.
- **Real HP tracking** visible on screen. Without numbers, the player can't decide when to be aggressive.
- **A restart that works** (R key resets the room). Without this, a single bad run ends the demo.
- **A visible state** (title / playing / win / lose). Without this, the player doesn't know when they're done.

## Out of concept (re-confirmed)
This is NOT a roguelike proper. No procedural generation, no perma-death meta-progression, no run history. It's a single self-contained fight in a single room. Calling it "Roguelike V1" means it's the first in a series — not that it has roguelike features yet.
