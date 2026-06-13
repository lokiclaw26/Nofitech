---
id: diy-hub-v1
title: DIY Hub V1
phase: build
status: stage-4-shipped
progress_pct: 90%
approval_needed: true
next_action: "Stage 4 (One-line AI search + per-model image) complete. Awaiting NOFI approval to begin Stage 5 (Inventory list page)."
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

**STAGES 1-4 SHIPPED 2026-06-13. AWAITING NOFI APPROVAL TO BEGIN STAGE 5.**

## Current state
- **Stage 1:** Project setup + running app — DONE
- **Stage 2:** Add Component flow (4-input form, mock data) — DONE
- **Stage 3:** Real Wikipedia images (replaces mock colored SVGs) — DONE
- **Stage 4:** One-line AI search + per-model image — DONE
- **Frontend:** Vite + React 19 + TS + Tailwind + Shadcn UI + Radix UI + Framer Motion + React Router DOM — RUNNING on :5173
- **Backend:** FastAPI + SQLAlchemy + SQLite + urllib (stdlib) + uvicorn — RUNNING on :8780
- **Database:** 7+ components in SQLite
- **Image dir:** real JPEGs from Wikimedia Commons in data/images/
- **RGV1 :8770:** UNTOUCHED, HTTP 200 (PID 137327)
- **Mission Control :8767:** UNTOUCHED, HTTP 200 (PID 130719)

## What works (Stage 4 deliverable)
- **Single text input** on /add (replaces the old 2-input name+model form)
- **Rule-based keyword parser** identifies component + specific model from free text
- For "ESP32 DevKit V1" → 1 specific candidate (no picker needed)
- For "esp32" → 3 candidates with 3 different images (picker dialog)
- For "arduino" → 3 candidates (Uno R3, Nano, Mega 2560) with 3 different images
- For "raspberry pi 4" → 1 specific candidate (Pi 4B)
- For "xyz123" → 1 synthetic candidate with no image (UI shows "No real image found")
- **15 hardcoded per-model image URLs** from Wikimedia Commons, all pre-verified
- **THE BUG FIX:** esp32-s3 has a DIFFERENT image (ESP32-S3_on_paper.jpg) from esp32-devkit-v1 (Espressif_ESP-WROOM-32...jpg). Previously both showed the same image.
- Save flow: search → confirm → save → image downloaded to data/images/<slug>.jpg → local path stored
- Frontend shows "Source: Wikipedia · CC BY-SA" attribution below the image
- 24/24 Argus verification checks pass

## Hard rules honored
- NO Google, NO Octopart, NO paid APIs, NO API keys, NO login, NO purchasing
- Only public Wikipedia REST + Wikimedia Commons with polite User-Agent
- NO new dependencies (urllib is stdlib, parser is pure python)
- NO auth, NO systemd, NO autostart, NO cron
- NO Docker
- NO changes to other projects (RGV1 paused, MC frozen)
- RGV1 PID 137327 and Mission Control PID 130719 NOT killed

## Completed stages
- Stage 1 — Project Setup + Running App
- Stage 2 — Add Component Flow (4-input form, mock search, Shadcn Dialog, save)
- Stage 2 Hotfix 1 — API URL runtime hostname
- Stage 2 Hotfix 2 — SVG scale regex in CandidateImage
- Stage 3 — Real Wikipedia images
- Stage 4 — One-line AI search + per-model image (CURRENT)

## V0.1 plan (Stage 5+, awaiting NOFI approval)
- **Stage 5** — Inventory list page: show all saved components with real images, search/filter/tag UI
- **Stage 6** — Idea Lab: draft/save flow + AI-suggest-but-don't-save rule
- **Stage 7** — Settings: theme toggle, data export
- **Stage 8+** — Polish, packaging

## Git
- 4 stage tags: diy-hub-v1-stage-1, stage-2, stage-3, stage-4 (pending, annotated)
- 2 hotfix tags: diy-hub-v1-hotfix-1, hotfix-2 (annotated)
- Stage 4 commit: pending

## Ports
| Service | Port | Bound | PID |
|---|---|---|---|
| Frontend (Vite) | 5173 | 0.0.0.0 | live |
| Backend (uvicorn) | 8780 | 0.0.0.0 | 163028 |
| RGV1 (untouched) | 8770 | 0.0.0.0 | 137327 |
| Mission Control (untouched) | 8767 | 0.0.0.0 | 130719 |
