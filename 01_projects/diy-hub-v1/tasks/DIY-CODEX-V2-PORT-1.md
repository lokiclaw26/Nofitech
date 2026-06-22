---
title: "DIY-CODEX-V2-PORT-1 — upgrade diy-hub-v1 UI to match codex-v2 design + add Build Studio"
status: done
kanban_status: done
priority: high
assigned_to: forge
created_at: 2026-06-22T23:05+04:00
project: diy-hub-v1
---

# DIY-CODEX-V2-PORT-1 — Port Codex V2 design + add Build Studio to diy-hub-v1

## Result
**Date:** 2026-06-23T00:41:50+04:00
**By:** forge
**Status:** success

Re-verification pass — the V2 port was already shipped by the earlier DIY-CODEX-PORT-1 dispatch (commits 17442e4 + a6dcf5a). All 8 port-target files in v1 are byte-identical to v2 (diff -q clean: App.tsx, NavBar.tsx, AppLogo.tsx, Dashboard.tsx, IdeaLab.tsx, Inventory.tsx, BuildStudio.tsx, index.css). Brand logo asset present at /home/nofidofi/NofiTech-Ind/01_projects/diy-hub-v1/code/frontend/public/brand/diy-hub-option-6-logo-centered.png (160427 bytes). npm run build passed (exit 0, tsc -b clean, 2106 modules, dist 728K). All 6 routes wired (/, /add, /inventory, /ideas, /build, /settings). IdeaLab BUILD IT button present (line 266, links to /build?idea=<title>). Dark mode persists via diyhub-theme localStorage key. Forbidden files byte-identical: AddComponent.tsx (1276 lines, md5 5c9b41c6), ManualImageInput.tsx, all lib/ files (api, storage PREFIX=diy-hub-v1-, url, utils, categories, sources), Settings.tsx, inventory.ts. No new npm packages (package.json deps identical set to v2; only name field differs). v1 storage PREFIX preserved — no diy-hub-codex-v2- leakage in dist. Backend, database, AddComponent all untouched. Log: /home/nofidofi/NofiTech-Ind/00_company_os/04_agents/logs/2026-06-23/forge-DIY-CODEX-V2-PORT-1.md
## Goal (verbatim from user)

Port the UI/UX improvements from DIY HUB CODEX V2 into the actual DIY Hub app (`01_projects/diy-hub-v1`), while preserving the real backend/API behavior and existing data flow of diy-hub-v1. Add the new Build Studio tab. UI/mock flow is fine for Build Studio (no real AI).

## Reference vs target (already inventoried by Thor)

Reference: `01_projects/diy-hub-codex-v2/code/frontend/`
Target: `01_projects/diy-hub-v1/code/frontend/`

**Stack parity (no new packages needed):** v1 and v2 use identical `package.json` (same deps: tailwind, framer-motion, lucide-react, radix-ui, react-router, etc). Just copy code + add 1 image asset.

**Files that must NOT be touched (preserved as-is from v1):**
- `src/pages/AddComponent.tsx` (54KB, 1276 lines — user explicitly said do not break)
- `src/components/ManualImageInput.tsx`
- `src/lib/api.ts`
- `src/lib/storage.ts` (keep PREFIX = "diy-hub-v1-" — different from v2's "diy-hub-codex-v2-")
- `src/lib/url.ts`
- `src/lib/utils.ts`
- `src/lib/categories.ts` (functionally identical, just different comment)
- `src/lib/sources.ts`
- Backend (`/home/nofidofi/NofiTech-Ind/01_projects/diy-hub-v1/code/backend/`) — DO NOT TOUCH
- Database (`data/diy-hub.db`) — DO NOT TOUCH

**Files identical in both projects (copy as-is from v2):**
- `src/lib/inventory.ts` (matches v1's existing one, no change)
- `src/pages/Settings.tsx` (245 lines, byte-identical)

**Files to copy/adapt from v2 → v1:**
- `src/App.tsx` — add dark mode state, localStorage persistence, Build Studio route, workbench background, scanline overlay
- `src/components/NavBar.tsx` — new dark mode toggle, larger logo via AppLogo, "Live workshop" badge, build studio link
- `src/components/AppLogo.tsx` — NEW, copy from v2
- `src/index.css` — copy v2's @layer utilities (bg-workbench, panel-surface, control-surface, animations) + dark mode variables
- `src/pages/Dashboard.tsx` — copy v2's improved version (351 lines, 12.7KB)
- `src/pages/IdeaLab.tsx` — copy v2's improved version (318 lines, 14.8KB) with BUILD IT button
- `src/pages/Inventory.tsx` — copy v2's improved version (849 lines, 30KB) — bigger styling pass
- `src/pages/BuildStudio.tsx` — NEW, copy from v2 (351 lines, 14.5KB)

**Asset to copy:**
- `public/brand/diy-hub-option-6-logo-centered.png` from v2 → v1 (AppLogo references it)

## Concrete changes (all mechanical, well-specified)

1. **Copy asset**: `cp 01_projects/diy-hub-codex-v2/code/frontend/public/brand/diy-hub-option-6-logo-centered.png 01_projects/diy-hub-v1/code/frontend/public/brand/`

2. **Create `src/components/AppLogo.tsx`** in v1 (copy from v2 verbatim — 813 bytes).

3. **Replace `src/components/NavBar.tsx`** in v1 with v2's version (accepts `darkMode` + `onToggleDarkMode` props).

4. **Replace `src/pages/Dashboard.tsx`** in v1 with v2's version.

5. **Replace `src/pages/IdeaLab.tsx`** in v1 with v2's version (includes BUILD IT button).

6. **Replace `src/pages/Inventory.tsx`** in v1 with v2's version.

7. **Create `src/pages/BuildStudio.tsx`** in v1 (copy from v2).

8. **Replace `src/App.tsx`** in v1 with v2's version (adds dark mode state + Build Studio route + workbench background).

9. **Replace `src/index.css`** in v1 with v2's version (adds workbench + dark mode).

## Non-negotiable scope (DO NOT exceed)

1. **AddComponent.tsx stays v1.** If v2 imports anything you think v1's AddComponent needs, prove it with `diff` and ask Thor first. Do NOT modify.
2. **Backend stays v1.** All API paths/contracts are v1's. The frontend should call v1's existing endpoints.
3. **No new npm packages.** v1 already has everything v2 uses.
4. **Preserve v1's localStorage PREFIX** in `lib/storage.ts` (already identical to v1's pattern; do not overwrite).
5. **Don't refactor what isn't broken** — the point is a tight design port, not a rewrite.

## Acceptance criteria

- [ ] `cd 01_projects/diy-hub-v1/code/frontend && npm install && npm run build` passes with 0 errors
- [ ] No new npm packages installed (`diff package.json` shows only same deps)
- [ ] `src/pages/AddComponent.tsx` is unchanged (byte-identical to pre-port version)
- [ ] `src/components/ManualImageInput.tsx` is unchanged
- [ ] `src/lib/api.ts`, `lib/storage.ts`, `lib/url.ts`, `lib/utils.ts`, `lib/categories.ts`, `lib/sources.ts` are unchanged
- [ ] Brand logo image asset exists at `public/brand/diy-hub-option-6-logo-centered.png`
- [ ] App has routes: `/`, `/inventory`, `/add`, `/ideas`, `/build`, `/settings`
- [ ] NavBar shows: Dashboard, Inventory, Add, Idea Lab, Build Studio, Settings + dark mode toggle + Live workshop badge
- [ ] Idea Lab cards have a "BUILD IT" button that links to `/build?idea=<title>`
- [ ] Build Studio shows: pin diagram, connection list, prompt box, mock generated code preview (no real AI)
- [ ] Dark mode toggle works and persists across reloads (localStorage key `diyhub-theme`)
- [ ] Selected nav tab is clearly highlighted in both light and dark mode
- [ ] Both light and dark mode look polished
- [ ] Frontend builds clean (npm run build succeeds, dist/ regenerated)
- [ ] No TypeScript errors (tsc -b clean)

## Test plan (after changes)

1. `cd 01_projects/diy-hub-v1/code/frontend`
2. `npm install` (should be no-op since deps unchanged)
3. `npm run build` (should pass cleanly)
4. `npm run lint` (if practical)
5. Inspect `dist/` for `brand/diy-hub-option-6-logo-centered.png` to be present

## Files NOT to modify (be explicit)

- `src/pages/AddComponent.tsx`
- `src/components/ManualImageInput.tsx`
- `src/lib/api.ts`
- `src/lib/storage.ts` (keep v1 PREFIX)
- `src/lib/url.ts`
- `src/lib/utils.ts`
- `src/lib/categories.ts`
- `src/lib/sources.ts`
- `src/lib/inventory.ts` (already identical)
- `src/pages/Settings.tsx` (already identical)
- `package.json`
- `tailwind.config.js`
- `tsconfig*.json`
- `vite.config.ts`
- anything in `code/backend/`
- anything in `data/`

## Out of scope

- Wiring real AI into Build Studio (mock flow only)
- Backend changes
- AddComponent refactor
- Auth/permissions
- New routes beyond `/build`
- Mobile-first redesign (use v2's responsive classes as-is)
- New npm packages

## Honest note from Thor

This task has a HIGH success rate IF scope is respected. The risk is Forge "improving" things (refactoring AddComponent, renaming storage PREFIX, tweaking api.ts) — every one of those would silently break user data or features. **If something looks broken, STOP and ask Thor, do not auto-fix.**

## Required final report

```json
{
  "status": "completed | blocked | failed",
  "files_changed": ["absolute paths"],
  "files_created": ["absolute paths"],
  "files_copied": ["absolute paths"],
  "files_unchanged_verified": ["list of files that must NOT have changed, with byte-identical verification"],
  "build_status": "npm run build exit code + size of dist/",
  "route_count": 6,
  "asset_count": 1,
  "new_npm_packages": [],
  "tests": "npm run build output",
  "out_of_scope_untouched": ["AddComponent.tsx", "ManualImageInput.tsx", "all lib/ except possibly categories.ts comment", "all backend/", "data/"],
  "risks": [],
  "next_recommendation": "..."
}
```

## Acceptance (extracted from task body)
- [ ] `cd 01_projects/diy-hub-v1/code/frontend && npm install && npm run build` passes
- [ ] App visually matches Codex V2 direction
- [ ] Navigation includes Dashboard, Inventory, Add, Idea Lab, Build Studio, Settings
- [ ] Idea Lab project cards include a BUILD IT action leading to Build Studio
- [ ] Dark mode toggle works and persists
- [ ] Existing app functionality remains intact (AddComponent, Inventory CRUD, Idea Lab, Settings, search, image upload, quantity edit, delete)
