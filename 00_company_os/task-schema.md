# NofiTech Task Schema (v1)

This document defines the YAML frontmatter that every task file under
`01_projects/<project>/tasks/*.md` MUST follow. Mission Control and the
helper script `mc_event.py` both read this frontmatter; inconsistent
fields break the dashboard silently.

A task file is a Markdown document. The first block is YAML frontmatter
between `---` markers. Everything after the second `---` is free-form
body (description, evidence, links, etc.) and is not parsed by the
wiring.

## Required frontmatter fields (14)

| # | Field          | Type    | Notes                                                            |
|---|----------------|---------|------------------------------------------------------------------|
| 1 | `id`           | string  | Unique task id, e.g. `MC-LIVE-TEST-001`. Used as primary key.    |
| 2 | `title`        | string  | Short, human-readable title.                                     |
| 3 | `project`      | string  | Project slug under `01_projects/`, e.g. `mission-control`.        |
| 4 | `created_by`   | string  | Who created the task (`nofi`, `thor`, `forge`, `argus`, etc.).   |
| 5 | `assigned_to`  | string  | Current owner (`forge`, `argus`, `thor`, `nofi`, etc.).          |
| 6 | `status`       | string  | One of the allowed values below.                                 |
| 7 | `priority`     | string  | `low` \| `normal` \| `high` \| `urgent`.                         |
| 8 | `created_at`   | string  | ISO-8601 UTC timestamp (e.g. `2026-06-11T01:00:00+00:00`).       |
| 9 | `updated_at`   | string  | ISO-8601 UTC timestamp. Bumped on every frontmatter change.      |
| 10| `current_stage`| string  | Free-form pipeline stage: `triage`, `build`, `qa`, `ship`, etc.  |
| 11| `blocker`      | string  | Short blocker description, or empty string.                      |
| 12| `data_source`  | string  | `real` for live tasks. `local-demo` for Stage 6 demo data.       |
| 13| `description`  | string  | One-paragraph task description.                                  |
| 14| `acceptance`   | string  | Concrete acceptance criteria — what proves the task is done.    |

Legacy Stage 6 demo tasks use a different shape (`agent`, `created`,
`updated`, `blockers`, `argus_result`, `evidence`). The helper script
and Mission Control wiring treat those as legacy and only the 14 fields
above are authoritative for new work.

## Allowed values for `status`

| Status        | Meaning                                                   |
|---------------|-----------------------------------------------------------|
| `triage`      | Just created, not yet assigned or scoped.                 |
| `assigned`    | Thor has assigned a builder. Work has not started.        |
| `in_progress` | Builder is actively working.                              |
| `verification`| Argus is verifying.                                       |
| `complete`    | Done and verified. Final state.                           |
| `failed`      | Attempt failed, cannot proceed.                           |
| `blocked`     | Cannot progress until a dependency / input arrives.       |
| `cancelled`   | Stopped, not failed.                                      |

Transitions that the wiring understands:

* `triage` → `assigned` (Thor assigns, appends `task_assigned` event)
* `assigned` → `in_progress` (Forge starts, appends `work_started`)
* `in_progress` → `verification` (Forge hands off, appends `forge_reported`)
* `verification` → `complete` (Argus passes, appends `argus_passed` + `task_completed`)
* `verification` → `in_progress` (Argus rejects, appends `argus_failed` + `work_updated`)
* any → `failed` (`task_failed` event)
* any → `blocked` (`work_updated` event)
* any → `cancelled` (`task_cancelled` event)

## Real example — MC-LIVE-TEST-001

```markdown
---
id: MC-LIVE-TEST-001
title: Verify automatic Mission Control task wiring
project: mission-control
created_by: nofi
assigned_to: forge
status: complete
priority: normal
created_at: 2026-06-11T01:00:00+00:00
updated_at: 2026-06-11T01:55:00+00:00
current_stage: ship
blocker: ""
data_source: real
description: Stage 14 live wiring test. Verifies that creating a real task file makes it appear in Mission Control after refresh, that status changes are reflected, that assignment shows, and that events.jsonl entries surface in the Logs/Activity panel.
acceptance: Task appears in dashboard; status changes visible; events.jsonl entries visible; no demo data shown by default.
---

## Notes

- Created by `mc_event.py create_task` (or equivalent).
- Status walk: `assigned` → `in_progress` → `complete`.
- Paired with 7 events in `00_company_os/events.jsonl`.
```

## Validation rules

1. `id` must be unique within the project's `tasks/` directory.
2. `data_source` MUST be `real` for any task created after Stage 12.
3. `status` MUST be one of the allowed values, lowercased.
4. `created_at` and `updated_at` MUST be valid ISO-8601 timestamps.
5. The body (after the second `---`) is optional but recommended for
   long-lived tasks.

If any of these rules is broken, Mission Control will still render the
task (best effort) but `mc_event.py` will refuse to update it.
