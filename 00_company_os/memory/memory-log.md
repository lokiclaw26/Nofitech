
### 011. (2026-06-18 01:12 Dubai) Argus mandatory before "shipped"
NOFI caught that Thor shipped MC-LIVE-DASHBOARD-1 and MC-LIVE-REFRESH-1 with self-test only. Argus's last log was 9 hours stale. Thor is now required to dispatch Argus for verification BEFORE claiming "shipped ✓". Self-test (curl, unittest) is Thor's job, not verification. Self-verify only for trivial fixes (<10 lines well-specified) or with explicit NOFI approval. Full rule at 00_company_os/auto-kanban-rule.md (addendum 1).
