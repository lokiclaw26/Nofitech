# DIY-002-HOTFIX-1 — API URL: hardcoded 127.0.0.1 fails on LAN

**id:** DIY-002-HOTFIX-1
**title:** API URL: hardcoded 127.0.0.1 fails on LAN
**project:** diy-hub-v1
**agent:** forge
**status:** complete
**priority:** high
**created:** 2026-06-13
**updated:** 2026-06-13
**description:** NOFI found a real bug live: AddComponent.tsx and Dashboard.tsx both hardcode the API URL to http://127.0.0.1:8780. When NOFI accesses the frontend on http://192.168.0.29:5173 (LAN IP), the browser tries to fetch from 127.0.0.1:8780, which is the user's own device, not the server. Fix: runtime hostname. 4 lines total, 2 files only.
**acceptance:**
- AddComponent.tsx uses a runtime-computed API base: yes
- Dashboard.tsx uses a runtime-computed API base: yes
- Both files use window.location.hostname in the fallback: yes
- Both files still respect import.meta.env.VITE_API_URL: yes
- 127.0.0.1 hardcode count in frontend pages: 0 (was 2 before): yes
- Vite HMR serves the new code: yes
- Backend POST /api/components/search from 127.0.0.1: HTTP 200, returns 3 candidates
- End-to-end LAN POST from 192.168.0.29: HTTP 200
- No new files, no new dependencies, no schema changes: yes
- No changes to other projects: yes
- RGV1 :8770 + MC :8767 still 200: yes
- Git commit: pending
**evidence:**
- `01_projects/diy-hub-v1/tasks/DIY-002-HOTFIX-1.md` (this file, updated to complete)
- `00_company_os/events.jsonl` (214 → 221 lines, +7 events for hotfix)
- `00_company_os/04_agents/state.json` (3 agents idle, awaiting Stage 3)
- `00_company_os/04_agents/logs/2026-06-13/forge-diy002-hotfix1-1781214686.md` (Forge report, honest note about Thor applying directly)
- `00_company_os/04_agents/logs/2026-06-13/argus-diy002-hotfix1-1781214686.md` (Argus report, 11/11 PASS, honest note about Thor verifying directly)
- 2 files modified: `code/frontend/src/pages/AddComponent.tsx`, `code/frontend/src/pages/Dashboard.tsx`
- Git commit: pending
**blockers:** None
**argus_result:** pass
**data_source:** real
