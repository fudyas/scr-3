# MONIT and RAOM

RAOM selects safe or normal mode during SysV startup. MONIT supervises services from selected profile.
Package `scr-raom` delivers selector, reset-history API, and startup adapters. Client defines service inventory in both profiles.

## Profiles and configuration

| # | Path | Purpose |
| --- | --- | --- |
| 1 | `/etc/default/scr-raom` | Client reset threshold, window, NTP timeout, error policy, and profile paths. |
| 2 | `/etc/monit/monitrc` | Default normal profile. Client owns contents and includes. |
| 3 | `/etc/monit/raom/safe.monitrc` | Default safe profile. Shipped sample supervises existing `wd_keepalive` only. |
| 4 | `/run/scr-raom/selection` | Selected mode, profile, reason, and kernel boot identity. |
| 5 | `/run/scr-raom/monitrc` | Link to validated selected profile. |
| 6 | `/etc/monitrc` | Includes runtime profile for default MONIT CLI calls. |
| 7 | `/etc/default/monit` | Native enable flag and MONIT options. |

Defaults: `MAX_RESETS=5`, `RESET_WINDOW_SECONDS=900`, `NTP_SYNC_TIMEOUT_SECONDS=60`, and `SAFE_MODE_ON_ERROR=true`.
Invalid or unavailable client configuration discards partial values and selects safe mode with complete built-in defaults.
[RAOM operator guide](../src/tools/raom/README.md) defines configuration format, valid values, commands, and error reasons.

## Startup and mode selection

Native keepalive remains active during bounded logging/NTP bootstrap and NTP readiness wait.
RAOM consumes `scr-resets-monitor check` after synchronization. Reset API owns history and threshold calculation.

| # | Condition | Result |
| --- | --- | --- |
| 1 | Reset count exceeds configured threshold within window | Safe profile, regardless of error policy. |
| 2 | Valid reset evidence stays within threshold | Normal profile. |
| 3 | NTP timeout or unavailable reset evidence | Safe profile when error policy is true; normal profile when false. Error reason remains visible. |
| 4 | Invalid client configuration | Safe profile with complete built-in defaults. |
| 5 | Missing binary/profile, invalid syntax, unavailable state storage, or failed keepalive | Explicit failed startup. |

Mode and selected profile path remain fixed during current boot. Repeated starts and restarts reuse selection. Reboot evaluates configuration and reset evidence again.
MONIT validates selected profile before launch. Failed safe-profile startup never selects normal profile as fallback.
Client profile edits remain subject to MONIT syntax validation during service actions.

## SysV and CLI integration

Runlevels 2–5 use `S03monit` links to `/etc/init.d/scr-raom`. Scheduler identity remains `monit` for native dependency ordering.
RAOM owns automatic reset evaluation. Native startup prerequisites run after filesystem/network readiness and runlevel stop actions.

`src/tools/raom/etc/compat/` contains adapters installed at existing OS entry points:

| # | Adapter | Installed path | Behavior |
| --- | --- | --- | --- |
| 1 | `monit.init` | `/etc/init.d/monit` | Routes lifecycle actions through RAOM. Delegates read-only status directly to native init. |
| 2 | `monitrc` | `/etc/monitrc` | Resolves default CLI configuration through validated runtime profile. |
| 3 | `monitstate.sh` | `/sbin/monitstate.sh` | Invokes gated MONIT startup. |
| 4 | `rc.local` | `/etc/rc.local` | Preserves MONIT state and invokes gated startup alongside platform setup. |
| 5 | `watchdog.init` | `/etc/init.d/watchdog` | Serializes watchdog changes with planned MONIT stops and starts. |

Debian diversions retain native originals. dpkg installs adapters directly. Package callbacks never start daemons or reboot.
Native binaries, defaults, watchdog checks, and normal-profile contents remain platform/client dependencies.

Native keepalive feeds the hardware timer during selection and planned MONIT stops. RAOM verifies handoff before stopping MONIT.
The selected profile requests full watchdog after MONIT starts. The normal target profile requests it. The stock safe sample uses keepalive only.
Client safe profiles can request the same watchdog activation. Full watchdog checks the MONIT PID and native service status.

RAOM starts MONIT through native `start-stop-daemon` with explicit `-c` selected-profile argument.
An existing daemon must use same profile. Conflicting `MONIT_OPTS` configuration or PID arguments fail validation.
Normal-mode reload refreshes native service-health files before HUP. Safe-mode reload does not refresh normal service-health files.
Missing runtime selection makes default CLI configuration fail closed.

## Inspection

These root commands read selection and process state:

```bash
/usr/bin/scr-raom status
/usr/bin/scr-raom profile
/etc/init.d/monit status
```

`/usr/bin/scr-raom --help` shows supported arguments without root or service access.
`/etc/init.d/monit syntax` validates existing selected profile without starting daemon.

The safe sample contains no normal-profile includes or reboot recovery handlers. Client must supply required production safe services and their MONIT definitions.
Automated integration checks exercise installed selector, reset API, and MONIT syntax. Physical boot and watchdog behavior require exact-package hardware acceptance.
