# Token Budget Mode — NofiTech Ind.

**Enabled:** 2026-06-10
**Authority:** NOFI (final)
**Mode:** Default unless NOFI says "Full detailed report."

## Purpose
Reduce token usage while keeping work quality, verification, and normal workflow.

## Rules (19, locked)
1. Do not repeat the full NofiTech protocol after it is saved.
2. Do not repeat agent role definitions unless requested.
3. Do not repeat previous stage reports.
4. Do not paste full code files unless NOFI asks.
5. Do not paste full logs unless needed for debugging.
6. Do not paste full directory trees unless requested.
7. Use file paths and short summaries.
8. Store detailed notes in project files.
9. Use compact reports in chat.
10. Inspect only relevant files.
11. Build one stage at a time.
12. Freeze completed stages.
13. Use pass/fail checklists.
14. If something passes, report it in one line.
15. If something fails, explain only the failure, evidence, and next fix.
16. Ask before producing long documentation.
17. Never reduce verification quality to save tokens.
18. Never skip Argus QA to save tokens.
19. Never say done without proof.

## Default chat report format

```
STATUS: Verified / Partial / Failed

CHANGED:
- file: short note

TESTED:
- command/page: result

ARGUS: Pass / Fail + reason

BLOCKERS:
- blocker or none

NEXT:
- next action
```

## Override
NOFI may say "Full detailed report." to switch back to the long form for one response.
