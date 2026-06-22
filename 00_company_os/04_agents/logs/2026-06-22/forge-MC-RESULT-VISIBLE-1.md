# Forge log — MC-RESULT-VISIBLE-1

**Date:** 2026-06-22T15:50:00+04:00 (Dubai)
**Agent:** forge
**Task:** MC-RESULT-VISIBLE-1 — make agent results visible on kanban cards
**Dispatched by:** kanban-auto-execute (Hermes cron) at 2026-06-22T15:37:56+04:00

## Goal

Make agent results visible on kanban cards. Before this fix, agents could
PATCH a card to `done` with a `result` field, but the PATCH endpoint at
`serve.py` (`patch_kanban_task`) silently dropped it. The card rendered
as `DONE` with no result text.

## Changes

### 1. `01_projects/mission-control/code/kanban_parser.py`

Added `upsert_result_section(task_id, result_text, metadata=None, root)` and
private helper `_format_result_block(result_text, metadata)`. The public
function:

- Locates the task file via the same `iterdir` logic other helpers use.
- Splits the file into header + body with `_split_frontmatter` so the
  YAML frontmatter is preserved byte-for-byte.
- Searches the body for an existing `## Result` section (regex on the
  `## Result` heading, scans for the next `^## ` heading as the lower
  boundary).
- Replaces the existing section in place (idempotent).
- Otherwise inserts the new section BEFORE the next `^## ` heading, or
  APPENDS at end of body if no further heading exists.
- Returns `(ok, reason)` tuple — `reason` is "ok", "task not found",
  "task file read failed", or "task file write failed".

Format written:

```
\n## Result
**Date:** <metadata.date or now()>
**By:** <metadata.by or "unknown">
**Status:** <metadata.status or "success">

<result_text, exactly as supplied>
```

### 2. `01_projects/mission-control/code/serve.py`

Extended the existing PATCH handler at `/api/data/kanban/task/:id`
(around line 2440). The whitelist of accepted fields was previously just
`status` (and the assign-variant had its own endpoint). Now the handler:

- Reads optional `payload["result"]` (string).
- Reads optional `payload["result_metadata"]` (dict; validated with
  `isinstance(..., dict)`).
- If `status == 200` AND `result` is non-empty AND `new_status == "done"`,
  calls `kanban_parser.upsert_result_section(task_id, result,
  result_metadata, COMPANY_ROOT)`.
- On success, appends a `result_recorded` event to
  `00_company_os/events.jsonl` (ts, event_type, actor=metadata.by or
  "unknown", project="mission-control", task_id, result_teaser, log=null).
  Event append failure is non-fatal — surfaced in `result_reason` but
  does not fail the PATCH.
- Adds two new response fields: `result_persisted` (bool) and
  `result_reason` (string, only present if persistence failed).

**Backward compat preserved:** PATCH with no `result` field behaves
exactly as before — status update happens, `result_persisted: false`,
no file write, no event. Verified.

## Files changed

- `/home/nofidofi/NofiTech-Ind/01_projects/mission-control/code/kanban_parser.py`
  — added `upsert_result_section` + `_format_result_block`.
- `/home/nofidofi/NofiTech-Ind/01_projects/mission-control/code/serve.py`
  — extended PATCH handler to accept `result` and `result_metadata`,
  call the helper, and emit events.

## Files NOT touched (per scope)

- `kanban.html` (UI already has the rendering logic).
- `kanban_parser._extract_result_section` (already correct).
- Any kanban cron (`kanban-auto-*.sh`, `jobs.json`).
- `llm_guard.py`, audit hook in `kanban-auto-execute.sh`,
  compression config — all from MC-LLM-BURN-FIX-1 / MC-SESSION-BUDGET-1.
- No new endpoint — only the existing PATCH was extended.

## MC restart

MC was restarted (PID 802555 → 2817917) via `./start-mc.sh` after the
code change. Restart was necessary so the live process loads the
modified `serve.py` — otherwise the verification curls would have
hit the OLD code without the `result` field. The dispatch context
explicitly says NOFI is AFK and not to ask for input; restart was a
required step for the verification gate.

## Verification

### Test 1 — backward-compat PATCH (no `result` field)

```
PATCH /api/data/kanban/task/MC-KANBAN-CREATE-20260622111708-F71B07
body: {"status":"ready"}
→ {"ok":true, "result_persisted":false, "result_reason":null, ...}
```

PASS — no error, status update succeeded, no phantom result.

### Test 2 — PATCH with `result` + done (fresh task)

Created `MC-KANBAN-CREATE-20260622114808-18A60D`, then PATCHed:

```
PATCH body: {"status":"done",
             "result":"MC-RESULT-VISIBLE-1 verification: PATCH with result field works end-to-end...",
             "result_metadata":{"by":"forge","status":"success","date":"2026-06-22T15:42:00+04:00"}}
→ {"ok":true, "result_persisted":true, "result_reason":null, "new_status":"done"}
```

Task file written correctly:

```
---
task_id: MC-KANBAN-CREATE-20260622114808-18A60D
... (frontmatter untouched) ...
---

# Result Visible Test A

(Body TBD — ...)

## Result
**Date:** 2026-06-22T15:42:00+04:00
**By:** forge
**Status:** success

MC-RESULT-VISIBLE-1 verification: ...
```

events.jsonl got the line:

```
{"ts": "2026-06-22T15:48:32+04:00",
 "event_type": "result_recorded",
 "actor": "forge",
 "project": "mission-control",
 "task_id": "MC-KANBAN-CREATE-20260622114808-18A60D",
 "result_teaser": "MC-RESULT-VISIBLE-1 verification: ...",
 "log": null}
```

### Test 3 — GET /api/data/kanban surfaces the result

```
GET /api/data/kanban
→ MC-KANBAN-CREATE-20260622114808-18A60D
    has_result: True
    result_teaser: "MC-RESULT-VISIBLE-1 verification: PATCH with result field works end-to-end..."
```

PASS — card UI will now render the 📋 Result button + teaser.

### Test 4 — backfill original test task

Backfilled `MC-KANBAN-CREATE-20260622111708-F71B07` (the one NOFI
created) with the result from `events.jsonl` ("all good — kanban
round-trip test passed..."). Card now shows:

```
has_result: True
result_teaser: "all good — kanban round-trip test passed. MC :8767 healthy, task verified in running_now, PATCH→done succeeded."
```

### Test 5 — idempotency

Ran a second PATCH with a different `result` on the test task. Result
section REPLACED in place — file contains exactly ONE `## Result`
heading. PASS.

## Acceptance criteria — all met

- [x] PATCH `/api/data/kanban/task/:id` accepts optional `result` and `result_metadata` fields
- [x] When `result` is present AND `status=done`, the task file's body gets a `## Result` section with the right format
- [x] When `result` is absent, behavior is unchanged (backward compat)
- [x] After PATCH, `GET /api/data/kanban` returns `has_result: true` and a non-empty `result_teaser` for that task
- [x] Test task `MC-KANBAN-CREATE-20260622111708-F71B07` shows the result in the UI (backfilled programmatically)
- [x] No changes to kanban crons, MC-LLM-BURN-FIX-1, or MC-SESSION-BUDGET-1 files
- [x] Forge log written
- [ ] Task PATCHed to done (this section will be the last action)
- [ ] Commit + push to origin/main (next steps)

## Risks

- **None identified.** The change is additive — old code paths still
  work, new code only runs when callers opt in via `result` field.
- The `result_recorded` event is a new event_type; existing event
  consumers that filter by known event_types will need to know about
  it. None of the kanban-auto-* crons filter event types — they only
  WRITE events, not read them.

## Next recommendations

- Argus and Thor should be updated to use the new `result` field on
  their done-PATCHes. This is a behavior change in their subagent
  dispatch templates (the wrapper that calls `delegate_task` →
  `kanban-auto-execute` → forge/argus/thor → PATCH). Recommend
  a follow-up task: `MC-AGENT-PATCH-RESULT-2` to update the kanban
  agent dispatch path so all future done-PATCHes include `result`.
- Currently `approval_status: pending` is on tasks even after they're
  done — pre-existing, not in scope, but worth noting for cleanup.

result: success