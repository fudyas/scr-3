# MONIT and RAOM

RAOM selects safe or normal mode during SysV startup. MONIT supervises services from selected profile.
Package `scr-raom` delivers selector, reset-history API, and startup adapters. Client defines service inventory in both profiles.

## Profiles and configuration

| # | Path | Purpose |
| --- | --- | --- |
| 1 | `/etc/default/scr-raom` | Client reset threshold, window, NTP timeout, error policy, and profile paths. |
| 2 | `/etc/monit/monitrc` | Default normal profile. Client owns contents and includes. |
| 3 | `/etc/monit/raom/safe.monitrc` | Default safe profile. Shipped sample monitors the full native watchdog through its PID file. |
| 4 | `/run/scr-raom/selection` | Selected mode, profile, reason, and kernel boot identity. |
| 5 | `/run/scr-raom/monitrc` | Link to validated selected profile. |
| 6 | `/etc/monitrc` | Includes runtime profile for default MONIT CLI calls. |
| 7 | `/etc/default/monit` | Native enable flag and MONIT options. |
| 8 | `/var/lib/scr-raom/decision` | Persistent safe latch, pending switch, and reset evidence. |

Defaults: `MAX_RESETS=5`, `RESET_WINDOW_SECONDS=900`, `NTP_SYNC_TIMEOUT_SECONDS=60`, and `SAFE_MODE_ON_ERROR=true`.
Invalid or unavailable client configuration discards partial values and selects safe mode with complete built-in defaults.
[RAOM operator guide](../src/tools/raom/README.md) defines configuration format, valid values, commands, and error reasons.

## Startup and mode selection

Native keepalive feeds the hardware timer during logging and NTP startup. Each startup command has a 10-second budget.
When evaluation needs NTP, RAOM waits up to 60 more seconds by default. Native network services can run. MONIT-managed services and full watchdog checks wait.
A timeout records a decision error. Persistent safe mode skips this readiness wait and the threshold check.

| # | Condition | Result |
| --- | --- | --- |
| 1 | Reset count exceeds configured threshold within window | Safe profile, regardless of error policy. |
| 2 | Valid reset evidence stays within threshold | Normal profile. |
| 3 | NTP timeout or unavailable reset evidence | Safe profile when error policy is true. Normal profile when false. Error reason remains visible. |
| 4 | Invalid client configuration | Safe profile with complete built-in defaults. |
| 5 | Missing binary/profile, invalid syntax, unavailable private decision storage, or failed keepalive | Explicit failed startup. |
| 6 | Safe latch with no bound normal request | Use safe profile again. Manual, threshold, and error-triggered safe entry persist. |

Mode and selected profile path remain fixed during current boot. Repeated starts and restarts reuse selection. Root can request the opposite mode through `scr-raom switch safe` or `scr-raom switch normal`. Exit 0 confirms reboot submission.
MONIT validates selected profile before launch. Failed safe-profile startup never selects normal profile as fallback.
Normal recovery requires a fresh, durable pre-reboot BMC acknowledgment. RAOM refuses reboot if capture or request storage fails.
Either identified switch exempts exactly +1. A larger increase counts in full. Ordinary reboots retain their resets.
Incomplete reboot evidence gives no exemption. When timing cannot decide the window, the configured error policy applies.

## SysV and CLI integration

Runlevels 2–5 use `S03monit` links to `/etc/init.d/scr-raom`. Scheduler identity remains `monit` for native dependency ordering.
RAOM owns automatic reset evaluation. Native startup prerequisites run after filesystem/network readiness and runlevel stop actions.

`src/tools/raom/etc/compat/` supplies the native entry adapters.

| # | Adapter | Installed path | Behavior |
| --- | --- | --- | --- |
| 1 | `monit.init` | `/etc/init.d/monit` | Routes lifecycle actions through RAOM. Delegates read-only status directly to native init. |
| 2 | `monitrc` | `/etc/monitrc` | Resolves default CLI configuration through validated runtime profile. |
| 3 | `monitstate.sh` | `/sbin/monitstate.sh` | Invokes gated MONIT startup. |
| 4 | `rc.local` | `/etc/rc.local` | Preserves MONIT state and invokes gated startup alongside platform setup. |
| 5 | `watchdog.init` | `/etc/init.d/watchdog` | Serializes watchdog changes with planned MONIT stops and starts. |
| 6 | `wd_keepalive.init` | `/etc/init.d/wd_keepalive` | Guards native requests from SysV and retained client profiles against a competing feeder. |

Debian diversions retain the native originals. Debian alternatives selects the packaged keepalive adapter through `/etc/alternatives/scr-raom-wd-keepalive`. Package callbacks never start daemons or reboot.
Native binaries, defaults, watchdog checks, and normal-profile contents remain platform/client dependencies.

Native keepalive feeds the hardware timer during selection and planned MONIT stops. RAOM verifies handoff before stopping MONIT.
RAOM activates the full native watchdog in both profiles after it verifies the selected MONIT.
Native watchdog checks the MONIT PID and native service status. MONIT supervises client services.
A retained safe profile can call the native keepalive entry. The adapter keeps an active full watchdog in control.
A planned MONIT stop requires verified keepalive. Restart requires a new verified handoff to the full watchdog.

RAOM starts MONIT through native `start-stop-daemon` with explicit `-c` selected-profile argument.
An existing daemon must use same profile. Conflicting `MONIT_OPTS` configuration or PID arguments fail validation.
Normal-mode reload refreshes native service-health files before HUP. Safe-mode reload does not refresh normal service-health files.
Missing runtime selection makes default CLI configuration fail closed.

## Inspection

These root commands read selection and process state.

```bash
/usr/bin/scr-raom status
/usr/bin/scr-raom profile
/etc/init.d/monit status
/etc/init.d/watchdog status
/etc/init.d/wd_keepalive status
```

`/usr/bin/scr-raom --help` shows supported arguments without root or service access.
`/etc/init.d/monit syntax` validates existing selected profile without starting daemon.

The safe sample contains no normal-profile includes or reboot recovery handlers. Client must supply required production safe services and their MONIT definitions.
RAOM clears safe after it verifies the current normal decision, the exact MONIT daemon, the full watchdog as sole feeder, and the completion save.
Physical boot, native shutdown accounting, and watchdog behavior require verification with the exact package on the target.
