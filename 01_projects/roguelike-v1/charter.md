# Roguelike V1 — Dungeon Spark (Charter)

## Concept
A lone explorer trapped in a corrupted dungeon room. Tiny 2D top-down roguelike prototype. **V1 is one dungeon room, one slime, win/lose only.** This is not the whole game.

## V1 Scope
- Player moves around one dungeon room
- Player cannot walk through walls
- One corrupted slime enemy
- Player can attack (Space)
- Enemy can damage player
- Player has HP
- Enemy has HP
- Win = slime dead
- Lose = HP reaches 0
- Player can restart (R)

## V1 Excludes
Inventory · Procedural generation · Multiple rooms · Multiple levels · Save/load · Shop · Equipment · Complex animations · Sound/music · Story campaign · Multiplayer · Online features · Mobile export

## Technology
- HTML5 Canvas + JavaScript
- Run: `python3 -m http.server 8770 --bind 0.0.0.0`
- Open: `http://192.168.0.29:8770/`
- Controls: WASD/Arrows = move, Space = attack, R = restart

## Operating rules
- Task file first. Events first. No coding before the task exists.
- Thor coordinates. Forge builds. Argus verifies.
- One stage at a time. No fake progress.
- Mission Control monitors. Does not interfere.
- Memory entry 010 still applies: hero mode = data problem.
