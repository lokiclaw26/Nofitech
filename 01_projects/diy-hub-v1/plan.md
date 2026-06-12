# DIY Hub V1 — Plan

## Stage 1 — Project Setup + Running App (THIS REPORT)
- [x] Project skeleton under `01_projects/diy-hub-v1/` with subdirs
- [x] Frontend: Vite + React + TypeScript + Tailwind + Shadcn + Radix + Framer Motion + React Router
- [x] Backend: FastAPI + SQLAlchemy + uvicorn + python-multipart + Pillow, in a venv
- [x] SQLite schema applied (6 tables, all empty, idempotent `CREATE TABLE IF NOT EXISTS`)
- [x] `/api/health` returns `{"status":"ok"}`
- [x] `/api/pages` returns the 5 page names
- [x] CORS configured for `http://127.0.0.1:5173`
- [x] 5 routes reachable: `/`, `/add`, `/inventory`, `/ideas`, `/settings`
- [x] Dashboard page calls backend and displays the response (proves end-to-end wiring)
- [x] `start-dev.sh` boots both servers, prints URLs, exits, leaves processes running
- [x] `data/images/` is writable, has `.gitkeep`
- [x] `requirements.txt` pinned, `package.json` populated
- [x] README documents how to run
- [x] **Stop here. Ask NOFI for approval before continuing.**

## Stage 2 — Add Component CRUD + image upload (FUTURE, BLOCKED)
- Schema work already done; API endpoints are next.
- "Add Component" form on `/add` with: name, category, quantity, location, notes, image upload.
- Image saved to `data/images/`, metadata written to `images` table, FK into `components.image_path`.
- POST `/api/components`, GET `/api/components`, GET `/api/components/{id}`.

## Stage 3 — Inventory list, search, filter, tag UI (FUTURE, BLOCKED)
- `/inventory` becomes a real table backed by `GET /api/components`.
- Tag picker against the `tags` table; many-to-many via `component_tags`.
- Search + filter by category, location, tag.

## Stage 4 — Idea Lab: draft/save + "AI suggests, NOFI confirms" (FUTURE, BLOCKED)
- `/ideas` page lists `ideas` table.
- AI suggestions live in client state (or a draft table) until NOFI clicks "Save".
- POST `/api/ideas` is the only write path; AI never writes directly.

## Stage 5+ — Settings, polish, packaging (FUTURE, BLOCKED)
- `/settings` reads/writes the `settings` table (theme, DB path display, image dir, etc.).
- TBD based on NOFI's feedback after Stage 1.
