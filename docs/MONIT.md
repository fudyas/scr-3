# Monit configuration and stability

## Overview

This document describes how [monit](https://mmonit.com/monit/) is configured on
the SCR system image, how it relates to the software-upgrade (RFS) procedure,
the known stability problems, and the proposed fixes.

Source: partition 2 (`rootfs`) of image `8.26.0`.

Contents:

1. [Current configuration](#overview) — factual snapshot of the on-image setup.
2. [Software upgrade procedure (RFS)](#software-upgrade-procedure-rfs-and-monits-place-in-it) — and monit's place in it.
3. [Stability issues](#stability-issues) — the gaps and their proposed fixes.

Monit runs as a system daemon started early in the SysV boot sequence. It polls
every 30 seconds and supervises three kinds of things:

- **Processes** — start/stop via `/etc/init.d/*` scripts, with restart/recovery
  actions when they fail repeatedly.
- **Files, directories and filesystems** — integrity (permission / uid / gid /
  checksum) and space-usage checks.
- **Programs** — periodic helper scripts whose exit status raises alerts.

The daemon exposes an HTTP control interface on port 2812.

### Boot integration

| Item        | Value                                                  |
| ----------- | ------------------------------------------------------ |
| Init system | SysV (`/etc/init.d/monit`)                             |
| Enable flag | `START=yes` in `/etc/default/monit`                    |
| Start link  | `S03monit` (start priority 03 — early in the sequence) |
| Kill link   | `K01monit`                                             |
| Command     | `monit -c /etc/monit/monitrc`                          |

The `monit` init script wraps the daemon with `start-stop-daemon` and supports
`start`, `stop`, `reload`, `restart`/`force-reload`, `syntax` (`monit -t`) and
`status`. Its `reload` action first touches the service health files
(`bserv_health.txt`, `cm_health.txt`, `cm_health_long.txt`, `pm_health.txt`)
before sending `HUP`.

### Main configuration (`/etc/monitrc`)

Mode `600`. The same file is also present at `/etc/monit/monitrc` (identical
content).

| Setting       | Value                  |
| ------------- | ---------------------- |
| Poll interval | `set daemon 30` (30 s) |
| Log file      | `/var/log/monit.log`   |
| PID file      | `/var/run/monit.pid`   |
| ID file       | `/var/lib/monit/id`    |
| State file    | `/var/lib/monit/state` |

### HTTP interface

```
set httpd port 2812 and
    use address 0.0.0.0
    allow localhost
    allow admin:monit
    allow 0.0.0.0/0.0.0.0
```

Bound on all interfaces, port 2812, with a single `admin` / `monit`
username / password credential.

### Includes

```
include /etc/monit/conf-enabled/*
```

### Configuration directory layout

Monit follows the Debian `conf-available` / `conf-enabled` pattern:

| Path                         | Role                                     |
| ---------------------------- | ---------------------------------------- |
| `/etc/monit/conf-available/` | All available check definitions          |
| `/etc/monit/conf-enabled/`   | Symlinks to the active ones (included)   |
| `/etc/monit/conf.d/`         | Empty                                    |
| `/etc/monit/conf/monitrc`    | Packaged default (not the active config) |
| `/etc/monit/templates/`      | Reusable check fragments                 |

Files are ordered by numeric prefix: `10-` (base OS / platform services),
`20-` (mysql), `30-` (SCR application services), `99-` (watchdog).

### Reusable templates

Included by the file-integrity checks:

| Template     | Contract                                                                  |
| ------------ | ------------------------------------------------------------------------- |
| `rootbin`    | checksum + perm `755` + uid/gid `root` → **unmonitor** on failure         |
| `rootstrict` | checksum + perm `600` + uid/gid `root` → **unmonitor** on failure         |
| `rootrc`     | changed-checksum → **alert**; perm `644` + uid/gid `root` → **unmonitor** |

### Enabled checks

30 configuration files are enabled (symlinked into `conf-enabled/`).

### Monitored processes

Each entry starts/stops the service through its `/etc/init.d/*` script and takes
a failure action after a number of restarts within a cycle window. Restart
windows are expressed in poll cycles (1 cycle = 30 s).

| File           | Service   | PID / match                                 | Failure action                                                                                                        | Notable extra checks                                              |
| -------------- | --------- | ------------------------------------------- | --------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------- |
| `10-adminTool` | adminTool | `/var/run/adminTool.pid`                    | 5 restarts / 10 cycles → alert                                                                                        | init, sbin, `application.yml`, `logback.xml` file checks          |
| `10-autossh`   | autossh   | `/var/run/autossh.pid` (`onreboot nostart`) | 1 restart / 10 cycles → stop                                                                                          | depends `sshd`                                                    |
| `10-cps`       | cps       | `/var/run/cps.pid`                          | 5 restarts / 10 cycles → alert                                                                                        | init, sbin, properties, version file checks                       |
| `10-cron`      | crond     | `/var/run/crond.pid`                        | 5 restarts / 10 cycles → `monit-recover.sh crond`                                                                     | bin, rc, spool-dir checks                                         |
| `10-nmsAgent`  | nmsagent  | `/var/run/nmsagent.pid`                     | 5 restarts / 10 cycles → alert                                                                                        | init, sbin, config file checks                                    |
| `10-ntpd`      | ntpd      | `/var/run/ntpd.pid`                         | 5 restarts / 10 cycles → `monit-recover.sh ntpd`                                                                      | bin, rc file checks                                               |
| `10-rsshagent` | rsshagent | `/var/run/rsshAgent.pid`                    | 5 restarts / 10 cycles → alert                                                                                        | init, sbin, config file checks                                    |
| `10-rsyslog`   | rsyslogd  | `/var/run/rsyslogd.pid`                     | 5 restarts / 10 cycles → `monit-recover.sh rsyslogd`                                                                  | bin, rc, `/var/log/syslog` checks                                 |
| `10-sergey`    | scriptd   | matching `"scriptd"`                        | 4 restarts / 10 cycles → `monit-recover.sh scriptd`                                                                   | depends `rsyslogd`                                                |
| `10-ssh`       | sshd      | `/var/run/sshd.pid`                         | port 22 proto ssh fail → restart; 5 restarts / 10 cycles → `monit-recover.sh sshd`                                    | bin, sftp, rsa/dsa keys, `sshd_config` checks; depends `rsyslogd` |
| `20-mysql`     | mysqld    | `/var/run/mysqld/mysqld.pid`                | port 3306 / unixsocket proto mysql fail (3× / 4 cycles) → restart; 4 restarts / 10 cycles → `monit-recover.sh mysqld` | bin, rc checks; depends `rsyslogd`                                |
| `30-bserv`     | bserv     | `/var/run/bserv.pid`                        | 4 restarts / 110 cycles → `monit-recover.sh bserv`                                                                    | health-file check (below)                                         |
| `30-cm`        | cm        | `/var/run/cm.pid`                           | 4 restarts / 110 cycles → `monit-recover.sh cm`                                                                       | health-file check (below)                                         |
| `30-pm`        | pm        | `/var/run/pm.pid`                           | 4 restarts / 110 cycles → `monit-recover.sh pm`                                                                       | health-file check (below)                                         |
| `30-wildfly`   | wildfly   | `/var/run/wildfly/wildfly.pid`              | 4 restarts / 10 cycles → `monit-recover.sh wildfly`                                                                   | start/stop via `zerowildfly.sh`; depends `mysqld`, `rsyslogd`     |
| `99-watchdog`  | watchdog  | `/var/run/watchdog.pid`                     | 4 restarts / 10 cycles → `monit-watchdog.sh`                                                                          | —                                                                 |

### Service health-file checks

`30-bserv`, `30-cm` and `30-pm` each pair their process check with a
health-file freshness check:

| File       | Health file                 | Action when stale                                |
| ---------- | --------------------------- | ------------------------------------------------ |
| `30-bserv` | `/var/run/bserv_health.txt` | `timestamp > 10 minute` → `killProc.sh F1_Board` |
| `30-cm`    | `/var/run/cm_health.txt`    | `timestamp > 10 minute` → `killProc.sh Comm`     |
| `30-pm`    | `/var/run/pm_health.txt`    | `timestamp > 10 minute` → `killProc.sh proto`    |

### Filesystem checks

| File                     | Target           | Threshold                 |
| ------------------------ | ---------------- | ------------------------- |
| `10-system-flash-check`  | `/`              | space usage > 90% → alert |
| `10-system-sdcard-check` | `/dev/mmcblk1p1` | space usage > 90% → alert |
| `10-tmp-check`           | `/tmp`           | space usage > 80% → alert |

### Program checks

Each runs a helper script and alerts on the configured exit status:

| File                   | Script                                | Alert condition |
| ---------------------- | ------------------------------------- | --------------- |
| `10-doubletag`         | `/root/scripts/doubletagchecker.sh`   | status != 0     |
| `10-future-past-dates` | `/root/scripts/futuredates.sh`        | status != 0     |
| `10-innodb`            | `/root/scripts/check_double_write.sh` | status == 0     |
| `10-tagflow`           | `/root/scripts/tagflowchecker.sh`     | status != 0     |
| `10-wildflytmp`        | `/root/scripts/wildflytmp.sh`         | status != 0     |
| `10-zeromac`           | `/root/scripts/davidmac.sh`           | status != 0     |
| `30-ears`              | `/root/scripts/failedear.sh`          | status != 0     |

### System-label checks

Three `check system` entries carry platform identifiers as their name:

| File             | Name                             |
| ---------------- | -------------------------------- |
| `10-fsver`       | `8.3.1.199` (filesystem version) |
| `10-imagenumber` | `8.26.0` (image number)          |
| `10-ip`          | `192.168.1.101` (IP address)     |

### Available but not enabled

`40-alerts` exists under `conf-available/` but has no symlink in
`conf-enabled/`, so it is not currently loaded.

### Recovery scripts

Referenced by the failure actions above.

### `/sbin/monit-recover.sh <service>`

Repeated-failure recovery for a named service:

1. Ensures `/mnt/usb/WatchdogRestarts.log` and `/mnt/usb/number_of_resets`
   exist.
2. Appends the current date to `/mnt/usb/number_of_resets`.
3. If that file has fewer than 3 rows: stops monit, removes
   `/var/lib/monit/state`, records the event in `WatchdogRestarts.log`, and
   issues `/sbin/shutdown -r +1` (reboot in 1 minute).
4. Otherwise: logs that two restarts were already made and does nothing.

### `/sbin/monit-watchdog.sh`

Watchdog-failure handler: logs, runs `monit stop all`, waits 5 s, removes
`/var/lib/monit/state`, and calls `/sbin/reboot`.

### `/usr/local/bin/killProc.sh <name>`

One line: `pkill <name>`. Used by the health-file checks to kill the stale
worker process.

### Service groups

Checks are tagged into monit groups for bulk operations:

| Group    | Members                                                                                      |
| -------- | -------------------------------------------------------------------------------------------- |
| `system` | adminTool, autossh, cps, crond, nmsagent, ntpd, rsshagent, rsyslogd, scriptd, sshd, watchdog |
| `app`    | mysqld                                                                                       |
| `scr`    | bserv, cm, pm, wildfly                                                                       |

Plus per-service groups (e.g. `sshd`, `mysql`, `bserv`) used by the paired file
and health checks.

### Additional control scripts

Beyond the recovery scripts, `/sbin` carries helper wrappers around the daemon:

| Script            | Purpose                                                                                                       |
| ----------------- | ------------------------------------------------------------------------------------------------------------- |
| `monit-status.sh` | Returns non-zero (and logs) if `service monit status` does not report "is running". Used as a liveness probe. |
| `monit-pause.sh`  | Iterates `monit summary` and `monit stop`s every monitored service **except** `watchdog`.                     |
| `monit-resume.sh` | The inverse: `monit start`s every service except `watchdog`.                                                  |

### Runtime and boot hooks

Several cron entries (root crontab) mutate monit state or its configuration at
runtime:

| Schedule       | Action                         | Effect on monit                                                                       |
| -------------- | ------------------------------ | ------------------------------------------------------------------------------------- |
| `@reboot`      | `rm -rf /var/lib/monit/state`  | Wipes restart/flap history on every boot                                              |
| `0 0 * * *`    | `rm /mnt/usb/number_of_resets` | Clears the `monit-recover.sh` reboot-loop counter daily                               |
| `*/1 * * * *`  | `getip.sh`                     | Rewrites `10-ip` + `monit reload` when the IP changes; also `monit restart admintool` |
| `*/10 * * * *` | `installedimage.sh`            | Rewrites `10-imagenumber` + `monit reload` when the image number changes              |
| `*/10 * * * *` | `fsversion.sh`                 | Rewrites `10-fsver` + `monit reload` when the FS version changes                      |

Each of the three rewrite scripts follows the same pattern — read the single
line, `sed --in-place '1d'`, `echo "check system <value>"` back, then
`monit reload`.

### Software upgrade procedure (RFS) and monit's place in it

### How an upgrade runs

The software upgrade is a **Debian-package deployment driven by an installer
that ships inside the upgrade pack**, not on the RFS image itself. The
on-image `fs*` scripts orchestrate it:

1. An upgrade **pack** (`f1pack_<ver>.tar.gz`) is placed under
   `/mnt/usb/builds/`.
2. **`fsdeploy.sh`** is the entry point:
   - `fsdeploy.sh LATEST <tarfile> <ver>` — unpacks the tar
     (`tar -xzf … --no-same-owner`) into `f1pack_<ver>_current`.
   - `fsdeploy.sh ROLLBACK <ver>` — locates a previously deployed pack
     (`_prev`/`_current`) and re-runs it.
   - With no `LATEST`/`ROLLBACK` keyword it delegates to the legacy
     `fsdeploy_old.sh` for backward compatibility.
   - It then `cd`s into the pack directory and runs the pack-bundled
     **`./f1install.sh`** (passing `-r`/`-c`/`-d` flags). `f1install.sh` is the
     real installer and is **not present on the RFS** — it is delivered by the
     pack.
3. `f1install.sh` installs the Debian packages listed by the pack's
   `debsToInstall*` manifest (**`fsgetdebstoinstall.sh`** resolves that list),
   writing `/var/run/f1installer.pid` and logging to `/mnt/usb/allLogs/`
   (`bashScriptOutput.log`, `status.log`).

Supporting scripts:

| Script                                                                        | Role                                                                                                                                               |
| ----------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `fsbackup.sh`, `fsbackupWildfly.sh`, `fsbackupasync.sh`, `fsbackupcancel*.sh` | Back up the system / Wildfly before deployment                                                                                                     |
| `fsgetcurrentpacklocation.sh`                                                 | Resolve a version number to a pack/backup path (for rollback)                                                                                      |
| `fsversion.sh`                                                                | Reconcile the deployed FS version into monit's `10-fsver` (see below)                                                                              |
| `fsdeploystatus.sh`                                                           | Report whether an install is in progress (`f1installer.pid` / `ps`)                                                                                |
| `fsdeploykill.sh`                                                             | Abort a running install (`kill -9`) and `shutdown -r +3`                                                                                           |
| `after_upgrade_cleaner.py`                                                    | `@reboot` cron (installed as `/etc/cron.d/shupgrade`): inspects `status.log`, removes the leftover `backup.tar.gz`, and removes its own cron entry |

The upgrade is initiated by a privileged path: `sudoers.d/shupgrade` grants the
`%tech` group NOPASSWD rights to move a `shupgrade` cron file into
`/etc/cron.d/` (triggering the deployment). The application layer (Wildfly /
adminTool) drives this.

### What the upgrade delivers for monit

This is the crux for the stability work. Monit's configuration is split into
two categories with **very different upgrade behaviour**:

**A. Owned by the application `.deb` packages — travels with the upgrade.**

Only the three SCR application service checks are `dpkg`-owned:

| File                                 | Owning package     |
| ------------------------------------ | ------------------ |
| `/etc/monit/conf-available/30-cm`    | `communicator`     |
| `/etc/monit/conf-available/30-bserv` | `f1_boardservices` |
| `/etc/monit/conf-available/30-pm`    | `protocol_manager` |

Each of those packages carries a `postinst` hook
(`30-set-monit-enabled.sh`) that, after installing the new `30-*` file:

```
mkdir -p /etc/monit/conf-enabled
cd /etc/monit/conf-enabled
if !(ls -l | grep -q "30-cm"); then
  ln -s /etc/monit/conf-available/30-cm /etc/monit/conf-enabled/30-cm
fi
```

i.e. it creates the `conf-enabled` symlink if absent. The same `postinst` also
runs `update-rc.d <svc> disable` — the init scripts are deliberately disabled at
boot because **monit**, not the rc sequence, is responsible for starting these
services. Notably, the hook does **not** call `monit reload` afterwards.

**B. Everything else — baked into the RFS base image, NOT in the upgrade
payload.**

The following are plain files on the root filesystem, owned by no package, and
therefore **not updated by a normal software (deb) upgrade**:

- `/etc/monitrc` (and the duplicate `/etc/monit/monitrc`)
- all `10-*`, `20-mysql`, `99-watchdog` checks and the `templates/`
- the recovery / control scripts `/sbin/monit-*.sh`

These change only through one of:

1. a **full RFS reflash** (new base image),
2. **in-place edits by cron scripts** — `getip.sh` → `10-ip`,
   `installedimage.sh` → `10-imagenumber`, `fsversion.sh` → `10-fsver`, each
   followed by `monit reload`,
3. the **recovery bundle** `etc/recovery.tar.gz` (assembled by
   `etc/update-recovery.sh` as the `check-scr-fs` SHAR recovery script).

**Consequence:** the parts of monit most implicated in the stability problems
below (the daemon config, the `99-watchdog`/recovery reboot logic, the `10-*`
checks) currently have **no delivery path through the software upgrade**. Making
monit "part of the upgrade procedure" is therefore a prerequisite for shipping
any of the fixes to fielded units — see [Stability issues](#stability-issues),
issue 4.

## Stability Issues

Stability and correctness gaps observed in the current configuration, each with
its proposed fix nested beneath it. Severity is a first-pass assessment for the
SCR-3 work, to be confirmed on-target. **Nothing here is implemented yet** — the
proposed fixes exist to be reviewed and agreed before any code changes.

Issues are ordered by severity, HIGH first. Ordering note: the fix for **issue
4** (packaging monit into the upgrade) is the enabler — until it lands, the
fixes to the RFS-baked files (issues 1–3, 5 and 6) have no delivery path to
fielded units, so it should be implemented before them.

1. **Recovery reboot loop** — *HIGH*

   `monit-recover.sh` responds to a service exceeding its restart budget by
   rebooting the unit (`shutdown -r +1`), after wiping `/var/lib/monit/state`.
   The only brake is a row count in `/mnt/usb/number_of_resets` (`< 3` rows →
   reboot), and that file is **deleted every midnight** by cron. A service that
   fails persistently (e.g. a bad upgrade, a dependency that never comes up)
   therefore reboots the unit repeatedly, day after day, without ever
   converging. If `/mnt/usb` is not mounted when the script runs, the counter
   cannot persist and the brake is unreliable. `monit-watchdog.sh` reboots
   unconditionally.

   1. **Proposed fix.** Replace the "count rows in `number_of_resets`, reset
      daily" scheme with a persistent, monotonic counter plus a
      cooldown/backoff, and a hard cap that **latches** — after N recovery
      attempts it stops rebooting and raises a durable alert instead of silently
      resetting at midnight. Prefer service restart + escalation over reboot;
      reboot only as a last resort. Store the counter on a guaranteed-mounted
      path and verify the mount before use. (Interacts with issue 3.)

2. **Monit starts too early in boot** — *HIGH*

   Monit starts at rc priority `S03`, before most monitored daemons, before the
   network is up, and potentially before `/mnt/usb` is mounted. During this
   window the port checks (`sshd:22`, `mysql:3306`) and pidfile checks
   legitimately fail, so monit counts boot-time "not running" states as failures
   and can trigger restarts and `monit-recover.sh` — i.e. reboot the unit — as
   part of a **normal** boot. Recovery logging targets `/mnt/usb`, which may not
   yet be mounted.

   1. **Proposed fix.** Move monit's start later in the boot sequence (after
      mounts, network, rsyslog and the app init), and/or gate active checks
      behind a boot-complete marker or a per-service `start delay`, so the boot
      window is not counted as failures. Ensure `/mnt/usb` is mounted before
      monit runs.

3. **State wiped on every boot** — *HIGH*

   `@reboot rm -rf /var/lib/monit/state` erases restart/flap history at each
   boot. Combined with issues 1 and 2, monit has no cross-reboot memory: a
   crash-loop that should trip a restart budget instead reboots-and-forgets,
   masking the root cause and enabling slow reboot cycling.

   1. **Proposed fix.** Drop or narrow `@reboot rm -rf /var/lib/monit/state`. If
      state corruption is the real concern, validate/repair the state file
      instead of deleting it, so flap history survives a reboot and the restart
      budgets work.

4. **Core monit config is undeliverable via upgrade** — *HIGH (enabler)*

   As established in the upgrade section, `monitrc`, the `10-*`/`20-*`/`99-*`
   checks and the `/sbin/monit-*.sh` scripts are not owned by any package, so a
   software upgrade cannot correct them in the field. These are exactly the
   files responsible for issues 1–3, 5 and 6. Without closing this gap, no fix
   reaches fielded units short of a full reflash.

   1. **Proposed fix — deliver via an A/B config slot.** Rather than replacing
      monit's files in place (not power-safe), keep two complete config sets in
      `/etc/monit/slots/A` and `/etc/monit/slots/B`, with a single
      `/etc/monit/active` symlink selecting the live one; monit runs from the
      active slot. An upgrade writes the **inactive** slot only, validates it
      with `monit -t`, then atomically flips the symlink and reloads. The
      currently-unowned assets (`monitrc`, the base `10-*` / `20-mysql` /
      `99-watchdog` checks, `templates/`, `/sbin/monit-*.sh`) ship this way as
      part of the upgrade, giving every other fix a delivery path to fielded
      units. The mechanism, its acceptance criteria and how each is validated
      are specified in [Appendix A — A/B config-slot upgrade:
      requirements](#appendix-a--ab-config-slot-upgrade-requirements) and
      [Appendix B — A/B config-slot upgrade:
      validation](#appendix-b--ab-config-slot-upgrade-validation).
   2. **Validate before switch.** The atomic flip happens only after the new
      slot passes `monit -t`; a corrupt or incomplete config fails validation,
      the upgrade stops, and the symlink is left pointing at the running slot.
      The same `monit -t` gate protects the fixes for issues 5, 6 and 7.

5. **Duplicate `check system` entities** — *MEDIUM*

   `10-fsver`, `10-imagenumber` and `10-ip` each declare `check system
   <string>`. Monit supports exactly **one** SYSTEM service; multiple
   declarations are invalid and rejected/undefined (`monit -t` should flag
   this). At most one takes effect; the configuration is technically malformed.
   The values (FS version, image number, IP) are **data, not services** — they
   are abused as SYSTEM names purely to appear in `monit summary`. This is
   malformed on every monit version, so the fix does not depend on the on-target
   version.

   1. **Proposed fix — one real `check system`, stably named, with real rules.**
      The three values carry no rules today, so even the entity that "wins"
      monitors nothing. Replace them with a single SYSTEM block named by a stable
      identifier (the host) that carries actual host-resource thresholds:

      ```
      check system $HOST
        if loadavg (5min) > 4      for 5 cycles  then alert
        if memory usage  > 85%     for 5 cycles  then alert
        if swap usage    > 50%     for 5 cycles  then alert
        if cpu usage (user) > 90%  for 10 cycles then alert
      ```

   2. **Proposed fix — re-home the three values off the SYSTEM entity.** Choose
      per intent:
      1. **Keep them visible in monit** — one `check program` each; the script
         echoes the value and exits `0`, so it shows in `monit summary` / the
         dashboard without inventing extra SYSTEM entities. Grammar-valid on any
         version.
      2. **Cleanest** — drop them from monit entirely and report version / image
         number / IP through the NMS agent / M-Monit host identity / a status
         file the dashboard reads. Monit is not a key-value store.

   3. **Knock-on effect.** Option 2.2 also removes the reason
      `getip.sh` / `installedimage.sh` / `fsversion.sh` edit the monit config at
      all, so it resolves **issue 6** in the same change. And because a valid
      config has zero duplicate `check system`, how a given monit build treats
      duplicates no longer matters — this **dissolves open question 1** (see
      below), leaving only a triage note about the current field state.

6. **Fragile in-place config rewrites** — *MEDIUM*

   `getip.sh`, `installedimage.sh` and `fsversion.sh` each edit their `10-*`
   file with `sed --in-place '1d'` + `echo`, assuming the file is exactly one
   line. Any comment, blank line or manual edit corrupts the file. The three run
   on independent 1–10 minute schedules and each call `monit reload`, producing
   frequent reloads (churn plus brief unmonitored windows) and a race between
   the writers and the reload.

   1. **Proposed fix.** Replace the `sed '1d'` + `echo` rewrites with atomic
      rendering: write a temp file, validate with `monit -t`, move into place,
      then a single debounced reload. Deduplicate the three reload triggers, or
      move version/image/IP reporting out of the monit config altogether.

7. **App upgrade does not reload monit** — *MEDIUM*

   The application `postinst` adds the `conf-enabled/30-*` symlink but never
   runs `monit reload`. A freshly installed/updated service is therefore
   unmonitored until the next monit restart or the next `@reboot` state wipe.

   1. **Proposed fix.** Add a guarded `monit reload` to the application
      `postinst` hooks after the `conf-enabled/30-*` symlink is ensured, so
      newly installed services are monitored immediately.

8. **Control interface exposed** — *LOW (security)*

   `set httpd port 2812 use address 0.0.0.0 … allow admin:monit … allow
   0.0.0.0/0.0.0.0` exposes the monit control API to the whole network with a
   weak, shared `admin`/`monit` credential — anyone reachable can stop services
   or the daemon. Not a boot-stability issue, but a real exposure worth folding
   into the same pass.

   1. **Proposed fix.** Bind the httpd to `localhost` only (or firewall port
      2812), and use a stronger, per-unit credential.

9. **Blunt process kills** — *LOW*

   `killProc.sh` is a bare `pkill $1`, invoked by the `bserv`/`cm`/`pm` health
   checks with fuzzy names (`F1_Board`, `Comm`, `proto`). It can match and kill
   unrelated processes. The app services also use a wide `4 restarts with 110
   cycles` (~55 min) failure window.

   1. **Proposed fix.** Replace bare `pkill` with pidfile-scoped kills, and
      review the app-service restart window.

### Open questions

- (Triage only, not a design blocker — the issue 5 fix removes all duplicate
  `check system` entities so the target config is valid on any version.) The RFS
  image binary is monit **5.22.0**; confirming the fielded fleet version and how
  its build currently handles the three duplicates only helps explain the
  present field behaviour, not the fix.
- Whether `f1install.sh` (inside the pack) already performs any monit steps we
  cannot see from the RFS image — needs a pack sample.
- Whether `/mnt/usb` is guaranteed mounted at the boot point monit starts.
- Whether the `scr-monit` package (issue 4) should own the app `30-*` files too,
  or leave those with their application packages (current split).

## Appendix A — A/B config-slot upgrade: requirements

This appendix specifies the A/B config-slot mechanism that realises the fix for
[issue 4](#stability-issues) and the acceptance criteria it must meet. It
replaces in-place editing of monit's configuration (which is not power-safe)
with a validated, atomic slot switch.

### Design

1. **Two slots.** `/etc/monit/slots/A/` and `/etc/monit/slots/B/` each hold a
   complete, self-contained config set (`monitrc`, `conf-available/`,
   `conf-enabled/`, `templates/`).
2. **One active pointer.** `/etc/monit/active` is a symlink to the live slot.
   Monit starts with `monit -c /etc/monit/active/monitrc`, and every `include`
   inside that `monitrc` is written relative to `/etc/monit/active/…`, so
   flipping the single symlink switches the whole set at once.
3. **Shared state stays outside the slots.** `/var/lib/monit/id`,
   `/var/lib/monit/state`, `/var/run/monit.pid` and `/var/log/monit.log` are
   slot-independent so a switch does not disturb them.
4. **Write inactive only.** An upgrade writes the **inactive** slot; the running
   slot is never modified.
5. **Validated, atomic switch.** Validate the inactive slot with
   `monit -t -c /etc/monit/slots/<inactive>/monitrc`, then repoint the pointer
   atomically (`ln -sfn <inactive> /etc/monit/active.tmp && mv -T
   /etc/monit/active.tmp /etc/monit/active`) and `monit reload`.
6. **Rollback.** If validation fails, do not switch. If the post-switch health
   soak fails, flip `/etc/monit/active` back to the previous slot and reload.

### Requirements

Happy flow:

1. **REQ-1 (A/B layout).** Two config slots exist; a single `/etc/monit/active`
   symlink selects the live one; monit runs from the active slot.
2. **REQ-2 (isolation).** During an upgrade, monit keeps running from the
   currently active slot for as long as the upgrade is unfinished; only the
   inactive slot is written.
3. **REQ-3 (validated switch).** The symlink flips to the new slot **only after**
   that slot passes `monit -t`; on pass, monit reloads from the new slot.
4. **REQ-4 (health soak).** After the switch, the system runs as expected for
   **>1 hour**, including: embedded services send discoveries; the device is
   reachable via NMS; Cloudflare is active (remote connection to the unit works);
   Wildfly is up.

Negative cases:

5. **REQ-5 (power-safe).** If power is lost or the unit is reset during the
   upgrade, monit continues from the original, undamaged slot — the only mutating
   step is one atomic symlink flip, so there is no half-applied config.
6. **REQ-6 (corruption stops switch).** If one or more monit files in the new
   slot are corrupted, `monit -t` fails, the upgrade stops, and the symlink does
   not change.
7. **REQ-7 (missing dependency stops switch).** If a dependency is missing (e.g.
   a file referenced from `conf-available` is absent), `monit -t` fails, the
   upgrade stops, and the symlink does not change.
8. **REQ-8 (no new errors).** No new ERROR-level entries appear in syslog as a
   result of the switch.
9. **REQ-9 (auto-rollback).** If the health soak (REQ-4) or the syslog check
   (REQ-8) fails, the upgrade flips `/etc/monit/active` back to the previous slot
   and reloads. *(Implied by "resilient / fail-safe"; not stated explicitly in
   the request — to confirm in scoping.)*

> **REQ-7 caveat.** Confirm that `monit -t` on 5.22.0 actually **fails** (not
> merely warns) on a missing `include` target. If it only warns, add an explicit
> dependency pre-check before the switch so a missing file still stops the
> upgrade.

## Appendix B — A/B config-slot upgrade: validation

The acceptance test plan for the POC. Each test maps to the requirements in
Appendix A; acceptance = all pass, with the happy-flow soak free of new
ERROR-level syslog entries.

1. **V1 — Happy flow** *(REQ-1, REQ-2, REQ-3, REQ-4, REQ-8)*
   1. Start with Slot A active (`/etc/monit/active → slots/A`); confirm
      `monit status` shows services running from A.
   2. Run the upgrade. While it runs, confirm the active symlink still points at
      A and `monit summary` is stable (REQ-2).
   3. Confirm `monit -t -c slots/B/monitrc` returned `0` **before** the flip
      (REQ-3).
   4. Confirm `/etc/monit/active` now points at `slots/B` and `monit reload`
      succeeded.
   5. Soak for >1 hour and verify all four hold for the full window (REQ-4):
      embedded discoveries are sent, NMS reaches the device, the Cloudflare
      tunnel is up (remote connection works), Wildfly is up.
   6. Over the same window, `grep -i error /var/log/syslog` shows no new
      ERROR-level entries attributable to the switch (REQ-8).
2. **V2 — Power loss during upgrade** *(REQ-5)*
   Cut power at several points (before validation, after writing the inactive
   slot, and around the symlink flip). On reboot, confirm `/etc/monit/active`
   points at a valid slot — the old one if the flip had not happened, the new one
   if it had — and monit is running. Pass = it never lands on a half-written or
   invalid active config.
3. **V3 — Corrupted file** *(REQ-6)*
   Stage the new slot with a syntactically broken monit file and run the upgrade.
   Pass = `monit -t` fails, the upgrade aborts, `/etc/monit/active` still points
   at the original slot, and monit keeps running from it.
4. **V4 — Missing dependency** *(REQ-7)*
   Stage the new slot with a `conf-enabled` symlink whose `conf-available` target
   is absent and run the upgrade. Pass = `monit -t` (or the dependency
   pre-check) fails, the upgrade aborts, and the symlink is unchanged.
5. **V5 — Auto-rollback** *(REQ-9)*
   Force the post-switch soak to fail (e.g. hold Wildfly down after the switch).
   Pass = `/etc/monit/active` flips back to the previous slot, monit reloads, and
   the services recover.
