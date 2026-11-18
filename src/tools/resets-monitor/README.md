# Reset monitor

`scr-resets-monitor` records existing BMC counters through Bash and the installed SEMA utility.
Hardware access is read-only: `/usr/bin/sema cap all`. The utility never changes counters, firmware, watchdogs, or boot policy.

## Source layout

1. `src/bin/src-resets-monitor` is the sole command entry point. Source-tree use loads project configuration, shared libraries, runtime modules, and the tool command layer.
2. `src/tools/resets-monitor/tool.sh` defines usage, argument parsing, command dispatch, and `main()`.
3. `src/tools/resets-monitor/src/runtime/` holds runtime modules. `history.sh` handles storage and journal/cache commits. `record.sh` handles observations. `time.sh` handles clock and reset-window calculations.
4. `test/` holds all checks, the SSH runner, and captured fixtures. `pkg/` holds Debian controls and callbacks. `etc/` holds configuration.
5. The Debian package copies the complete repository `src/` subtree to `/usr/local/scr/`.
6. `/usr/bin/scr-resets-monitor` links to `/usr/local/scr/bin/src-resets-monitor`. The entry loads shared libraries, configuration, runtime modules, and `tool.sh` from that tree.
7. The package also installs its SysV and logrotate integrations under `/etc/`. The Bash runtime has no LETS dependency.
8. Developer API entry: `./src/bin/src-resets-monitor --help`. Build and checks use the LETS commands below.

## Observation command

```bash
/usr/bin/scr-resets-monitor record
```

1. `record` requires root. Exit 0 means history and its state cache are committed. Exit 2 means unavailable or failed.
2. SEMA has at most two attempts. Each attempt has a two-second timeout and one-second termination allowance.
3. Captured stdout and stderr have file-size limits. Output over 64 KiB, embedded NUL bytes, incomplete fields, and unsuccessful commands fail.
4. Counter capacity is `0..4294967295`. This parser limit does not assert firmware counter width or rollover behavior.
5. Controller identity, firmware, and last restart cause have a 256-byte limit. Unknown cause text remains diagnostic data.
6. Separate capability declarations never replace observed counter or cause fields.

## Files and schema

| # | Path | Purpose |
| --- | --- | --- |
| 1 | `/var/log/scr/resets.jsonl` | Authoritative observation history. One versioned JSON object per line. |
| 2 | `/var/log/scr/resets-state.json` | Latest committed observation cache. Never an independent baseline. |
| 3 | `/var/log/scr/resets-monitor.log` | Commit, error, and discontinuity diagnostics. |
| 4 | `/run/lock/scr-resets-monitor.lock` | Stable invocation lock, with a two-second wait limit. |

1. Log directory is root-owned, mode `0700`. Owned files use mode `0600`. Unsafe types, symlinks, hardlinks, or wrong ownership fail.
2. Schema 1 uses fixed field order: `schema`, `sequence`, `epoch`, `timestamp`, `clock_valid`, `clock_reason`, `uncertainty`, `boot_id`, `uptime`, `controller`, `firmware`, `boot_count`, `power_cycles`, `boot_delta`, `power_delta`, `cause`, `discontinuity`.
3. Times and uncertainty use integer seconds. `clock_valid` is 0 or 1. Strings use JSON escapes, including control bytes.
4. `sequence` and `epoch` have capacity `1..2147483647`. Exhaustion returns 2 without wrapping.
5. First observation stores existing totals with zero deltas. Later observations record boot-count and power-cycle deltas separately.
6. A delta larger than one remains aggregate evidence. No individual event time or cause is invented.
7. Counter decrease, controller replacement, or firmware change starts a new epoch with zero deltas and an explicit discontinuity.
8. Unchanged counters produce zero deltas. A fully identical observation does not add another record.

## Decision API

```bash
/usr/bin/scr-resets-monitor status --json
/usr/bin/scr-resets-monitor check --max-resets 3 --window 3600
```

1. Both `--max-resets` and `--window` are mandatory. No environment, configuration, or built-in threshold defaults exist.
2. Threshold capacity is `0..2147483647`. Window capacity is `1..2147483647` seconds. Missing, duplicate, unknown, or invalid arguments return 2 before device access.
3. `check` refreshes and commits an observation before evaluating `(now - SECONDS, now]`. The count includes boot-count deltas only.
4. Exit 0 means complete evidence proves at most N resets. Exit 1 means reliable evidence proves strictly more than N resets.
5. Exit 2 means unavailable evidence, failed reading, failed persistence, or an indeterminate threshold. Callers must distinguish it from exits 0 and 1.
6. A reset delta belongs to an observation interval. A boundary-straddling interval adds only to the possible upper count, never the guaranteed lower count.
7. Time uncertainty expands interval bounds. Valid outer observations can bracket intermediate observations with invalid time within the same counter epoch.
8. Missing coverage prevents exit 0. Discontinuities, sequence gaps, corruption, unusable current time, and failed refresh cannot produce a healthy decision.
9. `check` produces no data on stdout. It never activates RAOM or changes caller recovery policy.
10. `status --json` reads committed history without a BMC query or cache update. It returns `observation`, `age`, `valid`, and `reason`.
11. `observation` is the latest schema-1 record, or null when history is unavailable. `age` is elapsed monotonic seconds within the same boot, otherwise null.
12. Status exit 0 means the record has valid clock evidence and a usable same-boot age. Otherwise it returns 2 with available data and a reason.
13. Status reasons include `ok`, `history_unavailable`, `clock_unreliable`, `boot_changed`, `uptime_invalid`, and `clock_unavailable`.
    13.1. Preparation failures return the same JSON shape with `privileges_required`, `storage_unavailable`, or `lock_unavailable`, plus exit 2.
14. Examples of unavailable decisions include insufficient installation history, an aggregate delta crossing the window boundary, and a failed journal write.

## Commit and recovery

1. Invocation holds the lock across history validation, observation, journal publication, and state update.
2. New journal content goes into a same-directory temporary file. File synchronization precedes rename; directory synchronization follows rename.
3. State cache advances only after journal synchronization succeeds. Interrupted temporary files never advance a baseline.
4. Cache failure returns 2 while the committed journal remains authoritative. Retry repairs the cache without repeating the committed counter delta.
5. Failure before journal publication leaves the earlier record intact. Baseline 146 followed by failed reading 147 records one delta on successful retry.
6. Uncertain post-rename results require successful synchronization before adoption. Corrupt, torn, conflicting, or missing sequence evidence returns 2.
7. Retained plain and gzip history is parsed as data. Identical repeated sequences are accepted; conflicting copies fail.
8. A cache ahead of retained history indicates missing evidence and fails. A stale or malformed cache can be rebuilt from valid history.
9. `.rotation-pending` prevents journal access during system rotation. Interrupted rotation requires explicit recovery; the utility never clears its marker automatically.
10. Diagnostics go to stderr and the owned log. When that log is unavailable, the existing system logger is a bounded fallback.

## Clock evidence

1. Each observation records wall time, boot ID, uptime, clock validity, and uncertainty.
2. Bounded local `ntpq -c 'rv 0'` must report `leap_none`, `sync_ntp`, valid numeric health, and a reference within four poll intervals.
3. Uncertainty includes root dispersion, half absolute root delay, absolute offset, clock resolution, and acquisition duration, rounded upward.
4. Wall-time and uptime disagreement marks time invalid. Invalid time does not discard valid BMC counters.
5. Current clock synchronization never proves an older timestamp was reliable.

## Focused checks

```bash
./bin/lets deb test runtime
```

1. Checks source named functions into isolated shells and use private temporary roots. Production CLI has no backend or command override.
2. Cases cover SEMA parsing, bounded acquisition, baseline/deltas, discontinuities, journal/cache failures, corruption, permissions, concurrency, clock parsing, and API decisions.
3. Failure injection covers write, file synchronization, directory synchronization, journal rename, and cache rename boundaries around real shell file operations.
4. Host checks execute file and directory synchronization through `dd count=0 conv=fsync` and read-only descriptors. They establish host behavior only.
5. Fixture SEMA fields derive from retained SCR observations. Combined capability/observation fixture preserves relevant field spelling; unrelated capability lines are omitted.
6. NTP fixture retains observed `ntpq` output. Fixture output is not new device evidence.
7. Rotation-specific tests are excluded by developer ruling. Architecture-specific or emulated target-image qualification is excluded by developer ruling.
8. Actual target execution remains a separate SSH stage after package readiness and target IP. Host results do not establish target persistence or hardware success.

## Debian build and installation

```bash
./bin/lets deb build src/tools/resets-monitor/etc/deb.conf
./bin/lets deb test
```

1. Bash-formatted `etc/deb.conf` is trusted build input. `INCLUDE_FILES` contains whitespace-separated local `source:destination` mappings.
2. Rsync trailing-slash semantics apply. `EXCLUDE_FILES` contains literal exclusion patterns, such as `*.bak`. Mapping paths cannot contain whitespace or colons.
3. Sources remain inside the project. Destinations remain below `build/resets-monitor/`. Unsafe ancestry and source/staging overlap fail before staging removal.
4. Build output is `build/scr-resets-monitor_1.0.7_all.deb`. Staging and archives remain ignored by Git. No compiler or development runtime is installed.
5. `MAINTAINER_COMMON` embeds the shared Bash lifecycle functions into each staged maintainer script. Each resulting script is self-contained.
6. Package payload first enters private staging paths under `/usr/lib/scr-resets-monitor/payload/`. Maintainer scripts install the complete `src/` subtree under `/usr/local/scr/` only after saving originals.
7. First-install backups remain under `/var/lib/scr-resets-monitor/`. Owner claims use `/var/lib/scr-sdlc/owners/`. Upgrades retain this original baseline.
8. Known package conflicts, unresolved ownership of existing executable paths, symlink ancestors, unsafe runtime links, and external hardlinks fail before payload replacement.
9. Configuration installs the observation hook without executing it. `/etc/rcS.d/S17scr-resets-monitor` follows the observed storage-ready hook.
10. The hook starts one bounded background observation. It does not gate boot, start another service, or change watchdog or monit policy.
11. The monit example installs at `/usr/local/scr/tools/resets-monitor/etc/monit-example.conf`. Its placeholders require explicit operator choices before activation.
12. Package transitions hold the stable runtime lock and `.package-pending` marker. Utility calls return 2 during a transition.
13. Removal restores original managed files, metadata, hardlinks within managed paths, and parent timestamps. Unrelated files remain intact.
14. New runtime logs must be exported before removal. Preservation across upgrades does not override original-state restoration during uninstall.
15. Existing runtime files become root-owned mode 0600 after backup. Removal restores their original ownership and permissions.
16. Restoration retains a recovery archive under `/var/lib/dpkg/info/.scr-resets-monitor-recovery` until payload and parent metadata synchronization succeed.
17. Failed restoration preserves that archive. Retry the failed `dpkg --remove scr-resets-monitor` operation after resolving its reported cause.
18. Configuration excludes originally existing directories from this package's dpkg file list. Payload files remain owned; purge preserves original empty parents.

On an authorized target, package commands are:

```bash
dpkg -i build/scr-resets-monitor_1.0.7_all.deb
dpkg -r scr-resets-monitor
```

## System rotation integration

1. `/etc/logrotate.d/scr-resets-monitor` names only the observation and diagnostic logs. System configuration retains schedule, size, compression, and retention policy.
2. The stanza uses rename/create, restricted ownership, and shared hooks. State cache and pending markers are excluded.
3. Begin hook records logrotate PID, process start time, boot ID, and committed sequence under the runtime lock, then synchronizes the marker.
4. End hook requires matching process identity and preserved committed sequence. Retained history is synchronized before marker removal.
5. Interrupted or unmatched rotation leaves the marker in place. Utility calls return 2. No timeout or automatic reboot recovery clears it.
6. Operator recovery requires rotation quiescence, valid retained history, and explicit marker recovery under the same lock. Preserve evidence before recovery.
7. No rotation-specific tests are part of this item. Shipped configuration and hook logic receive source review.

## Package and target verification

1. `./bin/lets deb test` runs runtime, build, isolated package lifecycle, and simulated SSH checks.
2. Host lifecycle checks use actual dpkg with `--root` and `--force-script-chrootless` in marked disposable roots under `/tmp`.
3. Host helpers execute maintainer scripts. Empty fixture package databases use `--force-depends`; these checks do not qualify a target OS.
4. Checks cover install, repeated configuration, history-preserving upgrade, failed upgrades, rollback, failed restoration and retry, removal, purge, and conflicts.
5. Before/after archives compare bytes, modes, owners, links, xattrs, access times, modification times, and original parent directories. Filesystem ctime is not restorable.
6. Successful runs remove only their marked roots. Failed runs retain roots and logs under the reported evidence path.
7. The upgrade fixture is version 1.0.8 with the same payload as version 1.0.7. Its only control change is `Version`.
8. Exact-package verification accepts both retained archives without rebuilding them:

```bash
./bin/lets deb test package \
  --deb build/scr-resets-monitor_1.0.7_all.deb \
  --upgrade-deb build/scr-resets-monitor_1.0.8_all.deb
./bin/lets deb test target-runner
```

9. The authorized SSH stage requires the supplied host/IP, expected hostname, identified device/image, checked package hashes, and an evidence directory.
10. SSH uses existing host-key trust and a root session. Initial package state must be absent. Existing installed or residual package state fails preflight.
11. After exact-package approval and target identification, run:

```bash
bash src/tools/resets-monitor/test/check-target.sh \
  root@HOST EXPECTED_HOSTNAME \
  build/scr-resets-monitor_1.0.7_all.deb \
  build/scr-resets-monitor_1.0.8_all.deb \
  /absolute/path/to/target-evidence
```

12. The runner records host/package identities, real BMC output, API exits, repeated observations, hook execution, upgrade, rollback, purge, and restoration evidence.
13. A timeout or disconnect stops dependent mutations. The runner retains its operation path and attempts evidence retrieval; it never blindly retries installation.
14. After an uncertain connection result, inspect retained operation and dpkg state before recovery. Do not kill the package manager or restart the test blindly.
15. Recovery uses the retained base package for rollback or package removal after the operation state is known. Preserve logs before cleanup.
16. This refactor requires fresh evidence for its exact package. Earlier package results remain historical; boot/reset/power-loss and developer confirmation remain separate.
17. Simulated SSH results prove runner behavior only. No reboot, physical reset, watchdog change, or firmware change occurs in these checks.
18. Hardware evidence must identify device/image, BMC/firmware, package versions/hashes, commands, expected/observed results, rollback, and developer confirmation.
