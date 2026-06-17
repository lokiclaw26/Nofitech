# Argus QA: MC-LIVE-REFRESH-1 (commit 60bf1f3)

**Date:** 2026-06-18T01:38:14+04:00
**Live server:** http://127.0.0.1:8767/ (PID 306445)
**Test framework:** Playwright + Python (chromium 149.0.7827.54 via Playwright API)
**Tester:** Argus (via thor-pre-ship dispatch)
**Test script:** `/home/nofidofi/NofiTech-Ind/01_projects/mission-control/qa/test_argus_mc_live_refresh.py`
**Raw result JSON:** `/tmp/argus_mc_live_refresh_result.json`

## How the test was run

- Playwright Python was already installed, but `python3 -m playwright install chromium` is unsupported on Ubuntu 26.04 (Playwright refuses). Reused `/home/nofidofi/.agent-browser/browsers/chrome-149.0.7827.54/chrome` (Google Chrome for Testing) via `chromium.launch(executable_path=...)`. Documented in the test script so future Argus runs do the same.
- Tests 1, 2, 4, 5, 7, 8 ran on the live page while the 5s `setInterval` was active (poll + heartbeat pings every 5s).
- Tests 3 and 6 require observing a **non-live → live** and **live → non-live** transition. Because the page auto-pings thor every 5s, leaving the page open keeps thor perpetually "live". So those two tests were deliberately ordered AFTER the others: I closed the page, posted a fresh heartbeat, waited 130 s with no client open, then re-opened the page to confirm thor fell back to its log mtime, and finally posted another heartbeat to confirm it went live again.

## Results

| # | Test | Result | Notes |
|---|------|--------|-------|
| 1 | Auto-refresh works | **PASS** | First read `01:35:18`, after 7.5 s read `01:35:23` → Δ = 5 s, exactly the 5s poll cadence. |
| 2 | Footer text 5s (no 30s) | **PASS** | `#last-refreshed` reads `Last refreshed: 01:35:23 · auto-refresh: 5s`. Contains `5s`, does NOT contain `30s`. |
| 3 | POST /api/heartbeat flips thor "non-live → live" | **PASS** | Before POST: `last_activity="9h ago"`. POST `{"agent":"thor"}` → 200 with `{"ok":true,...,"ts":"2026-06-17T21:37:55.092279+00:00"}`. After: `last_activity="live"`. Card re-renders with `live` badge on next 5s poll. |
| 4 | GET /api/heartbeat returns 3 agents with `fresh` | **PASS** | `count=3`, agents = `[argus, forge, thor]`, every entry has `fresh` boolean, `ttl_sec=120`. |
| 5 | Green pulse badge renders for live agent | **PASS** | `page.locator(".agent-card:has-text('Thor') .live-pulse").count()` = 1, text = `"live"`. |
| 6 | Heartbeat ages out (TTL=120s) | **PASS** | Before wait: `heartbeat_fresh=true`, `last_activity="live"`. After 130 s with no page open: `heartbeat_fresh=false`, `heartbeat_age_seconds=130`, `last_activity="9h ago"` (fell back to log mtime). |
| 7 | Unknown agent rejected (400) | **PASS** | POST `{"agent":"hacker"}` → HTTP 400, body `{"error":"unknown agent: 'hacker'; must be one of ['thor', 'forge', 'argus']"}`. |
| 8 | No regression on other panels (9 panels) | **PASS** | All 9 panels (Overview, Agents, Action Required, Tasks, Projects, Logs / Health, Warnings, Pending Orders, GitHub Connection) render with non-trivial body and no `loading…`, `TypeError`, `404`, `500` etc. Logs / Health shows `Errors: 0` (a label, not an error). Action Required shows two pre-existing provider warnings (proxy not bound, key missing) — those are pre-existing operational warnings, not regressions from MC-LIVE-REFRESH-1. |

## Verdict

**PASS** — all 8 spec checks green against the live server on commit 60bf1f3.

## Defects found

(none — all checks PASS)

## Notes / observations (non-blocking)

- `Playwright does not support chromium on ubuntu26.04-x64` from `python3 -m playwright install`. Worked around by using the existing Chrome-for-Testing binary at `/home/nofidofi/.agent-browser/browsers/chrome-149.0.7827.54/chrome`. The test script does this automatically.
- Test ordering matters: the page's 5s auto-ping keeps thor "live" while the page is open. To observe the live→non-live transition cleanly, the script closes the page, waits 130 s with no client, then re-opens.
- Pre-existing operational warnings in panel #3 (Action Required) — Hermes proxy port 8768 not bound, Minimax key missing in `.env` — are not caused by this commit and were already there. Not a regression.
- The "Logs / Health" panel still surfaces the literal word "Errors" because it labels a counter (`Errors: 0`). My initial test heuristic flagged this; the corrected heuristic only flags real error patterns (`TypeError`, `404`, `500`, `Failed to load`, etc.). Final test uses the corrected heuristic.

## Screenshots

- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-1-auto-refresh-before.png` (timestamp `01:35:18`)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-1-auto-refresh-after.png`  (timestamp `01:35:23`, Δ = 5 s)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-3-thor-card-before-agedout.png` (thor showing `9h ago`, after 130 s age-out)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-3-thor-card-after-live.png` (thor showing green `live` badge after fresh POST)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-5-thor-live-pulse.png` (focus on the `.live-pulse` element)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-6-thor-after-ageout.png` (thor back to log mtime after 130 s with no client)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-8-full-page.png` (above-the-fold snapshot during panel regression check)
- `/home/nofidofi/.hermes/image_cache/argus-mc-live-refresh-8-fullpage.png` (full-page snapshot, 1400 × 7064)

## Test artefacts

- Test script: `/home/nofidofi/NofiTech-Ind/01_projects/mission-control/qa/test_argus_mc_live_refresh.py`
- Raw JSON results: `/tmp/argus_mc_live_refresh_result.json`
- Final stdout: `{"overall_pass": true, "results": {"1": true, "2": true, "4": true, "5": true, "7": true, "8": true, "6": true, "3": true}}`
