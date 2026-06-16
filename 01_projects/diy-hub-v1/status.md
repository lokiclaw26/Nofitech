---
id: diy-hub-v1
title: DIY Hub V1
phase: build
status: stage-11-shipped
progress_pct: 100%
approval_needed: true
next_action: "Stage 11 (Real fix for Wemos D1 Mini + similar bugs) shipped 2026-06-14 23:15Z. 20/20 Argus tests pass. Wemos D1 Mini: 6 junk → 2 real. Awaiting NOFI verification of the live add-component page before next stage."
blocker: ""
data_source: real
created: 2026-06-13
updated: 2026-06-14
version: 0.11.0
charter: 01_projects/diy-hub-v1/charter.md
plan: 01_projects/diy-hub-v1/plan.md
tasks: 01_projects/diy-hub-v1/tasks/
evidence: 00_company_os/04_agents/logs/2026-06-13/, 00_company_os/04_agents/logs/2026-06-14/
code: 01_projects/diy-hub-v1/code/
---

# Project: DIY Hub V1

**STAGES 1-11 SHIPPED 2026-06-14 23:15Z. AWAITING NOFI VERIFICATION OF STAGE 11.**

## Current state (live)
- **Stage 11 (latest):** Component Lookup Quality Fix — Real fix for Wemos D1 Mini. 6 junk candidates → 2 real (PlatformIO + Wikidata). All 6 NOFI test cases now clean.
- **20/20 Argus tests pass** (last verification 2026-06-14 23:15Z)
- **Frontend:** Vite + React 19 + TS + Tailwind + Shadcn UI + Radix UI + Framer Motion + React Router DOM — RUNNING on :5173
- **Backend:** FastAPI + SQLAlchemy + SQLite + urllib (stdlib) + uvicorn — RUNNING on :8780
- **Database:** ~26 components in SQLite (`01_projects/diy-hub-v1/data/diy-hub.db`)
- **Image dir:** real JPEGs from Wikimedia Commons in `data/images/`
- **Quality module:** `code/backend/app/quality.py` — 34-term blacklist + 16-domain image allowlist + source priority + 0.50 confidence threshold + 12-candidate cap

## Services (live now)
| Service | Port | URL | PID | Status |
|---|---|---|---|---|
| DIY Frontend (Vite) | 5173 | http://192.168.0.29:5173 | 154295 | live, HMR active |
| DIY Backend (uvicorn) | 8780 | http://192.168.0.29:8780 | 186442 | live, Stage 11 quality active |
| RGV1 game (untouched) | 8770 | http://192.168.0.29:8770 | 137327 | live, paused |
| Mission Control | 8767 | http://192.168.0.29:8767 | 130719 | live, operational monitor |

## Stages shipped with dates
| Stage | Date (UTC) | Description |
|---|---|---|
| Stage 1 | 2026-06-13 | Project Setup + Running App (Vite+FastAPI+SQLite, /add empty) |
| Stage 2 | 2026-06-13 | Add Component Flow (4-input form, mock search, Shadcn Dialog, save) |
| Stage 2 Hotfix 1 | 2026-06-13 | API URL runtime hostname (uses window.location.hostname) |
| Stage 2 Hotfix 2 | 2026-06-13 | SVG scale regex in CandidateImage (300px max) |
| Stage 3 | 2026-06-13 | Real Wikipedia images (15 per-model URLs, NO MORE mock colored blocks) |
| Stage 4 | 2026-06-13 | One-line AI search + per-model image (ESP32-S3 ≠ ESP32-DevKit-V1) |
| Stage 5 | 2026-06-13 | Inventory list page (saved components, real images, search/filter) |
| Stage 6 | 2026-06-14 | Idea Lab (drafts + AI-suggested but NOT auto-saved — NOFI clicks ADD TO DATABASE) |
| Stage 7 | 2026-06-14 | Settings (theme toggle, data export) |
| Stage 8 | 2026-06-14 | Enter-Manually everywhere + List/Card view toggle |
| Stage 9 | 2026-06-14 | Image URL fix (Vite no proxy for /api/*) + Delete + Inline Qty Edit |
| Stage 10 | 2026-06-14 | Component Lookup Quality Fix (1st pass — had bugs in real use) |
| **Stage 11** | **2026-06-14 23:15Z** | **Component Lookup Quality Fix (real fix — Wemos D1 Mini 6→2, all clean)** |

## What works (Stage 11 deliverable)
- **5 quality fixes** in `code/backend/app/quality.py`:
  1. `_all_tokens_match` — requires ALL query tokens in title (was: at least one)
  2. REMOVED trusted-source bypass in `clean_candidates` (Adafruit is only trusted if title matches)
  3. NEW `PHOTO_SUFFIXES` (26 entries: Front/Back/Top/Pinout/Schematic/PCB/Assembled/Closeup) — Wikimedia photos, not products
  4. NEW `PROJECT_MARKERS` (36 entries, matched on NORMALIZED title: weatherstation/luftdata/iotproject/esphome/circuitpython/airquality/co2monitor/...)
  5. NEW `VARIANT_SUFFIXES` (25 entries: pro/plus/lite/micro/v2/s3/esp32) — `-0.25` score penalty (demoted, not rejected)
- **Plus:** Wikidata bonus +0.20 → +0.25; added `wikidata.org/entity/` to trusted sources
- **All 6 NOFI test cases verified clean:**
  - ESP32 DevKit V1 → 2 candidates (Adafruit ESP32-S3 + PlatformIO) ✅
  - Wemos D1 Mini → 2 candidates (PlatformIO + Wikidata Q31275763) — was 6, fixed ✅
  - BME280 → 5 candidates (Adafruit + PlatformIO + Wikidata + 2 chip photos) ✅
  - INA219 → 4 candidates (all clean) ✅
  - TP4056 → 3 candidates (PlatformIO + 2 chip photos, Adafruit Micro-Lipo correctly excluded) ✅
  - ILI9488 XPT2046 → 1 candidate (clean) ✅

## Hard rules honored
- NO Google, NO Octopart, NO paid APIs, NO API keys, NO login, NO purchasing
- Only public Wikipedia REST + Wikimedia Commons + PlatformIO + Adafruit + GitHub official with polite User-Agent
- NO new dependencies (urllib is stdlib, quality module is stdlib-only)
- NO auth, NO systemd, NO autostart, NO cron
- NO Docker
- NO changes to other projects (RGV1 paused, MC operational monitor)

## Git
- **11 stage tags:** `diy-hub-v1-stage-1` through `diy-hub-v1-stage-11` (annotated)
- 2 hotfix tags: `diy-hub-v1-hotfix-1`, `hotfix-2` (annotated)
- Latest commit: `5ae7850` (Stage 11)
- 4 files changed in latest, 247 insertions, 63 deletions

## V0.1 plan (Stage 12+, awaiting NOFI approval)
- **Stage 12** — TBD per NOFI (Idea Lab enhance? Settings v2? Image search across multiple sources? Bulk import? Tags/categories?)

## Evidence
- `00_company_os/04_agents/logs/2026-06-13/` — Stages 1-5 + 2 hotfixes
- `00_company_os/04_agents/logs/2026-06-14/` — Stages 6-11
- `01_projects/diy-hub-v1/qa/` — Argus test logs (26-29 tests per stage)
- `01_projects/diy-hub-v1/evidence/` — screenshots, verification scripts
