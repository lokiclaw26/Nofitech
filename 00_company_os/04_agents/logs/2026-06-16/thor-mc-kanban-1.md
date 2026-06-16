---
task_id: MC-KANBAN-1
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-16T18:55:00Z
---

# Thor Coordination Log — MC-KANBAN-1

## NOFI's request (verbatim)
"in mission control i want you to make a new tab/Page for Hermes Agent Kanban .... now prepare and setup multi-agent via the kanban in UI... prepare it for our team setup 3 members ... Thor forge and argus"

## What I (Thor) did — orchestration only, 0 implementation bytes

1. **Investigated source material** (read-only):
   - Fetched https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban (got the full reference)
   - Fetched https://hermes-agent.nousresearch.com/docs/user-guide/features/kanban-tutorial (got the 4 use-case stories)
   - Skipped the X video (not needed — docs cover it comprehensively)

2. **Distilled the data model** from the docs:
   - SQLite at ~/.hermes/kanban.db (but we WON'T use it — we have our own task file system at 01_projects/*/tasks/)
   - Status flow: triage → todo → ready → running → blocked → done (+ archived)
   - Per-profile swimlanes inside Running column (perfect for Thor/Forge/Argus)
   - REST API under /api/plugins/kanban/* (we'll mirror the shape but at /api/data/kanban/*)
   - CLI: hermes kanban (we WON'T use — not installed, we use delegate_task)
   - Tool calls: kanban_create, kanban_complete, etc. (we WON'T use — we orchestrate manually)

3. **Saved the reference as a skill** at `~/.hermes/skills/hermes-kanban-reference/SKILL.md` so Forge can read it before starting implementation. This makes the data model + REST surface + config keys instantly accessible without re-fetching the docs.

4. **Created the task file** at `01_projects/mission-control/tasks/MC-KANBAN-1.md` with:
   - 5 parts (A: GET endpoint, B: PATCH endpoint, C: HTML section, D: agent wiring, E: Argus verification)
   - 12 acceptance criteria
   - Explicit decision to NOT use external `hermes kanban` CLI or `~/.hermes/kanban.db` — instead reuse our existing project task files
   - Status mapping table (project task status → kanban status)
   - Handoff sections for both Forge (build) and Argus (verify)

5. **Logged 3 events** to events.jsonl: task_created, skill_saved, task_orchestrated

6. **Updated state.json**: thor/forge/argus all assigned to MC-KANBAN-1

## Architectural decision (locked by Thor for this task)

**Reuse existing project task files** as the kanban data source, NOT external Hermes kanban DB.

Reasoning:
- We already have 30+ task files at `01_projects/*/tasks/*.md` with proper frontmatter
- We do NOT have `hermes kanban` CLI installed on this machine
- We do NOT have `~/.hermes/kanban.db`
- Adding a new DB would create a new source of truth, violating the "page reads disk" rule
- Our existing task file frontmatter already has: task_id, title, status, priority, created_by, assigned_to, approval_status, current_assignment — that's 90% of the kanban data model
- Forge only needs to write a parser (`kanban_parser.py`) that reads all `*/tasks/*.md` files and groups by status

This means the kanban board is **synchronized with the rest of Mission Control automatically** — moving a card on the kanban updates the source task file, which other endpoints (Overview, Tasks, Agents) read from the same source.

## What I (Thor) will NOT do
- I will not edit serve.py
- I will not edit mission-control.html
- I will not write kanban_parser.py
- I will not create the new task files via UI (that's for NOFI via the page after delivery)
- I will not touch the existing 11 endpoints

## What happens next
- Forge sub-agent builds Parts A-D (probably hits 600s limit, will need retry)
- Argus sub-agent verifies (Part E)
- I (Thor) coordinate, log, commit, push

## Open questions for NOFI
None blocking. The scope is clear from NOFI's request. If NOFI wants auto-decompose or WebSocket later, that's a follow-up task.

## Memory notes
- This is the first task where the scope is "rebuild a feature from another product in our own stack" — not new development
- Decision pattern: prefer reusing existing data sources over adding new ones
- If we ever DO want to integrate with the real Hermes Kanban, the data is already structured to be exported
