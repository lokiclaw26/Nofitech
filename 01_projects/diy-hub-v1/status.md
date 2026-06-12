---
id: diy-hub-v1
title: DIY Hub V1
phase: build
status: stage-1-in-progress
progress_pct: 95%
approval_needed: true
next_action: "Stage 1 (Project Setup + Running App) complete. Awaiting NOFI approval to begin Stage 2 (Add Component CRUD)."
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

**STAGE 1 SHIPPED 2026-06-13. AWAITING NOFI APPROVAL TO BEGIN STAGE 2.**

## Current state
- **Stage 1:** Project setup + running app — DONE
- **Frontend:** Vite + React 19 + TypeScript + Tailwind + Shadcn UI + Radix UI + Framer Motion + React Router DOM — RUNNING on port 5173 (PID 153614)
- **Backend:** FastAPI + SQLAlchemy + SQLite + uvicorn — RUNNING on port 8780 (PID 153443)
- **Database:** `data/diy-hub.db` — 6 tables (components, ideas, tags, component_tags, images, settings) — empty
- **Image dir:** `data/images/` — created, writable
- **Both servers:** HTTP 200
- **RGV1 game server :8770:** UNTOUCHED, still HTTP 200
- **Mission Control :8767:** UNTOUCHED, still HTTP 200
- **End-to-end wiring proven:** Dashboard page fetches `/api/health` and `/api/pages` and displays the responses
- **Last commit:** pending (will be created at end of Stage 1 closure)

## What works (Stage 1 deliverable)
- 5 routes reachable via top nav bar:
  - `/` — Dashboard (live fetch of /api/health + /api/pages, Tailwind `bg-red-500` proves pipeline)
  - `/add` — Add Component (placeholder, framer-motion fade-in)
  - `/inventory` — Inventory (placeholder, empty state)
  - `/ideas` — Idea Lab (placeholder, empty state)
  - `/settings` — Settings (placeholder, empty state)
- Shadcn Button (uses Radix Slot) imported in Dashboard, AddComponent, NavBar
- Framer Motion `<motion.h1>` + `<motion.div>` with `initial`/`animate` in all pages
- React Router DOM v6 with `BrowserRouter` + `Routes` + `Route`
- 3 API endpoints: `/api/health`, `/api/pages`, `/api/info` (plus auto `/docs`, `/openapi.json`, `/redoc`)
- CORS configured for http://127.0.0.1:5173 (covers localhost, 10.x, 192.168.x, 172.16-31.x)

## Hard rules honored
- NO authentication, NO auth, NO signup, NO login, NO API key, NO remote calls, NO telemetry
- NO systemd, NO autostart, NO cron — `start-dev.sh` is the only start path
- NO Docker
- NO business logic, NO CRUD, NO AI, NO idea generation
- NO edits to other projects (roguelike-v1 paused, mission-control frozen)
- RGV1 PID 137327 and Mission Control PID 130719 NOT killed

## Completed stages
- Stage 1 — Project Setup + Running App (5 routes, 4 frontend stacks, FastAPI+SQLite, 6-table schema)

## V0.1 plan (Stages 2+, awaiting NOFI approval)
- **Stage 2** — Add Component CRUD + image upload to `data/images/`
- **Stage 3** — Inventory list + search/filter/tag UI
- **Stage 4** — Idea Lab: draft/save flow + AI-suggest-but-don't-save rule
- **Stage 5+** — Settings, polish, packaging

## Git
- 1 stage tag: `diy-hub-v1-stage-1` (pending, annotated)
- Stage 1 commit: pending

## Ports
| Service | Port | Bound | PID |
|---|---|---|---|
| Frontend (Vite) | 5173 | 0.0.0.0 | 153614 |
| Backend (uvicorn) | 8780 | 0.0.0.0 | 153443 |
| RGV1 (untouched) | 8770 | 0.0.0.0 | 137327 |
| Mission Control (untouched) | 8767 | 0.0.0.0 | 130719 |
