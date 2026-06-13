---
id: diy-hub-v1
title: DIY Hub V1
phase: build
status: stage-2-shipped
progress_pct: 65%
approval_needed: true
next_action: "Stage 2 (Add Component flow) complete. Awaiting NOFI approval to begin Stage 3 (Inventory list + search/filter/tag UI)."
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

**STAGES 1-2 SHIPPED 2026-06-13. AWAITING NOFI APPROVAL TO BEGIN STAGE 3.**

## Current state
- **Stage 1:** Project setup + running app — DONE
- **Stage 2:** Add Component flow — DONE (form + mock search + dialog + save + SVG)
- **Frontend:** Vite + React 19 + TS + Tailwind + Shadcn UI (Button + Dialog) + Radix UI (Slot + Dialog) + Framer Motion + React Router DOM — RUNNING on :5173
- **Backend:** FastAPI + SQLAlchemy + SQLite + uvicorn — RUNNING on :8780 with 6 API endpoints (/api/health, /api/pages, /api/info, /api/components, /api/components/search, /api/components GET)
- **Database:** 4 components in SQLite (ESP32 DevKit V1, Arduino Nano, Raspberry Pi 4, STM32 Blue Pill)
- **Image dir:** 4 SVG files in data/images/ (one per component, mock-generated, category-colored)
- **RGV1 game server :8770:** UNTOUCHED, HTTP 200
- **Mission Control :8767:** UNTOUCHED, HTTP 200

## What works (Stage 2 deliverable)
- 4-input form on /add: name, model number, quantity, location
- ADD button gated on name + model_number non-empty
- POST /api/components/search with 16-component mock catalog (esp32/3, arduino/3, raspberry/2, neopixel/2, servo/2, lm7805/1, lm358/1, + synthetic fallback for any input)
- 0/1/many branches: empty-state dialog, skip-to-confirm, model-picker dialog
- Model-picker: Shadcn Dialog with clickable animated cards (thumbnail + name + model + category)
- Confirmation popup: full spec layout — image (200x200 SVG), name, model, category, voltage, interfaces (chips), key_specs (chips), tags (chips), datasheet link (target=_blank), source link (target=_blank)
- 2 buttons: ADD TO DATABASE (primary) + CANCEL
- On ADD TO DATABASE: POST /api/components, 201 response, success animation (green flash 200ms + check scale-in 250ms), form reset after 1.5s
- Backend saves: row in `components` table (with spec fields JSON-packed in `notes` column) + SVG file in data/images/<slug>.svg + relative path in image_path
- All animations < 300ms, no bounce, no elastic, no spring
- Shadcn Dialog uses Radix DialogPrimitive (keyboard-accessible for free)

## Hard rules honored
- NO remote calls (mock catalog only, mock SVG generation only)
- NO auth, NO auth, NO API key, NO telemetry
- NO systemd, NO autostart, NO cron — start-dev.sh is the only start path
- NO Docker
- NO new dependencies beyond @radix-ui/react-dialog (auto-pulled by `npx shadcn@latest add dialog`)
- NO changes to other projects (RGV1 paused, MC frozen)
- RGV1 PID 137327 and Mission Control PID 130719 NOT killed

## Completed stages
- Stage 1 — Project Setup + Running App (5 routes, 4 frontend stacks, FastAPI+SQLite, 6-table schema)
- Stage 2 — Add Component Flow (4-input form, mock search, Shadcn Dialog picker, confirmation popup, save to SQLite + write SVG, success animation)

## V0.1 plan (Stages 3+, awaiting NOFI approval)
- **Stage 3** — Inventory list + search/filter/tag UI
- **Stage 4** — Idea Lab: draft/save flow + AI-suggest-but-don't-save rule
- **Stage 5+** — Settings, polish, packaging

## Git
- 2 stage tags: `diy-hub-v1-stage-1`, `diy-hub-v1-stage-2` (pending, annotated)
- Stage 2 commit: pending

## Ports
| Service | Port | Bound | PID |
|---|---|---|---|
| Frontend (Vite) | 5173 | 0.0.0.0 | live |
| Backend (uvicorn) | 8780 | 0.0.0.0 | live |
| RGV1 (untouched) | 8770 | 0.0.0.0 | 137327 |
| Mission Control (untouched) | 8767 | 0.0.0.0 | 130719 |
