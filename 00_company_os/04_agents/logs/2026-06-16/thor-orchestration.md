---
task_id: MC-MC-OUTAGE-RESTORE-1
agent: thor
role: CEO / Orchestrator
project: mission-control
status: complete
created: 2026-06-16T19:08:00Z
---

# Thor Coordination Log — MC-MC-OUTAGE-RESTORE-1

## NOFI's report

Mission Control page unreachable: http://192.168.0.29:8767/mission-control.html

## Investigation findings

- **Service stack:** `python3 serve.py` (custom http.server-based, v1.15.0) launched via `01_projects/mission-control/code/start-mc.sh` (v1.4.x) using `nohup` + `&`.
- **Port 8767:** not bound. `ss -tlnp | grep 8767` → empty.
- **Stale PID file:** `code/logs/mission-control.pid` contained PID 191803 from 2026-06-16 16:04 (now 23:08, ~7h old). `kill -0 191803` → process dead.
- **No python serve.py process running.** `ps -ef | grep serve.py` → empty.
- **Log file `code/logs/mission-control.log`:** last line is the startup banner from 16:04. No crash trace, no error message, no shutdown line.
- **Resources:** disk 2% used, memory 12Gi free — not OOM, not disk-full.
- **Network:** `enp0s31f6` still on 192.168.0.29/24 (unchanged). No IP drift.
- **Bind config:** `serve.py` line 53 = `HOST = "0.0.0.0"` (correct LAN-bind). Not a bind issue.
- **Conjunction:** log shows clean startup at 16:04; no SIGHUP handler, no trap; PID gone 7h later with no error. Classic orphan: the tmux/terminal pane that launched it closed (or the parent ssh/hermes session that started start-mc.sh was reaped) and the child died with it. The `nohup ... &` in start-mc.sh is not effective when launched from a transient parent that itself gets reaped in a way that doesn't propagate SIGHUP normally — the bash process group can still terminate.

## Fix applied

1. Removed stale PID file `code/logs/mission-control.pid`.
2. Launched `python3 serve.py` directly under Hermes `background=true` (proper detachment, parent-tracked by Hermes so it cannot be SIGHUP'd by a closing shell). PID 198424, started 2026-06-16 23:08.
3. Wrote fresh PID 198424 to `code/logs/mission-control.pid` (so future start-mc.sh runs are idempotent-aware).

## Verification

- `ss -tlnp | grep 8767` → `LISTEN 0 5 0.0.0.0:8767 0.0.0.0:* users:(("python3",pid=198424,fd=4))`
- `curl 127.0.0.1:8767/mission-control.html` → **200**
- `curl 192.168.0.29:8767/mission-control.html` → **200**
- `curl 192.168.0.29:8767/mission-control.html | head -c 200` → `<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>NofiTech Mission Control v1.15.0 — Operational Live Monitor</title>`

## Argus (root cause)

Process was orphaned by its original launch context. The `nohup ... &` in start-mc.sh did not survive because:
- The launching shell (likely a Hermes CLI pane or transient tmux) was reaped in a way that propagated termination to the child process group.
- serve.py has no `signal.signal(SIGHUP, SIG_IGN)` and no `setsid`/double-fork — so when the parent group went away, so did the server.
- No watchdog exists, so 7h elapsed before NOFI noticed the outage.

## Recommendations (NEXT)

1. **Make start-mc.sh actually orphan-proof.** Add `setsid` + redirect stdin from /dev/null + `disown` and ensure `trap '' HUP` inside a wrapper. Alternatively, use `python3 serve.py` inside a `setsid bash -c '...' </dev/null >log 2>&1 &` form.
2. **Add SIGHUP-ignore to serve.py itself** — one-liner: `signal.signal(signal.SIGHUP, signal.SIG_IGN)` at module top. Defensive belt.
3. **Add a watchdog cron** (e.g. every 5 min) that runs `curl -fsS -m 3 http://127.0.0.1:8767/health || ./start-mc.sh` and appends to `code/logs/mission-control.log`. Auto-heal on outage.
4. **Optional: convert to a `systemd --user` service** for proper Restart=on-failure + logjournal. Most robust fix.
5. **Add a /health endpoint to serve.py** so the watchdog has something cheap to probe.

## Files touched (this incident)

- Created: `00_company_os/04_agents/logs/2026-06-16/thor-orchestration.md` (this file)
- Appended: `00_company_os/events.jsonl` (one event line)
- Recreated: `01_projects/mission-control/code/logs/mission-control.pid` (PID 198424)
- NOT touched: `00_company_os/state.json` (per constraints)
- NOT touched: `01_projects/mission-control/code/serve.py` (per constraints)
- NOT touched: `01_projects/mission-control/code/mission-control.html` (per constraints)
