# RG-012 — Better Visual Style

**id:** RG-012
**title:** Better Visual Style
**project:** roguelike-v1
**agent:** forge
**status:** complete
**priority:** high
**created:** 2026-06-13
**updated:** 2026-06-13
**description:** Pure cosmetic stage. Improve the look of floor, walls, pillars, player, slime, HUD, and title/instructions. NO new gameplay, NO new state, NO new mechanic.
**acceptance:**
- Floor: 2-tone checker `#2a2a2a`/`#3a3a3a` on `(col+row)%2`: yes
- Walls: base `#1a1a1a` + 1px `#333` inner-edge highlight on 4 sides: yes
- Pillars: base `#555` + 24x24 `#444` carved inset: yes
- Player: 4 fillRect calls (body, helmet, eye, sword in facing direction): yes
- Slime: 1 arc + 1 fillRect highlight (blob + shine): yes
- HUD top bar y=0..26 (backdrop, HP rects, slime HP rects, title with shadow, state indicator): yes
- HUD bottom bar y=H-20..H (backdrop, controls text): yes
- Old center title and old bottom controls REMOVED: yes
- Existing v0.1 + Stage 11 mechanics all work: yes (13 functions/handlers byte-identical to Stage 11)
- Game still runs at `http://192.168.0.29:8770/`: yes (HTTP 200)
- No console errors: yes (node --check PASS)
- No procedural, no door, no potion, no new enemies, no new rooms, no sound, no images, no fonts, no external libs: yes (12 forbidden-additions categories = 0)
- Git commit created after Argus pass: yes
**evidence:**
- `01_projects/roguelike-v1/tasks/RG-012-BETTER-VISUAL-STYLE.md` (this file, updated to complete)
- `00_company_os/events.jsonl` (192 → 196 lines, +4 closure events for RG-012)
- `00_company_os/04_agents/state.json` (3 agents idle, awaiting Stage 13)
- `00_company_os/04_agents/logs/2026-06-13/forge-rg012-1781214686.md` (Forge implementation report)
- `00_company_os/04_agents/logs/2026-06-13/argus-rg012-1781214686.md` (Argus verification report, 31/31 PASS)
- `01_projects/roguelike-v1/code/index.html` (477 lines, +84 from Stage 11's 393)
- Git commit: pending (created at end of Stage 12)
**blockers:** None
**argus_result:** pass
**data_source:** real
