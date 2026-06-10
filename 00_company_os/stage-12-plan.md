# Stage 12 Plan — Deployment Hardening (NOT YET APPROVED)

**Status:** Plan only. **Do not implement** until NOFI explicitly approves Stage 12.

## Goal
Address the deployment risks NOFI identified at Stage 10:
- No git repo → resolved at Stage 11 (item 1, git initialized, tag `mission-control-v1.7.0-mvp` created)
- No autostart → addressed in Workstream B below
- No auth → addressed in Workstream A below
- Hardcoded IP → resolved at Stage 11 (item 3, auto-detect via `_detect_lan_ip()`)
- Hardcoded port → Stage 11 keeps 8767 (no change, port now exposed in `/api/version` so future change is one-line)
- Demo tasks still visible → resolved at Stage 11 (item 2, demo/real/all filter added)
- Provider not connected → addressed in Workstream C below

## Three orthogonal workstreams

### Workstream A: Auth
- **Scope:** add basic auth (username + password) OR a shared URL token
- **Risks:** breaks existing browser bookmarks, breaks curl usage without `--user`, password storage in `.env`
- **Dependencies:** NOFI must choose: basic auth vs URL token vs both. Password must be strong. Key never leaks to UI.
- **Done looks like:** unauthenticated requests get 401; browser shows login box; correct creds work; `/api/data/*` still returns the same JSON once authenticated

### Workstream B: Autostart
- **Scope:** make the server survive host reboot. systemd user unit OR `@reboot` cron. `start-mc.sh` stays the manual path.
- **Risks:** if `start-mc.sh` has a bug, the autostart version has the same bug; user-level cron vs systemd choice matters for permission model
- **Dependencies:** NOFI must choose systemd vs cron; needs sudo OR user-level cron access on nofidofi-ThinkCentre
- **Done looks like:** after `sudo reboot`, dashboard is live within 60s, no manual intervention

### Workstream C: Provider integration
- **Scope:** wire up the **free** provider (Hermes proxy on 127.0.0.1:8768) for actual model calls. **NO paid integration without explicit NOFI approval** (per spend authority rule).
- **Risks:** real LLM calls consume tokens; Hermes proxy may not be running; rate limits; chat endpoint becomes a new attack surface (input validation, output escaping)
- **Dependencies:** Hermes proxy must be running; a real `/api/chat` endpoint must be added to `serve.py`; rate limiting; input length cap
- **Done looks like:** a `/api/chat` endpoint exists, calls the free model, returns a real response, shows token usage in the panel

## Explicit "do not implement" list
- No real auth code in this plan
- No real systemd/cron unit in this plan
- No real `/api/chat` endpoint in this plan
- No real `.env` creation in this plan

## Order of operations (if NOFI approves)
1. NOFI picks which workstream(s) to do
2. Sub-agent brief is created for that workstream (Forge builds, Argus verifies, real sub-agents)
3. Build + verify + NOFI approval for each
4. NOFI says "NOFI approves deployment." at the end

## Why three workstreams, not one big Stage 12
Each workstream is small enough to be a separate sub-agent brief (Build + Verify). They are independent (no shared code). NOFI can approve one, two, or all three.

## Estimated scope per workstream
- **A (auth):** ~50-80 lines in serve.py + ~20 lines in HTML. Estimated 1 sub-agent round (build + verify).
- **B (autostart):** ~10-15 lines in a new `nofitech-mc.service` file OR a single `crontab -e` line. Estimated 1 sub-agent round.
- **C (provider integration):** ~80-120 lines in serve.py (chat endpoint, history, rate limit). Estimated 1-2 sub-agent rounds.

## What this plan does NOT include
- HTTPS / TLS (out of scope; home LAN assumed)
- Reverse proxy (Nginx/Caddy) — separate workstream if NOFI wants
- Database / persistence — files-on-disk is locked as the storage layer
- Multi-user / roles — single-user assumed
- Mobile app — web is the only UI

## Risk if NOFI says "no Stage 12"
- MVP continues to work locally (no regression)
- Deployment risk list remains: no auth, no autostart, no public-internet safety
- Workaround: keep dashboard on local-only Wi-Fi, restart manually after reboot
