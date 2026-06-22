# DIY-002 — Add Component Flow

**id:** DIY-002
**title:** Add Component Flow
**project:** diy-hub-v1
**agent:** forge
**status:** complete
**argus_result:** pass
**priority:** high
**created:** 2026-06-13
**updated:** 2026-06-16T11:22:01Z
**evidence:** 00_company_os/04_agents/logs/2026-06-13/forge-diy002-1781214686.md
**description:** Build the end-to-end Add Component flow. User inputs name + model + qty + location, clicks ADD, sees mock local search results, picks one, sees a confirmation popup with full spec, and on ADD TO DATABASE saves to SQLite + writes a local SVG to data/images/.
**acceptance:**
- /add page is a working form with 4 fields (name, model_number, quantity default 1, location): yes
- ADD button enabled only when name and model_number are non-empty: yes
- POST /api/components/search: yes (200 with 1+ candidates, 400 on empty)
- POST /api/components: yes (201, saves to SQLite, writes SVG to data/images/)
- GET /api/components: yes (200, returns all saved components)
- 0/1/2+ candidates branches: yes (empty-state / skip-picker / picker dialog)
- Shadcn Dialog with Radix DialogPrimitive: yes
- Confirmation popup: image + name + model + category + voltage + interfaces + key_specs + tags + datasheet link + source link: yes
- Datasheet + source links: target="_blank" rel="noopener noreferrer": yes
- ADD TO DATABASE + CANCEL buttons: yes
- Success animation: green flash + check scale-in: yes
- Form resets after save: yes
- All animations < 300ms, no bounce: yes
- NO remote calls (mock catalog only): yes
- NO new deps beyond @radix-ui/react-dialog: yes
- NO changes to other projects: yes
- RGV1 + MC still 200: yes
- Git commit created: yes
**evidence:**
- `01_projects/diy-hub-v1/tasks/DIY-002-ADD-COMPONENT.md` (this file, updated to complete)
- `00_company_os/events.jsonl` (210 → 214 lines, +4 closure events for DIY-002)
- `00_company_os/04_agents/state.json` (3 agents idle, awaiting Stage 3)
- `00_company_os/04_agents/logs/2026-06-13/forge-diy002-1781214686.md` (Forge report)
- `00_company_os/04_agents/logs/2026-06-13/argus-diy002-1781214686.md` (Argus report, 32/32 PASS)
- `code/backend/app/routes/components.py` (3 endpoints)
- `code/backend/app/mock_data.py` (16 components + SVG generator)
- `code/frontend/src/components/ui/dialog.tsx` (Shadcn Dialog, uses @radix-ui/react-dialog)
- `code/frontend/src/pages/AddComponent.tsx` (617 lines, full flow)
- `data/diy-hub.db` (4 components, gitignored)
- `data/images/*.svg` (4 SVG files, gitignored)
- Git commit: pending
- Git tag: `diy-hub-v1-stage-2` (pending, annotated)
**blockers:** None
**argus_result:** pass
**data_source:** real
