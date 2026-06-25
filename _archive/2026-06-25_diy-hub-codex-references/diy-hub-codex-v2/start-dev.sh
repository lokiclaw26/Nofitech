#!/usr/bin/env bash
# DIY Hub V1 — start both servers, print URLs, exit (leaves processes running).
# Idempotent: run it twice in a row, it restarts cleanly.
set -u

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

LOG_DIR="$PROJECT_DIR/logs"
mkdir -p "$LOG_DIR"
mkdir -p "$PROJECT_DIR/data/images"
touch "$PROJECT_DIR/data/images/.gitkeep"

FRONT_PORT=5173
BACK_PORT=8780

# ---- Detect LAN IP (best effort, falls back to 127.0.0.1) ------------------
LAN_IP="$(hostname -I 2>/dev/null | awk '{print $1}')"
[ -z "$LAN_IP" ] && LAN_IP="127.0.0.1"

# ---- Kill anything bound to our ports (idempotent restart) -------------------
echo "[start-dev] Killing any prior processes on :$FRONT_PORT and :$BACK_PORT ..."
lsof -ti:"$FRONT_PORT" 2>/dev/null | xargs -r kill -9 2>/dev/null || true
lsof -ti:"$BACK_PORT"  2>/dev/null | xargs -r kill -9 2>/dev/null || true
sleep 1

# ---- Backend: venv + uvicorn (background) -----------------------------------
BACKEND_DIR="$PROJECT_DIR/code/backend"
VENV="$BACKEND_DIR/.venv"

if [ ! -x "$VENV/bin/python" ]; then
  echo "[start-dev] Creating Python venv in $VENV ..."
  python3 -m venv "$VENV"
fi

# shellcheck disable=SC1091
source "$VENV/bin/activate"

echo "[start-dev] Installing/verifying backend deps ..."
pip install --quiet --upgrade pip >/dev/null 2>&1 || true
pip install --quiet -r "$BACKEND_DIR/requirements.txt" 2>&1 | tail -5 || {
  echo "[start-dev] pip install failed — see $LOG_DIR/backend.log"; exit 1; }

# Initialise DB (idempotent) before launching uvicorn so logs are clean.
# The init runs from $BACKEND_DIR so that `app.main` is importable.
echo "[start-dev] Initialising DB + loading app ..."
(cd "$BACKEND_DIR" && python -c "from app.main import app; print('schema OK, app loaded; routes =', [r.path for r in app.routes if hasattr(r, 'path')])") \
  > "$LOG_DIR/backend-init.log" 2>&1 || {
    echo "[start-dev] Backend init failed — see $LOG_DIR/backend-init.log"; exit 1; }

echo "[start-dev] Starting backend on 0.0.0.0:$BACK_PORT ..."
cd "$BACKEND_DIR"
nohup "$VENV/bin/uvicorn" app.main:app --host 0.0.0.0 --port "$BACK_PORT" \
  > "$LOG_DIR/backend.log" 2>&1 &
BACK_PID=$!
echo "[start-dev] backend PID: $BACK_PID"
cd "$PROJECT_DIR"

# ---- Frontend: npm install + vite (background) ------------------------------
FRONTEND_DIR="$PROJECT_DIR/code/frontend"

if [ ! -d "$FRONTEND_DIR/node_modules" ]; then
  echo "[start-dev] Installing frontend deps (this can take ~30s) ..."
  (cd "$FRONTEND_DIR" && npm install --no-audit --no-fund) >> "$LOG_DIR/frontend.log" 2>&1
fi

echo "[start-dev] Starting frontend on 0.0.0.0:$FRONT_PORT ..."
(cd "$FRONTEND_DIR" && nohup npm run dev -- --host 0.0.0.0 --port "$FRONT_PORT" --strictPort \
  > "$LOG_DIR/frontend.log" 2>&1) &
FRONT_PID=$!
echo "[start-dev] frontend PID: $FRONT_PID"

# ---- Wait for both to respond ----------------------------------------------
echo "[start-dev] Waiting for backend /api/health ..."
for i in $(seq 1 40); do
  if curl -sf "http://127.0.0.1:$BACK_PORT/api/health" >/dev/null 2>&1; then
    echo "[start-dev] backend up after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" = "40" ]; then
    echo "[start-dev] backend did not respond in 40s — see $LOG_DIR/backend.log"
  fi
done

echo "[start-dev] Waiting for frontend :$FRONT_PORT ..."
for i in $(seq 1 40); do
  CODE=$(curl -s -o /dev/null -w "%{http_code}" "http://127.0.0.1:$FRONT_PORT/" 2>/dev/null || echo "000")
  if [ "$CODE" = "200" ]; then
    echo "[start-dev] frontend up after ${i}s"
    break
  fi
  sleep 1
  if [ "$i" = "40" ]; then
    echo "[start-dev] frontend did not return 200 in 40s — see $LOG_DIR/frontend.log (last code: $CODE)"
  fi
done

# ---- Print URLs -------------------------------------------------------------
echo ""
echo "============================================================"
echo " DIY Hub V1 — dev servers running"
echo "   Frontend:  http://$LAN_IP:$FRONT_PORT/"
echo "   Backend:   http://$LAN_IP:$BACK_PORT/docs"
echo "   Health:    http://$LAN_IP:$BACK_PORT/api/health"
echo "   Pages:     http://$LAN_IP:$BACK_PORT/api/pages"
echo "   PIDs:      backend=$BACK_PID  frontend=$FRONT_PID"
echo "   Logs:      $LOG_DIR/backend.log  +  $LOG_DIR/frontend.log"
echo "============================================================"
echo " To stop:"
echo "   lsof -ti:$FRONT_PORT | xargs -r kill -9"
echo "   lsof -ti:$BACK_PORT  | xargs -r kill -9"
echo "============================================================"
echo ""
# Done — exit, leaving the two backgrounded processes running.
exit 0
