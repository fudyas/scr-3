# scr-resets-monitor

`scr-resets-monitor` reads reset counters through ADLINK SEMA, stores observations, and provides reset-threshold API. CLI never changes BMC settings or starts recovery.
Package 1.1.0 also delivers [RAOM boot selection](../raom/README.md), which consumes this API and starts MONIT with safe or normal profile.

## Design

Reset CLI remains one-shot tool. In package 1.1.0, RAOM calls `check` during boot after native NTP bootstrap/readiness.
Historical 1.0.x startup hook starts one bounded background `record`. Upgrade disables its obsolete `S17scr-resets-monitor` link.

1. `record` runs `/usr/bin/sema cap all`, parses required BMC fields, and compares counters with the last committed observation.
2. The first valid observation establishes a baseline with zero deltas. Later observations store boot-count and power-cycle deltas separately.
3. A counter delta greater than one stays aggregated. The tool records the observation time and does not invent individual reset times or causes.
4. `status --json` reads committed history without querying the BMC.
5. `check` refreshes the observation and uses boot-count deltas to decide whether the reset limit was exceeded within the requested time window.
6. Clock uncertainty bounds each observation interval. The tool returns unavailable when evidence cannot support a safe decision.
7. History and the latest state are committed under a lock. Failed reads or writes do not advance the saved baseline.

The runtime entry point loads shared SCR libraries, the runtime modules, and the tool command layer:

```mermaid
flowchart LR
    User -->|"runs command"| Entry["src/bin/src-resets-monitor"]
    Entry -->|"loads"| Modules["Bash runtime modules"]
    Modules -->|"reads"| SEMA["/usr/bin/sema cap all"]
    Modules -->|"commits observations"| History["/var/log/scr"]
    Modules -->|"returns decision"| User
```

## Repository layout

| # | Path | Purpose |
|---|---|---|
| 1 | `src/bin/src-resets-monitor` | Loads SCR libraries and monitor modules, then dispatches the command. |
| 2 | `src/tools/resets-monitor/tool.sh` | Parses arguments, prints usage, and runs `record`, `status`, or `check`. |
| 3 | `src/tools/resets-monitor/src/runtime/bmc.sh` | Runs the bounded SEMA query and parses BMC fields. |
| 4 | `src/tools/resets-monitor/src/runtime/record.sh` | Compares counters and builds observation records. |
| 5 | `src/tools/resets-monitor/src/runtime/time.sh` | Captures clock evidence and calculates conservative reset-window bounds. |
| 6 | `src/tools/resets-monitor/src/runtime/history.sh` | Validates and commits the JSONL history and state cache. |
| 7 | `src/tools/resets-monitor/src/runtime/status.sh` | Returns the latest committed observation as JSON. |
| 8 | `src/tools/resets-monitor/src/runtime/values.sh` and `diagnostics.sh` | Parse bounded values and write diagnostics. |
| 9 | `src/tools/resets-monitor/src/scr-resets-monitor.init` | Retains historical one-shot hook interface. RAOM replaces automatic early observation. |
| 10 | `src/tools/resets-monitor/src/rotation-hooks` | Coordinates history access with log rotation. |
| 11 | `src/tools/resets-monitor/etc/` | Holds Debian build, logrotate, and inactive Monit example configuration. |
| 12 | `src/tools/resets-monitor/pkg/` | Holds Debian control metadata and lifecycle scripts. |
| 13 | `src/tools/resets-monitor/src/package-common.sh` | Supplies project-specific Debian diversion and legacy migration callbacks. |
| 14 | `src/tools/resets-monitor/test/` | Holds runtime, package, build, and target-runner checks and fixtures. |
| 15 | `src/etc/scr.conf` and `src/lib/` | Provide shared SCR paths, logging, and command helpers. |

## Debian package

`src/tools/resets-monitor/etc/deb.conf` defines the files copied into package staging. LETS builds the package from the repository root:

```bash
./bin/lets deb build src/tools/resets-monitor/etc/deb.conf
```

Build stages files under `build/resets-monitor/` and creates `build/scr-resets-monitor_1.1.0_all.deb`. Git ignores `build/`.
Architecture is `all` because application contains shell scripts. Target still needs compatible SEMA and native runtime prerequisites.

dpkg installs operational source directly under `/usr/local/scr/`. New delivery has no generic private-payload copying or backup engine.
Debian diversions retain replaced native integration paths. Standard conffiles preserve client configuration. Maintainer scripts never start services or reboot.

Target installation requires separate explicit authority. On authorized target:

```bash
dpkg --install /tmp/scr-resets-monitor_1.1.0_all.deb
```

Supported 1.0.6/1.0.7 migration retains reset history and immutable legacy backup evidence. Same-version reinstall and supported 1.1.x upgrade retain client conffile choices.

1. ***if*** rollback to retained 1.0.6/1.0.7 is required ***then*** REMOVE current package with `dpkg --remove scr-resets-monitor`.
2. INSTALL exact retained archive with `dpkg --install /absolute/scr-resets-monitor_1.0.7_all.deb` or retained 1.0.6 archive.

Direct in-place legacy downgrade is unsupported and can leave MONIT missing. Remove-before-install restores diverted native originals first.
Remove retains client conffiles. Purge removes package conffiles. Both retain reset history and historical legacy backup evidence.

## Target prerequisites

| # | Requirement | Purpose |
|---|---|---|
| 1 | Debian with `dpkg` and SysV startup support | Installs package and native RAOM boot integration. Merged-/usr roots are unsupported by current package layout. |
| 2 | Root access | Required for the monitor commands and package lifecycle. |
| 3 | Bash 4.3 or later, `coreutils`, `util-linux`, and `dpkg` 1.17 or later | Declared Debian package dependencies. Legacy migration retains original archive tools as applicable. |
| 4 | ADLINK-compatible SEMA firmware, library, and `/usr/bin/sema` | Supplies read-only BMC readings. The package does not install SEMA. |
| 5 | `ntpq` with synchronized NTP data | Supplies clock-health evidence for valid timestamps and reset-window decisions. Without valid clock evidence, `check` returns 2. |
| 6 | `logrotate` | Runs the installed rotation policy and its history-coordination hooks. The package does not declare it as a dependency. |
| 7 | Writable `/var/log` and `/run/lock` filesystems | Stores history, state, diagnostics, and the invocation lock. |
| 8 | MONIT, native NTP/logging init scripts, and existing `wd_keepalive` | RAOM runtime prerequisites. Package never provisions client safe services. |

## Run on the target

Run commands as root. `record` reads the BMC and commits an observation:

```bash
/usr/bin/scr-resets-monitor record
```

Read the latest committed observation without a new BMC query:

```bash
/usr/bin/scr-resets-monitor status --json
```

Evaluate a threshold with an explicit limit and window in seconds:

```bash
/usr/bin/scr-resets-monitor check --max-resets 3 --window 3600
```

Both `--max-resets` and `--window` are required. Exit `0` means the limit is not exceeded. Exit `1` means reliable evidence proves the limit was exceeded. Exit `2` means the result is unavailable or indeterminate. `check` never starts a recovery action.

The monitor stores data in `/var/log/scr/`:

| # | File | Contents |
|---|---|---|
| 1 | `resets.jsonl` | Append-only observation and counter-delta history. |
| 2 | `resets-state.json` | Latest committed observation and baseline. |
| 3 | `resets-monitor.log` | Diagnostics and recovery messages. |

The monitor restricts the directory to root and mode `0700`. It restricts data files to root and mode `0600`.

## OS integration

1. The package installs its source tree under `/usr/local/scr/`. `/usr/bin/scr-resets-monitor` links to `/usr/local/scr/bin/src-resets-monitor`.
2. `/etc/init.d/scr-resets-monitor` retains one-shot interface. Package 1.1.0 disables obsolete `S17scr-resets-monitor`; RAOM owns automatic boot decision.
3. `/etc/logrotate.d/scr-resets-monitor` lets the host rotate the JSONL history and diagnostic log. Rotation hooks lock history access and preserve the committed sequence. The host keeps control of rotation timing and retention.
4. The package installs an inactive Monit example under `/usr/local/scr/tools/resets-monitor/etc/monit-example.conf`. Its threshold values are placeholders. The package does not enable it.
5. dpkg owns installed paths and tracks diversions. Package removal restores diverted originals. Historical `/var/lib/scr-resets-monitor/` backup stays intact during migration.
6. `/etc/default/scr-raom` configures `N=5`, `M=900`, `K=60`, `SAFE_MODE_ON_ERROR=true`, and profile paths. Invalid configuration uses complete defaults.
7. RAOM fixes mode/profile path per boot. API exit 1 always selects safe. API errors remain errors, even when configured policy permits normal.

Full configuration, launch failures, client sample limits, installed interfaces, and rollback: [RAOM operator guide](../raom/README.md).
