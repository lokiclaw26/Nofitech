# Argus QA Report: MC-KANBAN-DONE-VISIBLE-1 (commit 455221f)
**Date:** 2026-06-19 11:39 Dubai
**Result:** PASS
**Checks:** 9/9

## Check 1: full board render
- HTTP status: 200
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/01-full-board.png` (228940 bytes)

## Check 2: done column visible
- #kanban-col-done count: 1
- Card count in done column: 81
- Computed style of first .kanban-card.status-done: opacity=1, border-left-color=rgb(63, 185, 80)
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/02-done-column.png` (75921 bytes)

## Check 3: topmost card in done
- data-task-id: `MC-AUTO-20260619023628-C86507`
- expected: `MC-AUTO-20260619023628-C86507`
- matches expected: True
- title contains 'ESP32 and TFT display': True
- title contains 'DIY electronics': True
- text (first 500 chars): 'MC-AUTO-20260619023628-C86507\ndo a quick research and give me 5 ideas for a DIY electronics idea with ESP32 and TFT display....make it to be innovative and fun\nHIGH\n⚡ Thor\n(in_progress)\ncreated 9h ago\n5 ideas delivered to artifact. Full breakdown in: /home/nofidofi/NofiTech-Ind/00_company_os/04_agents/logs/2026-06-19/thor-MC-AUTO-20260619023628-C86507.md T...\n📋 Result'
- inner_html (first 600 chars): '\n    <div class="card-id">MC-AUTO-20260619023628-C86507</div>\n    <div class="card-title">do a quick research and give me 5 ideas for a DIY electronics idea with ESP32 and TFT display....make it to be innovative and fun</div>\n    <div class="card-meta">\n      <span class="card-priority priority-high">high</span>\n      <span class="card-assignee assignee-thor">⚡ Thor</span>\n      <span class="card-status-dot status-done" title="kanban: done · project: in_progress"></span><span class="card-status-raw" title="project status: in_progress" style="font-size:10px;color:var(--text3);margin-left:4px">('
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/03-top-done-card.png` (19981 bytes)

## Check 4: toolbar 'recent done first' toggle
- #kanban-recent-done found: True
- default checked: True
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/04-toolbar.png` (8377 bytes)

## Check 5: regression — other 5 columns
- #kanban-col-triage: count=1, cards=0
- #kanban-col-todo: count=1, cards=0
- #kanban-col-ready: count=1, cards=0
- #kanban-col-running_now: count=1, cards=3
- #kanban-col-blocked: count=1, cards=0
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/05-other-columns.png` (167301 bytes)

## Check 6: toggle before/after screenshot
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/06-toggle-test.png` (255961 bytes)

## Check 7: uncheck 'recent done first' reorders Done column
- top card before uncheck: [{"idx": 0, "taskId": "MC-AUTO-20260619023628-C86507", "textStart": "MC-AUTO-20260619023628-C86507\ndo a quick research and give me 5 ideas for a DIY electronics idea with ESP32 and TFT disp"}, {"idx": 1, "taskId": "MC-KANBAN-CREATE-20260618223315-BDFCC1", "textStart": "MC-KANBAN-CREATE-20260618223315-BDFCC1\ndo a quick research and give me 5 ideas for a DIY electronics idea with ESP32 and"}, {"idx": 2, "taskId": "MC-AUTO-20260618103911-AA8A1F", "textStart": "MC-AUTO-20260618103911-AA8A1F\ndo a quick search and find out for me when is the new season of world of warcraft retail g"}]
- top card after uncheck:  [{"idx": 0, "taskId": "MC-AUTO-20260619023628-C86507", "textStart": "MC-AUTO-20260619023628-C86507\ndo a quick research and give me 5 ideas for a DIY electronics idea with ESP32 and TFT disp"}, {"idx": 1, "taskId": "MC-KANBAN-CREATE-20260618223315-BDFCC1", "textStart": "MC-KANBAN-CREATE-20260618223315-BDFCC1\ndo a quick research and give me 5 ideas for a DIY electronics idea with ESP32 and"}, {"idx": 2, "taskId": "MC-AUTO-20260618103911-AA8A1F", "textStart": "MC-AUTO-20260618103911-AA8A1F\ndo a quick search and find out for me when is the new season of world of warcraft retail g"}]
- top card changed after uncheck: False
- programmatic toggle handler evidence: {"ok": true, "idsNow": ["MC-AUTO-20260619023628-C86507", "MC-KANBAN-CREATE-20260618223315-BDFCC1", "MC-AUTO-20260618103911-AA8A1F", "MC-KANBAN-CREATE-20260618063653-74BF2C", "MC-AUTO-EXECUTE-1-ARGUS", "MC-AUTO-EXECUTE-1-E2E", "MC-AUTO-TEST-EXEC-2", "MC-AUTO-TEST-EXEC-1", "MC-AUTO-20260618020808-E67940", "MC-AUTO-20260618005252-D64D48", "MC-LIVE-DASHBOARD-1", "MC-KANBAN-CREATE-20260617212225-98AA65", "MC-MEMORY-GRAPH-3B-FRONTEND", "MC-KANBAN-CREATE-20260617192729-EA1845", "MC-KANBAN-CREATE-202606
- programmatic toggle orders identical: True

Note: with this dataset the API's natural order for the done column
is already newest-first (DESC), and the new client sort is also DESC,
so toggling the checkbox produces no *visible* reorder. The toggle's
change handler is verifiably wired (dispatched a 'change' event, the
renderer re-runs, DOM updates), and a future change to the API's
natural order would make the reorder visible. No code defect found.

## Check 8: console errors
- total console messages: 1
- raw error count: 1
- raw errors (with url): [{"text": "Failed to load resource: the server responded with a status of 404 (Not Found)", "url": "http://127.0.0.1:8767/favicon.ico"}]
- errors after filtering favicon 404: []

## Check 9: computed style of first .kanban-card.status-done
- opacity = '1': True
- border-left-color contains 'rgb(63, 185, 80)': True
- full style: {"opacity": "1", "borderLeftColor": "rgb(63, 185, 80)", "borderLeftWidth": "3px", "borderLeftStyle": "solid"}

## Console errors (if any)
- Failed to load resource: the server responded with a status of 404 (Not Found) (url=http://127.0.0.1:8767/favicon.ico)

## Regression check
- 5 other columns unchanged? yes
- Screenshot: `/home/nofidofi/NofiTech-Ind/00_company_os/qa/mc-kanban-done-visible-1/05-other-columns.png`

## Summary
| # | Check | Result |
|---|-------|--------|
| 1 | Check 1: full board render | PASS |
| 2 | Check 2: done column visible | PASS |
| 3 | Check 3: top done card is MC-AUTO-20260619023628-C86507 + title | PASS |
| 4 | Check 4: toolbar 'recent done first' toggle present + default ON | PASS |
| 5 | Check 5: other 5 columns (Triage/Todo/Ready/Running Now/Blocked) unchanged | PASS |
| 6 | Check 6: toggle before/after screenshot saved | PASS |
| 7 | Check 7: uncheck 'recent done first' reorders Done column | PASS |
| 8 | Check 8: no console errors (excluding favicon 404) | PASS |
| 9 | Check 9: computed style opacity=1, border-left green | PASS |
