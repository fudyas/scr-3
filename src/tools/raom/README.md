# RAOM boot selection

`scr-resets-monitor` 1.1.0 delivers RAOM selector and reset-history API in one Debian package. RAOM starts one MONIT with selected safe or normal profile.

Client owns production profile contents. Shipped safe sample supervises existing `wd_keepalive` only. Sample supplies no SSH, Cloudflare, or remote-access guarantee.

## Configuration

`/etc/default/scr-raom` contains data, never shell code. All six keys required. Values use unquoted `KEY=value` lines. Blank lines and whole-line comments allowed.

```text
N=5
M=900
K=60
SAFE_MODE_ON_ERROR=true
SAFE_PROFILE=/etc/monit/raom/safe.monitrc
NORMAL_PROFILE=/etc/monit/monitrc
```

| # | Key | Contract |
| --- | --- | --- |
| 1 | `N` | Reset limit, integer `0..2147483647`. Strictly more than N selects safe. |
| 2 | `M` | Reset window in seconds, integer `1..2147483647`. |
| 3 | `K` | NTP readiness budget in seconds, integer `1..2147483647`. |
| 4 | `SAFE_MODE_ON_ERROR` | Literal `true` or `false`. False permits normal selection on decision errors. |
| 5 | `SAFE_PROFILE` | Absolute safe-profile path. Built-in path `/etc/monit/raom/safe.monitrc`. |
| 6 | `NORMAL_PROFILE` | Absolute normal-profile path. Built-in path `/etc/monit/monitrc`. |

Missing, unreadable, malformed, partial, duplicate-key, or unknown-key configuration discards all supplied values. Complete built-in defaults apply, including `SAFE_MODE_ON_ERROR=true`.
Quoted values, shell expansions, and inline comments are not shell syntax here. Profile paths cannot contain control characters or equal `/`.
Numeric limits prevent overflow. Client selects production N/M/K values.

## Boot behavior

1. PRESERVE native keepalive after filesystem/network prerequisites and runlevel stop actions.
2. START native logging and NTP through bounded init operations.
3. START monotonic K deadline at decision entry, after native bootstrap attempt.
4. ***if*** bootstrap succeeds ***then*** POLL local `ntpq -c 'rv 0'` until ready or deadline.
5. ***if*** NTP is ready ***then*** CALL `/usr/bin/scr-resets-monitor check --max-resets N --window M`.
6. SELECT profile from API result and error policy.
7. STORE complete selection atomically under `/run/scr-raom/selection`, with kernel boot identity.
8. VALIDATE selected MONIT profile before launch.
9. START selected instance through native `start-stop-daemon`.

Keepalive remains active during wait. Native bootstrap uses separate bounded budgets. K covers NTP readiness, not total service startup.
Linux `/proc/uptime` supplies deadline. Wall-clock jumps cannot extend wait. Reset API alone calculates reset threshold and refreshes history.

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

Commands require root. Inspection commands do not start services:

```bash
/usr/bin/scr-raom status
/usr/bin/scr-raom profile
/usr/bin/scr-resets-monitor status --json
```

`status` prints `schema`, `boot_id`, `mode`, `profile`, and `reason`. `profile` prints selected path. Both require existing current-boot selection.
`select` creates selection without MONIT launch. Service entry handles native bootstrap before first selection.
Exit `0` means complete selection, including safe mode. Exit `2` means unavailable operation. Selection alone never proves successful MONIT launch.

`/etc/init.d/scr-raom start` and MONIT `start`, `restart`, `force-reload`, `reload`, and `syntax` use RAOM adapter.
MONIT `stop`/`status` delegate original init script through Debian diversion. `/etc/default/monit` stays unchanged, including native `START` enable flag.
Conflicting `MONIT_OPTS` profile/PID arguments fail startup. Running instance must expose selected explicit `-c` path.

`/sbin/monitstate.sh` uses gated start. Default `/etc/monitrc` includes `/run/scr-raom/monitrc`, published after syntax validation.
Missing runtime selection makes default CLI configuration fail closed. Narrow `/etc/rc.local` replacement removes historical MONIT state deletion.
Runlevels 2–5 retain scheduler identity `monit`; `S03monit` targets `scr-raom`. Obsolete `S17scr-resets-monitor` observation hook no longer runs.

Missing binary/profile, invalid MONIT syntax, or unusable runtime filesystem means failed launch. Failed safe launch never substitutes normal profile.
Normal `/etc/monit/monitrc`, MONIT binaries, and watchdog payload stay outside package changes. Existing OS services continue independently.

## Package migration and rollback

Package installs operational files directly under `/usr/local/scr/`. `/usr/bin/scr-raom` links to `/usr/local/scr/bin/src-raom`.
Reset CLI remains `/usr/bin/scr-resets-monitor`, linked to `/usr/local/scr/bin/src-resets-monitor`.
Debian diversions retain native compatibility paths under `/usr/share/scr-resets-monitor/diverted/`. Standard conffiles preserve client configuration.
Package callbacks never start services, feed watchdog, or reboot. Explicit device authority remains necessary for target actions.

1. RETAIN exact prior `.deb`, version/hash, client configuration, and history evidence before authorized upgrade.
2. INSTALL new archive through `dpkg --install /absolute/scr-resets-monitor_1.1.0_all.deb`.
3. RETAIN conffile choices during supported reinstall or 1.1.x upgrade.
4. ***if*** rollback to retained 1.0.6/1.0.7 is required ***then*** USE these two operations in order:
   4.1. REMOVE 1.1.0 through `dpkg --remove scr-resets-monitor`.
   4.2. INSTALL retained archive through `dpkg --install /absolute/scr-resets-monitor_1.0.7_all.deb` or exact retained 1.0.6 archive.

Direct in-place downgrade to 1.0.6/1.0.7 is unsupported and can leave MONIT missing. Remove-before-install restores diverted originals first.
Removal retains conffiles and reset history. Purge removes package conffiles, but retains reset history and historical legacy backup evidence.
Retained 1.0.x private backups remain historical migration evidence. New package uses dpkg ownership/diversions rather than generic private-payload copying.
Foreign ownership/diversion conflicts and unsupported native compatibility content remain errors. Package does not repair global package inventory.

## Focused verification and acceptance limits

`test/check-integration.sh` installs built application and dependency fixtures through real `.deb` archives in approved disposable Debian root.
Actual installed selector consumes actual reset CLI. SEMA/NTP fixture dependencies supply controlled observations without hardware access.
Private mount/PID namespace supplies `/proc`. Real MONIT syntax checks never start daemons. Missing supported target MONIT evidence blocks V9.

Decision fixtures cover V1–V3. Boot fixtures cover V4–V6. Debian lifecycle checks cover V7–V8. Installed integration covers V9. This guide covers V10.
Focused results do not replace independent QA, repository gates, locked source-image acceptance, exact-pair SHOW, promotion, or developer hardware confirmation.
