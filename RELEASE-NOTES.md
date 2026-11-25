# Release notes

## 3.0.2 — Released (2026-11-25)

1. Administrators can request an orderly reboot with `scr-raom switch safe` or `scr-raom switch normal`. Safe mode persists until verified normal recovery.
2. Recovery acknowledges previous reset counts. An identified switch reboot with a BMC counter increase of one contributes zero resets. Larger increases count in full.
3. Both modes start the full native watchdog after RAOM verifies MONIT. Keepalive feeds the timer during boot selection and planned MONIT stops.
4. NTP readiness accepts a fresh selected `*` peer. Hardware decisions averaged 23 seconds across four boots. This result is not a startup guarantee.
5. The operator guide documents mode commands, reset accounting, boot order, and the NTP delay. Persistent safe boots skip NTP and threshold checks.

## 3.0.1 — Released

1. Select safe or normal mode at startup using configurable reset thresholds, NTP readiness, and error policy.
2. Start MONIT with the selected service profile. Coordinate watchdog activation and hardware timer feeding during startup and planned MONIT stops.
3. Deliver RAOM and the reset-history utility in one Debian package, with configuration and operator documentation.

The safe-profile sample in 3.0.1 supervises only `wd_keepalive`; full watchdog protection requires client configuration.
