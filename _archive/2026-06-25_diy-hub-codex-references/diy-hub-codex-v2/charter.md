# DIY Hub V1 — Project Charter

**Project:** DIY Hub V1
**Owner:** NOFI
**Date opened:** 2026-06-13
**Status:** Stage 1 — Project Setup + Running App (awaiting NOFI approval)

## 1. Goal

A **local DIY electronics inventory and idea-generation app**. NOFI owns
every component that goes in and every idea that gets saved. The database is
local and is the source of truth.

**Core rule (from NOFI's brief):** *AI can suggest, but nothing is saved
until NOFI confirms.* This is enforced architecturally (the API surface in
Stage 1 is built so that the UI can show AI suggestions without ever calling
a write endpoint, and confirmation writes through a separate user-OK'd path).

## 2. Scope

### Stage 1 (this report)
- Full project structure under `01_projects/diy-hub-v1/`
- Frontend scaffold: Vite + React + TypeScript + Tailwind + Shadcn UI + Radix UI + Framer Motion + React Router DOM
- Backend scaffold: Python FastAPI + SQLAlchemy + SQLite + uvicorn
- SQLite schema applied (6 empty tables: `components`, `ideas`, `tags`, `component_tags`, `images`, `settings`)
- Basic running app with a top nav bar and 5 reachable routes:
  - `/` — Dashboard (proves end-to-end wiring with a live `/api/health` call)
  - `/add` — Add Component (placeholder)
  - `/inventory` — Inventory (placeholder, empty state)
  - `/ideas` — Idea Lab (placeholder, empty state)
  - `/settings` — Settings (placeholder, empty state)
- No business logic, no CRUD, no AI, no idea generation.

### Future stages (not built yet)
- **Stage 2** — Add Component CRUD + image upload to `data/images/`
- **Stage 3** — Inventory list + search/filter/tag UI
- **Stage 4** — Idea Lab: draft/save flow + AI-suggest-but-don't-save rule
- **Stage 5+** — Settings, polish, packaging

## 3. Tech stack

| Layer    | Choice                                            |
|----------|---------------------------------------------------|
| Frontend | React 19 + Vite 8 + TypeScript 6                  |
| Styling  | Tailwind CSS 3 + tailwindcss-animate              |
| UI kit   | Shadcn UI (Button) + Radix UI (`@radix-ui/react-slot`) |
| Motion   | Framer Motion 12                                  |
| Routing  | React Router DOM 6                                |
| Backend  | Python 3.11 + FastAPI + uvicorn[standard] + SQLAlchemy 2.0 |
| ORM      | SQLAlchemy 2.0                                    |
| DB       | SQLite 3 (file: `data/diy-hub.db`)                |
| Images   | Local disk: `data/images/` (writable)             |

NO Docker. NO auth. NO telemetry. NO remote calls.

## 4. Hard rules (NOFI + memory entry 010)

1. **No hero mode.** Task file FIRST, events FIRST, state.json FIRST, then code.
2. **Stop after Stage 1** and ask NOFI for approval before continuing.
3. **Database is local and is the source of truth.** No remote sync, no cloud.
4. **AI can suggest, NOFI confirms.** No silent writes.
5. **No business logic in Stage 1.** No CRUD, no form submission, no AI.
6. **No new dependencies** beyond the approved stack.
7. **No Docker, no systemd, no autostart, no cron.** `start-dev.sh` is the only way to start.
8. **No edits to other projects** (roguelike-v1 paused, mission-control frozen at v1.15.0).
9. **Do not kill** PID 137327 (RGV1 game server) or PID 130719 (Mission Control).

## 5. Ports

| Service       | Port | Bound        | Note                          |
|---------------|------|--------------|-------------------------------|
| Frontend (Vite) | 5173 | 0.0.0.0      | Default Vite port             |
| Backend (uvicorn) | 8780 | 0.0.0.0   | FastAPI                       |
| RGV1 (don't touch) | 8770 | —        | Game server (PID 137327)      |
| Mission Control (don't touch) | 8767 | — | Frozen (PID 130719)         |

## 6. File layout

```
diy-hub-v1/
├── charter.md          ← this file
├── status.md           ← live project status
├── plan.md             ← stage plan
├── README.md           ← run instructions
├── start-dev.sh        ← boots both servers
├── tasks/              ← task files
├── logs/               ← backend.log + frontend.log
├── evidence/           ← evidence artifacts
├── qa/                 ← QA reports
├── design/             ← design notes
├── code/
│   ├── frontend/       ← Vite + React + TS app
│   └── backend/        ← FastAPI app + .venv
└── data/
    ├── diy-hub.db      ← SQLite
    └── images/         ← writable image storage
```

## 7. Status

**Phase:** build
**Stage:** Stage 1 in progress (running, awaiting NOFI approval)
**Approval needed:** yes
**Data source:** real (real running services, real schema, real HTTP responses)
