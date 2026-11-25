# Release notes

## 3.0.2 — Planned

1. Administrators can request an orderly reboot with `scr-raom switch safe` or `scr-raom switch normal`. Safe mode persists until verified normal recovery.
2. Recovery acknowledges previous reset counts. An identified switch reboot with a BMC counter increase of one contributes zero resets. Larger increases count in full.
3. Both modes start the full native watchdog after RAOM verifies MONIT. Keepalive feeds the timer during boot selection and planned MONIT stops.

## 3.0.1 — Released

1. Configurable reset thresholds, time windows, and error policy select the safe or normal MONIT profile at boot.
2. One Debian package delivers the RAOM command and reset-history API. Client profiles define supervised services.
3. RAOM coordinates native watchdog and keepalive handoffs. The supplied safe sample supervises keepalive only.
