# ITM-0001-BMC-RESET-MONITOR-UTILITY — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Remove rotation tests

1. **Overrides:** Plan r3 TSK-0006 To do 1 (rotation test file), To do 13, Done when 1, 5, and 6. Rotation-specific test obligations in Done when 3 and later task/acceptance gates are also removed. Other behavior and package restoration requirements remain.
2. **Decision:** Developer: "Remove these tests, proceed with the implementation". Remove active rotation tests and their exclusive harnesses. OS owns rotation policy. Keep production rotation integration, non-rotation tests, package restoration, and required hardware confirmation. Do not rerun archived rotation probes or claim removed coverage passed.
3. **Context:** Developer: "Where in the plan did we need to test logs rotation if I said that logs rotation is the target OS responsibility ?" Approved PLAN.md remains unchanged. Historical evidence remains preserved.

## D-02 — Proceed with next task and preserve source images

1. **Overrides:** Historical quarantine/recovery holds as prerequisites to starting TSK-0008, including plan r3 TSK-0008 To do 6/6.1 and conflicting retained-hold wording. Approved PLAN.md remains unchanged.
2. **Decision:** Developer: "Drop all quaranteed / blocks now. You must proceed autonomously preserving images under var/ intact for future reuse. Resume, don't stop too much".
3. **Decision:** Developer correction: "Correction: the dance around old SDLC is taking too long. Just proceed to the next task". Proceed with TSK-0008 implementation and fresh verification. Do not spend task execution on retired SDLC recovery ceremonies.
4. **Boundary:** Original image/kernel bytes and metadata under var/ remain preserved. Mutable verification uses disposable copies. Historical records remain evidence, never fabricated restoration or runtime success.
5. **Boundary:** Current source-integrity, package ownership, reversibility, isolated execution, cleanup, independent validation, and truthful result reporting remain. D-01 remains effective. Device operations and exact-revision SHOW approval remain separate.
