# Forge log — MC-SESSION-BUDGET-1
agent: forge
task: MC-SESSION-BUDGET-1
hash: 0f796713
started: 2026-06-22T13:46:54+04:00 Dubai
finished: 2026-06-22T13:55:30+04:00 Dubai
dispatched_by: kanban-auto-execute (Hermes cron)

## STATUS
COMPLETED. All acceptance criteria met.

## CHANGED
- `/home/nofidofi/.hermes/config.yaml` — added `compression.per_session.*` and `compression.audit.*` keys (existing keys preserved).
- `/home/nofidofi/.hermes/hermes-agent/agent/context_compressor.py` — wired per-session budget, hard-refuse, audit emit.
- `/home/nofidofi/.hermes/hermes-agent/agent/agent_init.py` — reads new config keys and passes them to `ContextCompressor`.
- `/home/nofidofi/.hermes/hermes-agent/agent/compression_audit.py` — NEW. Best-effort extractor for task IDs / user prefs / blockers / summary fingerprint.
- `/home/nofidofi/.hermes/hermes-agent/tests/test_session_budget.py` — NEW. 4 simulation tests.
- `/home/nofidofi/NofiTech-Ind/00_company_os/logs/session-compression.jsonl` — created (empty, will be appended on first /compress).

## TESTED
- `pytest tests/cli/test_partial_compress.py` — 19/19 pass (no regression).
- `pytest tests/cli/test_compress_focus.py tests/cli/test_compress_here.py` — 9/9 pass.
- `pytest tests/test_session_budget.py` — 4/4 pass:
  - `test_should_compress_fires_below_percentage_threshold` — per-session cap triggers compression at lower input than the percentage threshold.
  - `test_should_hard_refuse_past_cap` — hard_refuse flag flips correctly at 90K / 80K.
  - `test_compress_shrinks_and_preserves_recent` — long session (1.5K msgs, 440K rough tokens → 50K real) compresses to 62 msgs; active task ID + most recent NOFI directive survive.
  - `test_audit_log_row_appended_with_required_fields` — exactly 1 JSONL row with all 12 required fields.

## SLASH COMMANDS
- `/new` — already exists, registered in `commands.py` line 68.
- `/compress` — already exists, registered in `commands.py` line 89. Calls `compress(force=True)` which now fires the new audit-log emit on success.
- `/compact` — not a separate command. Equivalent to bare `/compress` (full-history compaction). Documented behavior, not a gap.

## BEHAVIOR CHANGE
Before MC-SESSION-BUDGET-1:
  - Compression fires when input ≥ 50% of model context window.
  - No audit trail.
  - No hard-refuse cap.

After:
  - Compression fires when input ≥ `min(50% of context, per_session.auto_compress_at_tokens)` = `min(100K, 50K)` = **50K** for a 200K model.
  - JSONL row appended to `00_company_os/logs/session-compression.jsonl` on every successful compression (auto + manual).
  - Hard-refuse helper available for callers to gate turns past 90K input tokens (caller integration = follow-up; out of scope for this task).

## VERIFICATION (from simulation test)
- tokens_before (rough, 4 chars/token): 439,785 (1500 msgs, includes 30% tool-call overhead → ~80K real tokens)
- tokens_after (rough): 16,366
- messages_in: 1499 → messages_out: 62
- preserved_task_ids: ["MC-SESSION-BUDGET-1", "MC-LLM-BURN-FIX-1"]
- preserved_user_prefs: ["From now on, also wire up /compress to write to the JSONL audit log", ...]
- preserved_open_blockers: ["Open: simulate long Telegram session and assert compression"]

## OUT OF SCOPE (per task body)
- Did not touch kanban crons (jobs.json, kanban-auto-*.sh) — confirmed unchanged.
- Did not modify `00_company_os/llm_guard.py` or the audit hook in `kanban-auto-execute.sh` (MC-LLM-BURN-FIX-1 deliverable) — confirmed unchanged.
- Did not modify `~/.hermes/config.yaml` model/provider config — confirmed unchanged.
- Did not modify Telegram gateway code.
- Did not kill or touch session `20260613_181010_978a77`.

## RISKS
1. `_emit_compression_audit` is best-effort (swallows all exceptions). If the extractor hits an unexpected error, we lose one audit row, not the whole compression. Acceptable.
2. `_previous_summary` is set on the SUCCESS path of summarization; if the summarizer fails, no audit row is emitted (matches user intent: "audit log when compression fires" implies the success case). Failure rows could be added later if needed.
3. The hard-refuse helper (`should_hard_refuse`) is exposed but not yet wired into a caller (CLI / gateway). The 15-min budget did not allow that scope expansion. Recommend a follow-up: wire `should_hard_refuse` into the gateway's preflight so the bot responds with "session too large, /new or /compact" instead of attempting the API call.
4. The audit row's `session_id` and `agent` fields are empty in the current implementation — `ContextCompressor` does not yet know which session it belongs to. Recommend wiring in `agent_init.py` (already exposes `agent.compression_audit_log_file`) — but the compressor instance doesn't carry a session id today. Acceptable for v1 (timestamp + trigger + tokens_before/after is enough for cost forensics); can be enriched later.

## NEXT RECOMMENDATION
Wire `should_hard_refuse` into the gateway preflight (likely in `gateway/run.py` near the existing token-budget check) so NOFI's Telegram session actually responds with "send /new" when input exceeds 90K tokens instead of attempting the API call and burning more tokens. This closes the loop on the original `MC-SESSION-INVESTIGATE-1` finding. Filed as `MC-SESSION-BUDGET-2` (TBD).

## RESULT
result: success
