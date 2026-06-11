# NofiTech Event Schema (v1)

This document defines the JSON-Lines event log format used by NofiTech
Mission Control. Every meaningful workflow transition is recorded as
one line of JSON in:

    00_company_os/events.jsonl

The file is append-only. One event per line. UTF-8 encoded. No trailing
commas. Stdlib JSON in, stdlib JSON out.

The Mission Control server reads the last 50 events for the
`/api/data/events` endpoint, and the last 20 events for the Logs panel
(merged into `data_logs()`).

## Required fields (10)

| #  | Field         | Type    | Notes                                                       |
|----|---------------|---------|-------------------------------------------------------------|
| 1  | `ts`          | string  | ISO-8601 UTC timestamp, e.g. `2026-06-11T01:55:00+00:00`.   |
| 2  | `actor`       | string  | Who emitted the event: `nofi`, `thor`, `forge`, `argus`.    |
| 3  | `event_type`  | string  | One of the 14 allowed values below.                         |
| 4  | `project`     | string  | Project slug, e.g. `mission-control`. Empty string allowed. |
| 5  | `task_id`     | string  | Task id this event refers to. Empty string allowed.         |
| 6  | `title`       | string  | Short human-readable title. May be empty.                   |
| 7  | `message`     | string  | Free-form body. May be empty.                               |
| 8  | `status`      | string  | Status of the referenced task (or `pass`/`fail` for QA).    |
| 9  | `source_file` | string  | Originating file (relative to repo root) or empty.          |
| 10 | `schema`      | string  | Always `nofitech-event/v1`. Lets us version the format.     |

## Allowed `event_type` values (13)

| event_type        | Emitted by | When                                                |
|-------------------|------------|-----------------------------------------------------|
| `task_created`    | anyone     | A new task file is created.                         |
| `task_assigned`   | thor       | Thor assigns a task to a builder.                   |
| `task_completed`  | thor       | Thor marks a task complete after Argus passes.      |
| `task_failed`     | forge/thor | Task status moved to `failed`.                      |
| `task_cancelled`  | thor       | Task was stopped, not failed.                       |
| `work_started`    | forge      | Forge began the build phase.                        |
| `work_updated`    | forge      | Mid-build progress / blocker / field change.        |
| `forge_reported`  | forge      | Forge hands a build off to Argus.                   |
| `argus_started`   | argus      | Argus begins verification.                          |
| `argus_passed`    | argus      | Argus verified, result is `pass`.                   |
| `argus_failed`    | argus      | Argus rejected, result is `fail`.                    |
| `stage_advanced`  | thor       | The whole stage moved forward (Stage 14, etc.).     |
| `system_event`    | anyone     | Catch-all for ops / env / pipeline.                 |
| `fix_order`       | nofi       | **Stage 19:** Structured order receipt from a dashboard "Send fix order" button. Carries `order_id`, `recommended_fix`, `requires_chat_confirmation: true`. Thor ONLY acts on explicit chat phrase: `Thor, do it` or `Thor, execute pending order <order_id>`. Never auto-executes. |

## Validation rules

1. Every line MUST be valid JSON.
2. Every line MUST contain all 10 fields.
3. `ts` MUST be a valid ISO-8601 UTC string.
4. `event_type` MUST be one of the 14 allowed values.
5. `actor` MUST be one of the canonical agents (`nofi`, `thor`,
   `forge`, `argus`) or a documented extension (e.g. a future sub-agent).
6. `schema` MUST be `nofitech-event/v1` so future readers can detect
   format changes.

## Real example — Stage 14 wiring run

```jsonl
{"ts":"2026-06-11T01:00:00+00:00","actor":"nofi","event_type":"task_created","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"Verify automatic Mission Control task wiring","message":"Stage 14 brief approved. Forge to wire tasks+events into Mission Control.","status":"triage","source_file":"01_projects/mission-control/tasks/MC-LIVE-TEST-001.md","schema":"nofitech-event/v1"}
{"ts":"2026-06-11T01:05:00+00:00","actor":"thor","event_type":"task_assigned","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"MC-LIVE-TEST-001 assigned to forge","message":"","status":"assigned","source_file":"01_projects/mission-control/tasks/MC-LIVE-TEST-001.md","schema":"nofitech-event/v1"}
{"ts":"2026-06-11T01:10:00+00:00","actor":"forge","event_type":"work_started","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"Stage 14 build start","message":"Implementing schema, helper, and serve.py wiring.","status":"in_progress","source_file":"00_company_os/mc_event.py","schema":"nofitech-event/v1"}
{"ts":"2026-06-11T01:40:00+00:00","actor":"forge","event_type":"forge_reported","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"Stage 14 wiring implemented","message":"Schemas, helper, and serve.py edits done. Test task created. Handing off to Argus.","status":"in_progress","source_file":"01_projects/mission-control/code/serve.py","schema":"nofitech-event/v1"}
{"ts":"2026-06-11T01:42:00+00:00","actor":"argus","event_type":"argus_started","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"Verifying Stage 14","message":"Checking API responses and key-leak surface.","status":"in_progress","source_file":"","schema":"nofitech-event/v1"}
{"ts":"2026-06-11T01:50:00+00:00","actor":"argus","event_type":"argus_passed","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"Stage 14 verified","message":"All endpoints respond; MC-LIVE-TEST-001 visible; events.jsonl surfacing; no key leaks.","status":"pass","source_file":"","schema":"nofitech-event/v1"}
{"ts":"2026-06-11T01:55:00+00:00","actor":"thor","event_type":"task_completed","project":"mission-control","task_id":"MC-LIVE-TEST-001","title":"MC-LIVE-TEST-001 complete","message":"Stage 14 closed.","status":"complete","source_file":"01_projects/mission-control/tasks/MC-LIVE-TEST-001.md","schema":"nofitech-event/v1"}
```

## How it is read

Mission Control reads `events.jsonl` on every request. There is no cache.
This is fine because the file is small (kilobytes) and the read is a
single linear scan. If the file is missing, the API returns
`{events: [], reason: "No events yet."}` and the dashboard shows a
friendly empty state.
