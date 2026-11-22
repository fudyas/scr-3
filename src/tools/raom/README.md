# RAOM boot selection

`scr-raom` 1.1.0 delivers RAOM selector and reset-history API in one Debian package. RAOM starts one MONIT with selected safe or normal profile.

Client owns production profile contents. Shipped safe sample supervises existing `wd_keepalive` only.

## Configuration

`tool.sh` loads trusted `etc/raom.conf` for runtime paths and fallback profile paths. Shared SCR libraries supply logging and root checks.
Client policy lives in `/etc/default/scr-raom`. This file contains data, never shell code. All six keys required.
Values use unquoted `KEY=value` lines. Blank lines and whole-line comments allowed.

```text
MAX_RESETS=5
RESET_WINDOW_SECONDS=900
NTP_SYNC_TIMEOUT_SECONDS=60
SAFE_MODE_ON_ERROR=true
SAFE_PROFILE=/etc/monit/raom/safe.monitrc
NORMAL_PROFILE=/etc/monit/monitrc
```

| # | Key | Contract |
| --- | --- | --- |
| 1 | `MAX_RESETS` | Reset limit, integer `0..2147483647`. Strictly more resets selects safe. |
| 2 | `RESET_WINDOW_SECONDS` | Reset window in seconds, integer `1..2147483647`. |
| 3 | `NTP_SYNC_TIMEOUT_SECONDS` | NTP readiness budget in seconds, integer `1..2147483647`. |
| 4 | `SAFE_MODE_ON_ERROR` | Literal `true` or `false`. False permits normal selection on decision errors. |
| 5 | `SAFE_PROFILE` | Absolute safe-profile path. Built-in path `/etc/monit/raom/safe.monitrc`. |
| 6 | `NORMAL_PROFILE` | Absolute normal-profile path. Built-in path `/etc/monit/monitrc`. |

Missing, unreadable, malformed, partial, duplicate-key, or unknown-key configuration discards all supplied values. Complete built-in defaults apply, including `SAFE_MODE_ON_ERROR=true`.
Quoted values, shell expansions, and inline comments are not shell syntax here. Profile paths cannot contain control characters or equal `/`.
Numeric limits prevent overflow. Client selects production threshold, reset window, and NTP timeout.

## Boot behavior

1. HAND OFF full watchdog to native `wd_keepalive` at runlevel `K01watchdog stop`. The following `S01wd_keepalive start` keeps that feeder running.
2. START native logging and NTP through bounded init operations.
3. START monotonic `NTP_SYNC_TIMEOUT_SECONDS` deadline at decision entry, after native bootstrap attempt.
4. ***if*** bootstrap succeeds ***then*** POLL local `ntpq -c 'rv 0'` until ready or deadline.
5. ***if*** NTP is ready ***then*** CALL reset API with `MAX_RESETS` and `RESET_WINDOW_SECONDS`.
6. SELECT profile from API result and error policy.
7. STORE complete selection atomically under `/run/scr-raom/selection`, with kernel boot identity.
8. VALIDATE selected MONIT profile before launch.
9. START selected instance through native `start-stop-daemon`.
10. VERIFY native MONIT executable, PID, and selected `-c` argument while RAOM holds its lock.
11. ***if*** selected profile requests watchdog startup ***then*** TRANSFER feeding to native watchdog after verification of selected MONIT.

Keepalive remains active during wait. Native bootstrap uses separate bounded budgets. `NTP_SYNC_TIMEOUT_SECONDS` covers NTP readiness after bootstrap.
Linux `/proc/uptime` supplies deadline. Wall-clock jumps cannot extend wait. Reset API alone calculates reset threshold and refreshes history.

Each new service decision writes one timing record to stderr and native syslog with tag `scr-raom`.
Fields are `boot_id`, `mode`, `reason`, and `decision_ms`. Elapsed time starts before the service hands feeding to keepalive and bootstraps logging and NTP.
Timing ends immediately after selection publication. It includes NTP readiness wait and any reset API call. Clock resolution is 10 ms.
Earlier SysV actions, lock wait, MONIT startup, and cached service calls are outside this measurement.
If timing is unavailable, `decision_ms=unavailable`. A logging error leaves the decision intact. Compare fresh decisions with the same NTP conditions and policy.

| # | Evidence | Selection |
| --- | --- | --- |
| 1 | API exit `0` | Normal, `reason=below_threshold`. |
| 2 | API exit `1` | Safe, `reason=threshold_exceeded`, regardless of error flag. |
| 3 | API exit `2` | Error, `reason=reset_evidence_unavailable`. Flag chooses safe/normal. |
| 4 | Unexpected API exit | Error, `reason=reset_api_failed`. Flag chooses safe/normal. |
| 5 | NTP timeout/bootstrap failure | Error, `reason=ntp_timeout` or `ntp_start_failed`. Flag chooses safe/normal. |
| 6 | Invalid configuration | Safe with complete built-in defaults, `reason=configuration_invalid`. |
| 7 | Unavailable clock | Error, `reason=clock_unavailable`. Flag chooses safe/normal where state publication remains possible. |

Errors remain visible on stderr and in retained reason. Error-permitted normal selection never means reliable evidence proved threshold clear.
Unavailable keepalive, runtime storage, boot identity, or selection publication can prevent startup entirely.

Selection fixes mode and profile path for current boot. Repeated starts/restarts reuse selection. Configuration edits take effect on next boot.
Selected profile contents remain client-managed. No automatic same-boot return to normal. New boot reevaluates retained reset history.

## Installed interfaces

Help works without root or runtime access. Other commands require root. Inspection commands do not start services:

```bash
/usr/bin/scr-raom --help
/usr/bin/scr-raom status
/usr/bin/scr-raom profile
/usr/bin/scr-resets-monitor status --json
```

`status` prints `schema`, `boot_id`, `mode`, `profile`, and `reason`. `profile` prints selected path. Both require existing current-boot selection.
`select` creates selection without MONIT launch. Service entry handles native bootstrap before first selection.
If full watchdog is active, standalone `select` returns `watchdog_not_idle`. The service entry can perform the required handoff.
Exit `0` means complete selection, including safe mode. Exit `2` means unavailable operation. Selection alone never proves successful MONIT launch.

MONIT `start`, `stop`, `restart`, `force-reload`, `reload`, and `syntax` use RAOM. Native MONIT `status` reads process state without taking the RAOM lock.
`/etc/default/monit` supplies the native `START` enable flag.
Conflicting `MONIT_OPTS` profile/PID arguments fail startup. Running instance must expose selected explicit `-c` path.

`/sbin/monitstate.sh` uses gated start. Default `/etc/monitrc` includes `/run/scr-raom/monitrc`, published after syntax validation.
Missing runtime selection makes default CLI configuration fail closed. `/etc/rc.local` preserves MONIT state and invokes gated startup.
Runlevels 2–5 use scheduler identity `monit`; `S03monit` targets `scr-raom`. RAOM owns automatic reset evaluation during boot.

Missing binary/profile, invalid MONIT syntax, or unusable runtime filesystem means failed launch. Failed safe launch never substitutes normal profile.
Platform supplies normal `/etc/monit/monitrc`, MONIT and watchdog binaries, and native watchdog checks.

## Watchdog protection

The normal profile on SCR-7CCC91 requests full watchdog through `99-watchdog`. That daemon checks the MONIT PID file and runs `/sbin/monit-status.sh`.
The stock safe profile supervises only `wd_keepalive`. This feeds the hardware timer. Full watchdog does not check MONIT in stock safe mode.
A client safe profile can request full watchdog through `/etc/init.d/watchdog start`. The same selection and process checks apply in both modes.
The native watchdog takes over hardware feeding from keepalive. A client profile must choose the feeder it supervises.

Before planned MONIT stop or restart, RAOM stops full watchdog and verifies its absence. RAOM then starts or verifies native keepalive before MONIT can stop.
RAOM requires the keepalive executable before stopping full watchdog. Bounded `start-stop-daemon --status --exec` verifies the actual keepalive process after handoff.
The parent holds the same lock through restart. A concurrent watchdog request must acquire this lock and verify the current selected daemon.
After restart, the selected profile can request full watchdog again. If MONIT stays stopped, keepalive continues feeding.
If keepalive handoff fails, RAOM preserves the MONIT PID and reports failure. It attempts to restore the previous full watchdog only against the verified selected MONIT.
If neither feeder can be verified, hardware feeding is unconfirmed.

## Startup adapters

`etc/compat/` contains installed adapters for existing OS entry points. These files keep native startup and CLI calls on selected RAOM profile.

| # | Source | Installed path | Purpose |
| --- | --- | --- | --- |
| 1 | `monit.init` | `/etc/init.d/monit` | Routes lifecycle actions through RAOM. Native status stays lock-free for watchdog checks. |
| 2 | `monitrc` | `/etc/monitrc` | Includes validated `/run/scr-raom/monitrc` for default MONIT CLI calls. |
| 3 | `monitstate.sh` | `/sbin/monitstate.sh` | Starts MONIT through gated init entry. |
| 4 | `rc.local` | `/etc/rc.local` | Runs gated startup and platform setup while preserving MONIT state. |
| 5 | `watchdog.init` | `/etc/init.d/watchdog` | Gates activation on selected running MONIT. Stop hands feeding to native keepalive. |

## Debian delivery

Package installs operational files directly under `/usr/local/scr/`. `/usr/bin/scr-raom` links to `/usr/local/scr/bin/src-raom`.
Reset CLI remains `/usr/bin/scr-resets-monitor`, linked to `/usr/local/scr/bin/src-resets-monitor`.
Debian diversions retain native compatibility paths under `/usr/share/scr-raom/diverted/`. Standard conffiles preserve client configuration.
Package callbacks never start services, feed watchdog, or reboot. Build both commands with `./bin/lets deb build etc/deb/raom/deb.conf`.
On an authorized system, install `pkg/scr-raom_1.1.0_all.deb` with `dpkg --install`.
Foreign ownership, active diversions from another package, and unsupported native integration files stop installation.
For a same-package rollback, install the retained `scr-raom` archive with dpkg. Keep local conffiles when prompted.
`dpkg --remove scr-raom` restores native startup paths and retains client policy. Purge deletes package conffiles.
Before a change of package owner, keep an offline copy of live reset data and client configuration through rollback.

## Focused verification and acceptance limits

`test/check-integration.sh` installs built application and dependency fixtures through real `.deb` archives in approved disposable Debian root.
Actual installed selector consumes actual reset CLI. SEMA/NTP fixture dependencies supply controlled observations without hardware access.
Private mount/PID namespace supplies `/proc`. Real MONIT syntax checks never start daemons.
Decision and boot checks cover selection, bounded waits, startup ordering, and launch failures. Package checks cover dpkg lifecycle and configuration preservation.
Physical boot and watchdog behavior require hardware acceptance with exact package.
