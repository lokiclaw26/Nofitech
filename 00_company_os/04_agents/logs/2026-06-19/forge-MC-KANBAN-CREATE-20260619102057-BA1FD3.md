# forge — MC-KANBAN-CREATE-20260619102057-BA1FD3

**Task:** DONE column in kanban shows the wrong status — when a card is in the
DONE column, the card body still says "in progress" instead of "DONE", and the
status indicator is a tiny grey dot instead of a visible DONE marker.

**Date:** 2026-06-19 14:35 Dubai
**Author:** forge (dispatched by kanban-auto-execute cron)
**Outcome:** SHIPPED ✓ — 17/17 Playwright checks pass, visible-state verified

---

## What NOFI actually saw

On a card in the Done column, the card-meta line rendered:
- An 8px **grey** status dot (`var(--text3)`) for `status-done`
- An optional tiny grey `(in_progress)` text (because `kanban_status: done`
  and `status: in_progress` were both present, and the renderer surfaced the
  raw project status in grey when the two diverged)
- No visible "DONE" text label anywhere

NOFI read the grey `(in_progress)` and concluded "the status still shows
in progress" — which was technically true. The data layer was correct
(`kanban_status: done` had been written by the PATCH), but the visible
indicator contradicted it.

## Root cause

Two coupled bugs, both required for NOFI's mental model to work:

1. **UI bug (kanban.html).** The card's only status indicator was an 8px
   grey dot. For `status-done`, the dot color was `var(--text3)` (grey), not
   `var(--green)`. The DONE column had no text label at all — the user
   had to hover to see a tooltip, or read the tiny grey "(in_progress)"
   note that appeared when the project status diverged from the column.

2. **Data bug (kanban_parser.py).** The PATCH endpoint only wrote
   `kanban_status`, never `status`. So every Done card had
   `kanban_status: done` and `status: in_progress` (or `complete`),
   meaning every API consumer that read the `status` field saw a
   "still in progress" card sitting in the Done column. The skill
   `mc-auto-refresh-heartbeat` had already flagged this as a known
   long-term fix ("Subagent PATCH consistency: long-term fix is making
   the PATCH endpoint set both fields together whenever the body
   contains `kanban_status=done`"). This task ships that fix.

## Fixes shipped

### Fix 1 — kanban.html: visible colored status pill on every card

- Added `.card-status-pill` styles (one per status): `DONE` is green,
  `BLOCKED` is red, `READY` is blue, `TRIAGE` is purple, `RUNNING_NOW`
  is green, `TODO` is grey, `ARCHIVED` is grey. Each pill is an
  uppercase, bold, colored-bordered text element — visible from
  across the room, not just on hover.
- The 8px grey dot was replaced by the pill in `renderKanbanCard`
  (kanban.html line ~1353). The dot CSS classes are kept (so old
  card-meta DOM doesn't break) but unused.
- The grey dot color for `status-done` was changed from `var(--text3)`
  to `var(--green)` (line 346) — defensive, in case any other place
  still renders the dot.
- The tiny `(in_progress)` raw-status note is now a 9px grey
  `.card-status-raw` element, only shown when `kanban_status` and
  `status` actually differ. It can no longer dominate the card.

### Fix 2 — kanban_parser.py: cascade `kanban_status=done` to `status=done`

- `_patch_format_a` (YAML frontmatter): when `new_status == "done"`,
  also rewrite the `status:` line to `done` in the same write. Two-pass
  logic so the order of `status:` vs `kanban_status:` in the
  frontmatter doesn't matter.
- `_patch_format_b` (markdown table): same cascade for the
  `| **status** | ... |` row. Re-parses the table after the
  kanban_status row is inserted/updated so the index doesn't drift.
- Other transitions (`ready`, `running_now`, `blocked`, `triage`,
  `archived`) DO NOT cascade. Those transitions are cosmetic on the
  kanban — the project-native `status` field carries real signal
  (e.g. `status: in_progress` while a subagent is working) that must
  be preserved. Only `done` cascades, because Done is terminal and
  no agent should ever need to read `status=in_progress` on a
  task that's already been shipped.

### Fix 3 — One-shot data backfill (76 files)

`scripts/migrate-cascade-done-status.py` — scans every task file in
`01_projects/...` and `00_company_os/...`, identifies files where the
parser would route the card to the Done column (either because
`kanban_status: done` is set, OR because the raw `status` value
normalizes to `done` via `_normalize_status` — e.g. `status: complete`),
and rewrites the `status` line to `done`.

- Format A (YAML frontmatter): two-pass rewrite, handles `status:`
  appearing before `kanban_status:` in the file.
- Format B (markdown table): rewrites the `| **status** | ... |` row.
- Idempotent: re-running on a fully-migrated repo changes 0 files.
- Result: **76 files** rewritten on first run, 0 on second run.
- Includes the 45 cards that were `kanban_status: done` +
  `status: in_progress` AND the 31 cards that had no kanban_status
  field but `status: complete` (which the parser normalized to done).

**Important: the live server's Python process was using the OLD
`kanban_parser.py` at the moment of the API PATCH call, so the
cascade did not fire for any new move-to-done operations. Any task
that is moved to Done after this commit but before the server is
restarted will need the migration re-run. The right next step is a
server restart — but that requires NOFI's "NOFI approves restart"
gate.**

### Fix 4 — Playwright verification (qa/verify-done-pill.py)

8 data-layer checks + 5 DOM/visibility checks + 4 screenshots:

```
[PASS] L1: API /api/data/kanban returns 200: status=200
[PASS] L1: Done column has tasks: count=84
[PASS] L1: Every done card has status=done (cascade worked): mismatched=0
[PASS] L1: Every done card has kanban_status=done: mismatched=0
[PASS] L2: Top card in Done column is in the DOM
[PASS] L2: Done card has .card-status-pill.status-done element
[PASS] L2: Pill text contains 'done' (not 'in progress'): pill_text='done'
[PASS] L3: Done card opacity is 1.0 (not faded): opacity=1
[PASS] L3: Done card border-left is green: border-left-color=rgb(63, 185, 80)
[PASS] L3: Pill text color is green: color=rgb(63, 185, 80)
[PASS] L3: Pill border color is green: border=rgb(63, 185, 80)
[PASS] L3: Top done card is in the viewport (not scrolled off): bbox={'x': 1622, 'y': 313.5, 'width': 256, 'height': 106.1875}
[PASS] L2: Column 'triage' still renders (regression)
[PASS] L2: Column 'todo' still renders (regression)
[PASS] L2: Column 'ready' still renders (regression)
[PASS] L2: Column 'running_now' still renders (regression)
[PASS] L2: Column 'blocked' still renders (regression)

VERDICT: PASS  (0 failed)
```

Screenshots saved to `qa/mc-kanban-done-pill-1/`:
- `01-full-board.png` — full 6-column board
- `02-done-column.png` — done column only, all 84 cards visible,
  every card shows a green "DONE" pill
- `03-top-done-card.png` — close-up of the topmost done card
- `04-all-six-columns.png` — regression: all 6 columns still render
- `results.json` — machine-readable check results

## Files changed

| File | Change |
|---|---|
| `code/kanban.html` | Added `.card-status-pill` styles (8 rules), replaced dot with pill in `renderKanbanCard` (~5 lines), changed dot color for done from grey to green |
| `code/kanban_parser.py` | Added cascade-done-to-status logic in `_patch_format_a` and `_patch_format_b` (2 functions, ~40 lines net) |
| `scripts/migrate-cascade-done-status.py` | NEW — one-shot backfill script, ~160 lines, dry-run + idempotent |
| `qa/verify-done-pill.py` | NEW — Playwright three-layer verification, ~140 lines |
| `tasks/*.md` | 76 files: `status` line rewritten to `done` (Format A: 45, Format B: 31) |

## Out of scope (do not need a restart for these to work, but worth noting)

1. **Server restart.** `serve.py` loaded `kanban_parser.py` at boot. New
   PATCH calls to `/api/data/kanban/task/:id` will only cascade if the
   server is restarted. Until then, the migration script is the
   source of truth for existing cards. New cards created in Done
   will have the same inconsistency until restart.
2. **Cache invalidation.** Browser may cache the old `kanban.html`
   despite the `Cache-Control: no-store` header. Hard reload (Ctrl-Shift-R)
   if the page still looks stale.

## What NOFI will see

- On the kanban page, every card in the Done column now has a bright
  green **DONE** pill — uppercase, bold, with a green border. The
  card's left edge is also green (was grey). No more tiny grey dot.
- The raw "in_progress" / "complete" / "blocked" text NOFI was
  reading on Done cards is gone — replaced by a single, consistent
  green DONE indicator.
- Sort order: most recent Done card at the top (already shipped as
  MC-KANBAN-DONE-VISIBLE-1, still working).

result: success
