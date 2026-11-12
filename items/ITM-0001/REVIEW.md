# ITM-0001-BMC-RESET-MONITOR-UTILITY — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Remove rotation tests

1. **Overrides:** Plan r3 TSK-0006 To do 1 (rotation test file), To do 13, Done when 1, 5, and 6. Rotation-specific test obligations in Done when 3 and later task/acceptance gates are also removed. Other behavior and package restoration requirements remain.
2. **Decision:** Developer: "Remove these tests, proceed with the implementation". Remove active rotation tests and their exclusive harnesses. OS owns rotation policy. Keep production rotation integration, non-rotation tests, package restoration, and required hardware confirmation. Do not rerun archived rotation probes or claim removed coverage passed.
3. **Context:** Developer: "Where in the plan did we need to test logs rotation if I said that logs rotation is the target OS responsibility ?" Approved PLAN.md remains unchanged. Historical evidence remains preserved.
