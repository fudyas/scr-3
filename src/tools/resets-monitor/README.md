# scr-resets-monitor

`scr-resets-monitor` reads reset counters through ADLINK SEMA, stores observations, and provides reset-threshold API. CLI never changes BMC settings or starts recovery.
The `scr-raom` Debian package also delivers [RAOM boot selection](../raom/README.md), which consumes this API and starts MONIT with safe or normal profile.

## Design

The reset CLI runs once per call. RAOM captures switch observations before the NTP readiness wait. It calls `check` after readiness when boot selection requires evaluation.

1. `record` runs `/usr/bin/sema cap all`, parses required BMC fields, and compares counters with the last committed observation.
2. The first valid observation establishes a baseline with zero deltas. Later observations store boot-count and power-cycle deltas separately.
3. A counter delta greater than one stays aggregated. The tool records the observation time and does not invent individual reset times or causes.
4. `status --json` reads committed history without querying the BMC.
5. `check` refreshes the observation and uses boot-count deltas to decide whether the reset limit was exceeded within the requested time window.
6. Clock uncertainty bounds each observation interval. The tool returns unavailable when evidence cannot support a safe decision.
7. The monitor uses one lock for history and the latest state. A failed capture cannot acknowledge resets.

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
| 9 | `src/tools/resets-monitor/src/scr-resets-monitor.init` | Provides explicit one-shot observation service. RAOM owns automatic boot evaluation. |
| 10 | `src/tools/resets-monitor/src/rotation-hooks` | Coordinates history access with log rotation. |
| 11 | `src/tools/resets-monitor/etc/` | Holds logrotate configuration and an inactive MONIT example. |
| 12 | `etc/deb/raom/` | Defines the combined package, installed links, and dpkg callbacks. |
| 13 | `etc/deb/raom/package-common.sh` | Supplies project-specific Debian installation and diversion callbacks. |
| 14 | `src/tools/resets-monitor/test/` | Holds runtime, package, build, and target-runner checks and fixtures. |
| 15 | `src/etc/scr.conf` and `src/lib/` | Provide shared SCR paths, logging, and command helpers. |

## Debian package

`etc/deb/raom/deb.conf` defines the files copied into package staging. LETS builds the package from the repository root:

```bash
./bin/lets deb build etc/deb/raom/deb.conf
```

LETS stages files in `build/scr-raom/` and writes `src/pkg/scr-raom_1.1.1_all.deb`. Git ignores both generated directories.
Generated archives under `src/pkg/` are excluded from the package payload.
Architecture is `all` because application contains shell scripts. Target still needs compatible SEMA and native runtime prerequisites.

dpkg installs operational source directly under `/usr/local/scr/`.
Debian diversions retain replaced native integration paths. Standard conffiles preserve client configuration. Maintainer scripts never start services or reboot.

Target installation requires separate explicit authority. On authorized target:

```bash
dpkg --install /tmp/scr-raom_1.1.1_all.deb
```

## Target prerequisites

| # | Requirement | Purpose |
|---|---|---|
| 1 | Debian with `dpkg` and SysV startup support | Installs package and native RAOM boot integration. Merged-/usr roots are unsupported by current package layout. |
| 2 | Root access | Required for the monitor commands and package lifecycle. |
| 3 | Bash 4.3 or later, `coreutils`, `util-linux`, and `dpkg` 1.17 or later | Declared Debian package dependencies. |
| 4 | ADLINK-compatible SEMA firmware, library, and `/usr/bin/sema` | Supplies read-only BMC readings. The package does not install SEMA. |
| 5 | `ntpq` with synchronized NTP data | Supplies clock quality for timed decisions. Counter capture can succeed with `clock_valid=0`. A valid acknowledgment can still bound eligible resets. |
| 6 | `logrotate` | Runs the installed rotation policy and its history-coordination hooks. The package does not declare it as a dependency. |
| 7 | Writable `/var/log` and `/run/lock` filesystems | Stores history, state, diagnostics, and the invocation lock. |
| 8 | MONIT, native NTP/logging, `watchdog`, and `wd_keepalive` | RAOM verifies native feeder handoff before planned MONIT stops and restarts. |

## Run on the target

Run commands as root. `record` reads the BMC. Plain `record` returns no observation on stdout.
`record --print-observation` prints one canonical JSON observation after a successful commit. An identical fresh read can reuse the latest committed sequence.
`status --json` reads cached history. Its status envelope cannot serve as an observation argument.

```bash
/usr/bin/scr-resets-monitor record --print-observation
/usr/bin/scr-resets-monitor status --json
/usr/bin/scr-resets-monitor check --max-resets 3 --window 3600
```

### Reset-window API

```text
scr-resets-monitor check --max-resets N --window SECONDS [--after-observation ACK] [--switch-reboot BEFORE AFTER]
```

| # | Argument | Contract |
| --- | --- | --- |
| 1 | `--max-resets N` | Required. Integer 0..2147483647. Only a count strictly greater than N exceeds the limit. |
| 2 | `--window SECONDS` | Required. Integer 1..2147483647. Window ends at the refreshed observation. |
| 3 | `--after-observation ACK` | Optional. ACK is a fresh committed record saved before `scr-raom switch normal` submitted its reboot. Resets through that counter are acknowledged. |
| 4 | `--switch-reboot BEFORE AFTER` | Optional. BEFORE is the committed source observation. AFTER is the first committed destination observation for the identified switch, or the literal `unavailable`. |

Pass each JSON record unchanged as one quoted argument. The marker `unavailable` is valid only for AFTER.
For example, RAOM can supply a recovery acknowledgment and a missing endpoint in the same check.

```bash
/usr/bin/scr-resets-monitor check --max-resets 1 --window 900 \
    --after-observation "$ack" --switch-reboot "$before" unavailable
```

RAOM identifies the submitted reboot and boot IDs. The monitor checks sequence, controller, firmware, counter epoch, and journal evidence.
For an identified switch in either direction, 100 → 101 contributes zero. A change of 100 → 102 contributes both resets. Zero change earns no credit.
A later ordinary 101 → 102 counts as one. Repeated checks cannot transfer the exemption to a later interval.
All raw observations and deltas stay in the journal.

| # | Exit | Evidence |
| --- | --- | --- |
| 1 | `0` | Eligible resets are at or below N. A valid acknowledgment can prove this from the total increase alone, even before a full synchronized window. |
| 2 | `1` | Reliable timed observations prove more than N eligible resets inside the window. A higher counter alone cannot prove when resets occurred. |
| 3 | `2` | Evidence cannot decide the window, refresh failed, or arguments are invalid. Clock jumps, lost records, and counter discontinuities can prevent a decision. |

An unavailable endpoint grants no exemption. The first retained observation after BEFORE on a different boot bounds the unknown interval.
The check returns `2` until reliable timing covers a full window beyond that bound. Ordinary threshold rules then return `0` or `1` when evidence permits.
RAOM keeps the marker after a successful check. A wider window can include the unknown interval again.
Plain `check` keeps the same exit codes. The monitor never starts recovery.

The monitor stores data in `/var/log/scr/`.

| # | File | Contents |
|---|---|---|
| 1 | `resets.jsonl` | Append-only observation and counter-delta history. |
| 2 | `resets-state.json` | Latest committed observation and baseline. |
| 3 | `resets-monitor.log` | Diagnostics and recovery messages. |

The monitor restricts the directory to root and mode `0700`. It restricts data files to root and mode `0600`.

## OS integration

1. The package installs its source tree under `/usr/local/scr/`. `/usr/bin/scr-resets-monitor` links to `/usr/local/scr/bin/src-resets-monitor`.
2. `/etc/init.d/scr-resets-monitor` provides explicit one-shot interface. RAOM owns automatic boot decision.
3. `/etc/logrotate.d/scr-resets-monitor` lets the host rotate the JSONL history and diagnostic log. Rotation hooks lock history access and preserve the committed sequence. The host keeps control of rotation timing and retention.
4. The package installs an inactive Monit example under `/usr/local/scr/tools/resets-monitor/etc/monit-example.conf`. Its threshold values are placeholders. The package does not enable it.
5. dpkg owns installed paths and tracks diversions for native startup adapters.
6. `/etc/default/scr-raom` configures `MAX_RESETS=5`, `RESET_WINDOW_SECONDS=900`, `NTP_SYNC_TIMEOUT_SECONDS=60`, `SAFE_MODE_ON_ERROR=true`, and profile paths. Invalid configuration uses complete defaults.
7. RAOM fixes the selected profile path per boot. Safe persists until verified normal recovery. During evaluation, exit 1 selects safe and exit 2 invokes the error policy.

Full configuration, launch failures, client sample limits, and installed interfaces: [RAOM operator guide](../raom/README.md).
