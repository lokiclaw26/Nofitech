# DIY HUB CODEX V2

A local DIY electronics inventory and idea-generation app with a more playful Codex-built V2 interface.

See `charter.md`, `status.md`, and `plan.md` for the full picture.

## Stack

- **Frontend:** React 19 + Vite 8 + TypeScript 6, Tailwind CSS 3, Shadcn UI (Button) + Radix UI (`@radix-ui/react-slot`), Framer Motion 12, React Router DOM 6.
- **Backend:** Python 3.11, FastAPI, SQLAlchemy 2.0, uvicorn[standard], SQLite 3.
- **No auth, no Docker, no systemd, no cron, no telemetry.**

## Run

```bash
# One-shot: install + boot both servers, print URLs.
bash start-dev.sh
```

The script:
1. Kills anything on `:5173` or `:8780` (idempotent).
2. Starts the FastAPI backend on `0.0.0.0:8780` (logs → `logs/backend.log`).
3. Starts the Vite frontend on `0.0.0.0:5173` (logs → `logs/frontend.log`).
4. Waits for both to respond, then prints:
   - `Frontend:  http://<lan-ip>:5173/`
   - `Backend:   http://<lan-ip>:8780/docs`
   - `Health:    http://<lan-ip>:8780/api/health`
5. Exits (the two servers keep running in the background). Use `tail -f logs/backend.log` / `tail -f logs/frontend.log` to watch.

To stop:
```bash
lsof -ti:5173 | xargs -r kill -9
lsof -ti:8780 | xargs -r kill -9
```

## Manual run (for development)

### Backend
```bash
cd code/backend
source .venv/bin/activate   # or create with: python3 -m venv .venv
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8780
```

### Frontend
```bash
cd code/frontend
npm install
npm run dev -- --host 0.0.0.0 --port 5173
```

The frontend talks to the backend at `VITE_API_URL` (default `http://127.0.0.1:8780`).

## Layout

```
diy-hub-codex-v2/
├── charter.md
├── status.md
├── plan.md
├── README.md              ← this file
├── start-dev.sh
├── tasks/                 ← task files
├── logs/                  ← backend.log, frontend.log
├── evidence/              ← evidence artifacts
├── qa/                    ← QA reports
├── design/                ← design notes
├── code/
│   ├── frontend/          ← Vite app (port 5173)
│   └── backend/           ← FastAPI app (port 8780, venv lives here)
└── data/
    ├── diy-hub.db         ← SQLite (created on first backend boot)
    └── images/            ← local image storage (writable)
```

## Endpoints (Stage 1)

- `GET /api/health` — `{"status":"ok"}` — used by the Dashboard to prove wiring.
- `GET /api/pages` — `["Dashboard", "Add Component", "Inventory", "Idea Lab", "Settings"]`.
- `GET /api/info` — debug dump of DB path, image dir, version, pages.
- `GET /docs` — auto-generated Swagger UI.

## SQLite schema

6 tables, applied idempotently on backend boot (`CREATE TABLE IF NOT EXISTS`):
`components`, `ideas`, `tags`, `component_tags`, `images`, `settings`.

## Hard rules

- Do **not** edit other projects (`01_projects/roguelike-v1/` is paused, `01_projects/mission-control/` is frozen at v1.15.0).
- Do **not** kill the RGV1 game server (PID 137327) or Mission Control (PID 130719).
- Do **not** add new dependencies beyond the approved stack.
- Stage 1 is the only stage built so far. **Stop after Stage 1 and ask NOFI for approval before continuing.**
