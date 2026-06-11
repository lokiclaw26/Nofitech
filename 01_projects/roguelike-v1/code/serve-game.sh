#!/usr/bin/env bash
# Dungeon Spark — convenience launcher.
# Idempotent: refuses to start a second instance while the first is alive.
set -e

PORT=8770
BIND=0.0.0.0
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Check for an existing listener on PORT (any owner).
if command -v ss >/dev/null 2>&1; then
  if ss -ltn "sport = :$PORT" 2>/dev/null | grep -q ":$PORT"; then
    echo "serve-game.sh: port $PORT already in use, refusing to start a duplicate." >&2
    exit 1
  fi
elif command -v lsof >/dev/null 2>&1; then
  if lsof -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
    echo "serve-game.sh: port $PORT already in use, refusing to start a duplicate." >&2
    exit 1
  fi
fi

cd "$DIR"
echo "serve-game.sh: serving $DIR on http://$BIND:$PORT/"
exec python3 -m http.server "$PORT" --bind "$BIND"
