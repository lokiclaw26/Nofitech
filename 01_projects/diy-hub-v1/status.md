---
id: diy-hub-v1
title: DIY Hub V1
phase: build
status: stage-3-shipped
progress_pct: 80%
approval_needed: true
next_action: "Stage 3 (Real Wikipedia images) complete. Awaiting NOFI approval to begin Stage 4 (Inventory list + search/filter/tag UI)."
blocker: ""
data_source: real
created: 2026-06-13
updated: 2026-06-13
version: 0.1.0
charter: 01_projects/diy-hub-v1/charter.md
plan: 01_projects/diy-hub-v1/plan.md
tasks: 01_projects/diy-hub-v1/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-13/
code: 01_projects/diy-hub-v1/code/
---

# Project: DIY Hub V1

**STAGES 1-3 SHIPPED 2026-06-13. AWAITING NOFI APPROVAL TO BEGIN STAGE 4.**

## Current state
- **Stage 1:** Project setup + running app — DONE
- **Stage 2:** Add Component flow (mock data, colored SVG images) — DONE
- **Stage 3:** Real Wikipedia images (REPLACES the colored SVGs from Stage 2) — DONE
- **Frontend:** Vite + React 19 + TS + Tailwind + Shadcn UI (Button + Dialog) + Radix UI (Slot + Dialog) + Framer Motion + React Router DOM — RUNNING on :5173
- **Backend:** FastAPI + SQLAlchemy + SQLite + urllib (stdlib) + uvicorn — RUNNING on :8780 with 7 API endpoints (/api/health, /api/pages, /api/info, /api/components, /api/components/search, /api/components GET, /api/images/<basename> static mount)
- **Database:** 6+ components in SQLite (ESP32 DevKit V1 [1 real JPEG], Arduino Nano, Raspberry Pi 4, STM32 Blue Pill, ESP32-S3, etc.)
- **Image dir:** real JPEGs from Wikipedia in data/images/ (esp32-devkit-v1-devkit-v1.jpg = 56KB, magic bytes ffd8ffdb)
- **RGV1 game server :8770:** UNTOUCHED, HTTP 200 (PID 137327)
- **Mission Control :8767:** UNTOUCHED, HTTP 200 (PID 130719)

## What works (Stage 3 deliverable)
- Wikipedia REST fetcher (`code/backend/app/wikipedia.py`): stdlib-only, 5s timeout, polite User-Agent, in-memory cache, never raises
- Search endpoint returns candidates with `image_url` (real Wikipedia thumbnail) + `image_source: "wikipedia"` + `image_attribution: { license, source_url }`
- Save endpoint downloads the image to `data/images/<slug>.<ext>` (real JPEG/PNG/WebP), stores the local path, records in `images` table
- Graceful degradation: if no Wikipedia image (WS2812, SG90, unknown terms) or download fails, save still succeeds with `image_path=null`
- Frontend uses `<img src={image_url}>` with `onError` fallback to a gray "No real image found" placeholder
- Hotfix-2 SVG code is REMOVED (no more `dangerouslySetInnerHTML`, no more `mock_image_data`, no more colored SVG blocks)
- Confirmation popup shows "Source: Wikipedia · CC BY-SA" attribution below the image
- /api/images/<basename> serves the saved images back to the browser
- All 24 Argus verification checks PASS

## Hard rules honored
- NO Google, NO Octopart, NO paid APIs, NO API keys, NO login, NO purchasing
- Only public Wikipedia REST endpoint with polite User-Agent
- NO new dependencies (urllib is stdlib)
- NO auth, NO systemd, NO autostart, NO cron
- NO Docker
- NO changes to other projects (RGV1 paused, MC frozen)
- RGV1 PID 137327 and Mission Control PID 130719 NOT killed
- NO fake placeholder/color-block images for components anymore (NOFI explicit)

## Completed stages
- Stage 1 — Project Setup + Running App (5 routes, 4 frontend stacks, FastAPI+SQLite, 6-table schema)
- Stage 2 — Add Component Flow (4-input form, mock search, Shadcn Dialog picker, confirmation popup, save to SQLite + write SVG)
- Stage 2 Hotfix 1 — API URL: hardcoded 127.0.0.1 fails on LAN → runtime hostname (4 lines, 2 files)
- Stage 2 Hotfix 2 — Component images not visible → SVG scale regex in CandidateImage (3 lines, 1 file)
- Stage 3 — Real Wikipedia images (replaces Stage 2's mock SVGs, stdlib urllib, real JPEG/PNG/WebP on disk, attribution shown)

## V0.1 plan (Stages 4+, awaiting NOFI approval)
- **Stage 4** — Inventory list page: show all saved components with real images, search/filter/tag UI
- **Stage 5** — Idea Lab: draft/save flow + AI-suggest-but-don't-save rule
- **Stage 6** — Settings: theme toggle, data export, image directory view
- **Stage 7+** — Polish, packaging

## Git
- 3 stage tags: `diy-hub-v1-stage-1`, `diy-hub-v1-stage-2`, `diy-hub-v1-stage-3` (pending, annotated)
- 2 hotfix tags: `diy-hub-v1-hotfix-1`, `diy-hub-v1-hotfix-2` (annotated)
- Stage 3 commit: pending

## Ports
| Service | Port | Bound | PID |
|---|---|---|---|
| Frontend (Vite) | 5173 | 0.0.0.0 | live |
| Backend (uvicorn) | 8780 | 0.0.0.0 | 161060 |
| RGV1 (untouched) | 8770 | 0.0.0.0 | 137327 |
| Mission Control (untouched) | 8767 | 0.0.0.0 | 130719 |
