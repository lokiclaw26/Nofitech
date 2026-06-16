---
task_id: MC-KANBAN-2-DUAL-FORMAT-PARSER
agent: thor
role: CEO / Orchestrator
project: mission-control
status: in_progress
created: 2026-06-16T19:36:00Z
---

# Thor Coordination Log — MC-KANBAN-2

## NOFI's decision (verbatim)
*"I choose Option 2: Extend the Kanban parser to read both task formats. Do not normalize all 50 task files right now. The board should support existing historical markdown-table task files as well as newer YAML frontmatter task files."*

## What I (Thor) did — orchestration only, 0 implementation bytes

1. **Investigated the 50/52 format gap** (read-only):
   - `find /home/nofidofi/NofiTech-Ind/01_projects -name "*.md" -path "*/tasks/*" | wc -l` → 52 files
   - Format A (YAML frontmatter): 2 files (MC-KANBAN-1, MC-AGENT-LOG-FIX-1)
   - Format B (markdown table `| Field | Value |`): 50 files (all DIY-*, most MC-*)
   - The DIY-011 file confirmed Format B uses `id` (not `task_id`), `owner` (not `assigned_to`), `created_at` (not `created`)
   - NOFI's choice (don't mass-convert) is correct — would have been ~50 file rewrites with risk of losing nuance

2. **Identified the data-loss bug** from MC-KANBAN-1's Argus log:
   - PATCH overwrites the file's `status:` field with the kanban column value
   - Round-trip: PATCH `running` then PATCH back to `in_progress` → API rejects `in_progress` (not a kanban status)
   - Result: data loss. Must be fixed.

3. **Wrote the task file** at `01_projects/mission-control/tasks/MC-KANBAN-2-DUAL-FORMAT-PARSER.md` with:
   - Full spec for Format A + Format B parsing
   - Field mapping table (Format B → canonical)
   - PATCH fix algorithm (kanban_status separated from status)
   - Edge cases (missing kanban_status row, both formats in one file, etc.)
   - 5 parts (parser, PATCH fix, data_kanban update, git tag, verification)
   - 12 acceptance criteria
   - Explicit forbidden list (no mass-convert, no silent rename, no status removal)
   - Detailed handoff to Forge + Argus

4. **Logged 4 events**: task_created, task_assigned, work_started, task_orchestrated

5. **Updated state.json**: thor/forge/argus → MC-KANBAN-2-DUAL-FORMAT-PARSER

## Architectural decision (locked)

**Separate `kanban_status` from `status`** — this is the cleanest fix:
- `status` = project/task lifecycle (in_progress, complete, blocked, pending, approved, archived) — NEVER touched by Kanban
- `kanban_status` = board column (triage, todo, ready, running, blocked, done, archived) — written by PATCH only
- Both fields coexist in the file
- For Format A: YAML frontmatter gets both keys
- For Format B: two table rows (`| **status** | in_progress |` and `| **kanban_status** | running |`)

This way, NOFI can drag a card on the Kanban UI, and the project's `in_progress` lifecycle status stays intact. The drag just adds a `kanban_status: running` row.

## What I (Thor) will NOT do
- 0 bytes of implementation
- Will not edit kanban_parser.py
- Will not edit serve.py
- Will not edit mission-control.html
- Will not add the git tag (Forge does that)
- Will not modify any task file
- Will not commit (Forge + Argus do that)

## Memory note
- This is the 3rd task in a row where I delegate properly (MC-GITHUB-PANEL-1 was messy, MC-AGENT-LOG-FIX-1 was clean, MC-KANBAN-1 was clean, this is clean)
- Pattern: NOFI picks a direction → I write the task spec → I delegate to Forge → Forge ships → Argus verifies → I write the final coordination log
- 11+ tool calls per task is normal
- The 600s budget for Forge keeps getting hit, but they always ship 90%+. The pattern works.

## Open follow-ups (not in this task)
- If Argus finds anything wrong, MC-KANBAN-3 will be needed
- If everything passes, Kanban can be frozen
- After freeze, consider: drag-drop persistence, real-time WebSocket, auto-decompose, profile-based permissions

## What happens next
- Forge: backup + refactor parser + fix PATCH + add tag + commit + push + log
- Argus: verify A-F checks + log + state.json + commit + push
- Thor: append final events + write final log + commit + push
