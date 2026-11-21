# ITM-0007-RAOM-SYSV-STARTUP-SERVICE — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Configure RAOM decision and MONIT profiles

1. **Overrides:** Initial brief sections 5–6 and 8, preliminary MONIT-independent startup recommendation, and customer email requirement against MONIT loading RAOM services. No approved plan exists.
2. **Decision:** Developer: "The RAOM service runs after NTP is available" and "The service launches MONIT with the safe/normal mode configuration".
3. **Decision:** Developer: "Create a default configuration for the service with >N resets in M seconds - such that YOU can test it, the RAOM client will configure their values".
4. **Decision:** Developer: "RAOM needs to enter safe mode if no NTP sync occured for more than K seconds (configurable)".
5. **Decision:** Developer answered "YES" to RAOM reading configuration and calling `scr-resets-monitor check --max-resets N --window SECONDS`. Existing utility owns threshold calculation. No duplicate counter algorithm.
6. **Decision:** Developer: "Yes, we still need monitoring the safe mode services, no reason to duplicate monit's job". MONIT owns safe/normal profile service supervision. Do not add parallel RAOM supervision.
7. **Decision:** Developer: "It is now 192.168.68.52". Supersedes 192.168.68.54 as inspection target.
8. **Boundary:** Planning and read-only inspection only. No package install, service restart, watchdog operation, reboot, or physical output authorized here.
9. **Pending:** Non-NTP exit-2 policy, exact timing boundary, and boot-mode persistence remain proposed design details for concrete plan review. NTP timeout safe-mode behavior is settled.
