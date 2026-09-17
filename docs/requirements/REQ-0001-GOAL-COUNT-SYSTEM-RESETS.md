---
schema: 1
id: REQ-0001-GOAL-COUNT-SYSTEM-RESETS
title: Count system resets reliably
state: drafting-plan
round: 1
sequence: 13
approval: none
implementation_branch: 
implementation_commit: 
updated: 2026-09-17T13:04:19+00:00
---

# REQ-0001-GOAL-COUNT-SYSTEM-RESETS: Count system resets reliably

## Round 1

### Customer requirements

Goal: Count system resets reliably.

Problem:
The SCR system running image v8.26.0 experiences resets and sometimes enters reset loops as docs/MONIT.md describes. First step is a new low-level system reset counter providing a base for future reset-loop detection.

In scope:
- System reset detection mechanism.

Out of scope:
- Reset-loop detection and mitigation.

Tasks:
- Review image contents.
- Analyze kernel capabilities.
- Provide system reset counting mechanism relying only on low-level primitives: i.MX6 CPU registers and kernel subsystems.
- Implement according to notes; ask follow-up questions where needed.

Required behavior and constraints:
- Must not rely on user-space services such as monit or any other service; use only i.MX6 CPU registers and kernel subsystems.
- Log resets using atomic file functions under /var/log/scr/reset-<UTC timestamp in milliseconds>.
- After each reset, create a new reset-XXXX file under /var/log/scr/ and write reset reason into it.
- Perform file creation first, then reason write as a distinct second step, so at least reset signal survives if reason write cannot complete.

### Developer instructions

None.

### Requirements analysis

#### Facts and traceability

- Round 1 source is the Customer requirements section: “Count system resets reliably” on SCR image `v8.26.0`, as groundwork for future reset-loop detection. No prior hardware-result round exists.
- Customer reports resets and occasional reset loops and cites `docs/MONIT.md`. Those symptoms and that document's applicability have not yet been independently verified in this analysis.
- “After each reset, create a new reset-XXXX file” requires a distinct record under `/var/log/scr/reset-<UTC timestamp in milliseconds>` with reset reason content.
- “Perform file creation first, then reason write as a distinct second step” establishes ordering and an empty-file fallback when reason writing cannot complete.
- Coordinator relays newly supplied target hardware endpoint `192.168.68.56`. Hardware identity, running image version, reset behavior, and filesystem properties remain unverified; access credentials are intentionally absent from this record.
- This refines the existing round 1 analysis without treating its assumptions or open questions as customer answers.

#### Constraints

- Customer requires only “i.MX6 CPU registers and kernel subsystems”; detection/counting must not depend on `monit` or another user-space service.
- Record location, UTC millisecond filename, atomic file operations, and separate creation/reason-writing steps are explicit customer constraints.
- Image contents and kernel capabilities must be reviewed before solution planning.
- Repository workflow requires any later image change to be a reversible Debian package, with locked testing and verified restoration. This requirements task makes no image change.

#### Assumptions, not confirmed requirements

- Existing reset files are expected to preserve evidence across subsequent resets; actual storage durability and boot-stage availability need investigation.
- Counting files may satisfy “counter”; a separate numerical state or interface is not expressly requested.
- A record may be generated on the boot following a reset, but neither the lifecycle point nor coverage of resets before storage becomes available is defined.
- “Exactly one record per reset” is the testable interpretation of reliable counting, not a supplied list of qualifying reset causes.
- Valid UTC at record creation, unique timestamps, available storage, and readable retained reset-cause state must not be assumed proven.

#### Acceptance criteria

- On the confirmed target image, each agreed reset event produces one distinct regular file matching the required directory and UTC millisecond naming convention; repeated exercised resets neither overwrite prior records nor create duplicate counts.
- Evidence demonstrates file creation completes before the separate reason-write step begins.
- A completed reason write identifies the reset cause from an allowed low-level source; unknown or combined causes are represented without inventing a known cause.
- An interrupted or failed reason write after creation leaves the created file as reset evidence, within the persistence guarantee agreed below.
- Detection/counting operates without dependency on `monit` or another user-space service and uses only the customer-authorized low-level primitives.
- Validation maps each agreed reset class to observed record count and reason. Any unexercised cause or interval before recording becomes possible is stated explicitly; universal coverage is not inferred from successful ordinary boots.
- These criteria remain conditional on resolution of the material questions below and the image/kernel capability findings.

#### Non-goals

- Reset-loop detection, mitigation, or recovery.
- Diagnosing or repairing the underlying reset causes in this round.
- An additional numeric counter, reporting interface, or retention policy unless required by clarification.

#### Unresolved questions that materially affect scope or acceptance

- Which events must count: watchdog, software reboot/reset, external reset, brownout, power-on/power-cycle, panic-associated reset, and other reported causes? Must events occurring before persistent recording is possible also be counted individually?
- Is the count derived from reset files sufficient, or is a separate persistent numeric counter or exposed count required?
- Does “atomic file functions” require operation atomicity, persistence through another immediate reset, persistence through abrupt power loss, or all of these? The creation and reason-write steps need an explicit failure boundary for acceptance.
- What result is acceptable when valid UTC is unavailable or timestamps collide, given the required filename and the requirement to preserve every reset record?

The previous question about reset-reason vocabulary remains an unspecified output detail. Hardware inspection should establish which causes can be distinguished; a separate customer question is necessary only if the proposed representation changes accepted counting or cause semantics. None of the current questions blocks read-only image analysis.

### Image analysis

#### Scope and method

- **Verified:** The supplied target was inspected read-only over SSH. No reset, reboot, mount, package operation, or image write was performed.
- **Verified:** Local source image is the regular 3,850,371,072-byte file `var/image_8.26.0`. `./bin/lets scr image parts --image var/image_8.26.0` attempted its LETS read-only loop setup but failed at `losetup` with `Operation not permitted`; it did not mount the image. Thus no facts below are asserted from the local raw image filesystem.
- **Verified:** The target has `/etc/monit/conf-available/10-imagenumber` (regular file, mode `0755`, `root:root`, 20 bytes) containing exactly `check system 8.26.0`; `/etc/monit/conf-enabled/10-imagenumber` is a mode-`0777` symlink to it. This verifies a deployed configuration marker, not the raw-image identity or a cryptographic match to `var/image_8.26.0`.

#### Verified target identity, storage, and boot relationships

- Target is `ADLINK LEC-iMX6 (Quad/Dual) SMARC module`; root compatible is `adlink,lec-imx6,fsl,imx6q`; it runs Debian 8 (jessie), `3.10.105-imx6`, ARMv7, built 2018-05-16.
- `/` is `/dev/root`, `ext4`, mounted `rw,noatime,errors=remount-ro,data=ordered`; `/var` and `/var/log` are ordinary rootfs directories (both mode `0755`, `root:root`) rather than separate mounts. `/boot` is `/dev/mmcblk0p1`, `ext2`. `/var/log/scr` does not exist. Consequently, `/var/log/scr` would reside on the writable root ext4 filesystem once created; sudden-power-loss durability, available space at boot, and the required atomic/durable semantics remain unproved.
- `/etc/fstab` makes the root `/dev/mmcblk0p2` ext4, boot `/dev/mmcblk0p1` ext2, and mounts `/dev/mmcblk1p1` at `/mnt/usb`. PID 1 is SysV `init [2]`.
- `/boot/uImage` is a mode-`0777` symlink to `/boot/uImage-3.10.105-imx6`; both have MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`. This kernel is the running release. However, `dpkg-query -S` assigns `/boot/uImage` and `/boot/config-3.10.105-imx6` to installed `linux-image-3.10.53-lec-imx6` version `7`. This provenance/version mismatch is a material packaging conflict: a plan must not assume Debian metadata represents the running kernel or overwrite the boot artifacts.

#### Verified low-level reset facilities and limits

- The live DT contains `fsl,imx6q-src,fsl,imx51-src` at `/proc/device-tree/soc/aips-bus@02000000/src@020d8000` and `fsl,imx6q-wdt,fsl,imx21-wdt` nodes at `wdog@020bc000` and `wdog@020c0000`. The former watchdog is `status = "disabled"`; the latter is `status = "okay"`. `/proc/iomem` maps `0x020c0000-0x020c3fff` to the enabled watchdog.
- Kernel configuration in `/boot/config-3.10.105-imx6` has `CONFIG_WATCHDOG=y`, `CONFIG_IMX2_WDT=y`, `CONFIG_MFD_SYSCON=y`, `CONFIG_RESET_CONTROLLER=y`, `CONFIG_EXT4_FS=y`, `CONFIG_DEBUG_FS=y`, and `CONFIG_MODULES=y`; `CONFIG_RTC_DRV_SNVS=m`. It does not show enabled `PSTORE`, `RAMOOPS`, or `NVMEM` options. `/dev/watchdog` is character device `10:130`, mode `0600 root:root`; dmesg says `Use WDOG2 as reset source` and that `imx2-wdt 20c0000.wdog` is enabled with a 60-second, non-nowayout timeout.
- `/proc/kallsyms` exports existing internal `imx_src_init` and `imx_src_reset_module`, plus the reboot-notifier interface. This confirms a kernel path to the i.MX6 SRC exists, but does **not** prove the SRC reset-status register's lifecycle, bit-to-cause mapping, or retention for power-loss events. Those require the exact vendor kernel source and hardware reset exercises.
- **Inference for planning:** Achieving the customer prohibition on user-space services while creating a regular file requires kernel-resident code using kernel VFS/ext4 facilities, likely built into the specific vendor kernel (a late-loadable module may miss early status or storage readiness). Kernel-context file I/O and metadata/data flush ordering are high-risk on 3.10 and must be explicitly designed/tested; ordinary `O_CREAT|O_EXCL` protects name creation but does not prove power-loss persistence.
- **Conflict/feasibility limit:** A UTC-millisecond filename cannot be guaranteed by SRC/watchdog registers alone. The observed SNVS RTC support establishes a clock device, but valid UTC at the proposed execution point and collision handling are not established. A counter that records every individual power-cycle reset also cannot be claimed until SRC register semantics and retention have been demonstrated.

#### Existing reset-related configuration (explicitly out of bounds as a dependency)

- `monit` and `watchdog` are active: `/usr/bin/monit -c /etc/monit/monitrc` and `/usr/sbin/watchdog`. `watchdog` package version `5.14-3` is installed; `monit` metadata/ownership is unavailable from the target's incomplete dpkg file-list database.
- `/etc/monit/conf-enabled/99-watchdog` is a mode-`0777` symlink to regular mode-`0755` `/etc/monit/conf-available/99-watchdog` (390 bytes). It starts/stops `/etc/init.d/watchdog` and executes `/sbin/monit-watchdog.sh` after four restarts in ten cycles. `/sbin/monit-watchdog.sh` (regular mode `0755`, 143 bytes) stops monit, removes `/var/lib/monit/state`, then calls `/sbin/reboot`.
- `/sbin/monit-recover.sh` (regular mode `0755`, 1,204 bytes) creates/appends `/mnt/usb/number_of_resets`, counts its lines, then may call `shutdown -r +1`; the target currently has that 29-byte regular file. `/root/scripts/restartsdatetime.sh` (regular mode `0755`, 1,241 bytes) appends UTC text to `/mnt/usb/restarts.log`, and the root crontab invokes it at `@reboot`. The root crontab also removes `/var/lib/monit/state` at `@reboot`.
- These paths are not owned according to `dpkg-query -S` (or ownership cannot be proved because package file-list metadata is missing). They rely on user-space services/scripts and `/mnt/usb`, so they conflict with the stated implementation constraint and must neither be reused as the new mechanism nor silently replaced. `docs/MONIT.md` accurately identifies their reset-loop risk; reset-loop mitigation remains out of scope.
- No earlier SDLC implementation or requirement package is recorded in this requirement ledger; therefore no prior SDLC package path overlap is currently known. The target's unmanaged/custom paths and the mismatched kernel package metadata remain external conflicts to preserve and test against.

#### Planning evidence and open decisions

- A reversible package cannot safely deliver a built-in kernel change as an ordinary file-only DEB without an approved kernel-build/boot-artifact strategy, version provenance, ABI handling, and recovery/rollback test. The planner must decide whether a separate vendor-kernel package is in scope; the customer requirement constrains the implementation to kernel/i.MX6 primitives but does not authorize changing boot artifacts without that plan.
- Required developer decisions remain: reset classes to count (including power-on/power-loss); whether file count is the counter; exact atomicity/power-loss boundary; and acceptable behavior for invalid/colliding UTC. Additionally, confirm whether a kernel rebuild/boot artifact is authorized and provide the matching vendor kernel source/config or a reproducible source provenance.
- Required validation evidence: decode and exercise SRC reset-status bits on this exact kernel/hardware; show read-before-clear timing; simulate/observe watchdog, software reboot, external reset, and permitted power events; verify one distinct `reset-<UTC-ms>` regular file per accepted event; inject failure between creation and reason write; and test ext4 persistence according to the agreed durability boundary.

### Planner questions and answers

#### Scope and provenance

The coordinator relayed the developer's intake answers and subsequent clarifications on 2026-09-17. These answers resolve the planning questions for round 1. They amend the original requirements where explicitly stated below. They are not approval of a solution plan. No prior hardware-result round or implementation exists.

#### Reset classes, early resets, and reset reasons

**Question:** Which reset classes count, and must resets before the recording code or persistent filesystem becomes available be counted individually?

**Developer answer:** Count all listed causes: software reboot/reset, watchdog reset, external reset, brownout, power-on/power-cycle, panic-associated reset, and unknown causes. Every reset should create a new file so future logic can count events over a time interval. Reset-loop detection and mitigation remain outside this requirement.

**Clarification presented:** A reset can occur before the kernel/module can record a file. Several resets before recording becomes possible cannot necessarily be reconstructed from a reset-cause register. Existing evidence does not establish a retained hardware event counter.

**Final developer answer:** Investigate whether an i.MX6 reset counter register can preserve/count early resets. If no such supported hardware capability exists, resets occurring before module load may be clobbered or missed; document that limitation rather than block implementation. Do not claim exact counts for events the hardware cannot preserve. Reason writing is best effort; unknown causes still produce reset evidence.

#### Counter and durability

**Question:** Is file count sufficient, and what must survive an interruption between creation and reason writing?

**Developer answer:** File count is the counter. Durable empty-file creation is required before the separate reason-write step. Reason writing is best effort. An empty file therefore remains a valid counted reset event. No separate persistent numeric counter is requested.

**Engineering obligation:** Validate the actual creation/flush boundary and storage behavior. Developer acceptance of the intended durability guarantee is not evidence that the existing filesystem/device already provides it. Never treat successful exclusive creation alone as proof of power-loss persistence.

#### Filename, collisions, and invalid UTC

**Question:** What filename should be used, and what happens when time is invalid or timestamps collide?

**Developer answer:** Use `/var/log/scr/reset-<UTC timestamp milliseconds>-<random 4 letters>` and never overwrite an existing record. If UTC is invalid, record immediately using the kernel's current time rather than waiting for time synchronization.

**Consequence:** The random suffix supports distinct records with equal timestamps; collision handling must still preserve the no-overwrite requirement. Records created with invalid or adjusted kernel time cannot establish accurate real-world event rates for those intervals. Timestamp representation, suffix alphabet, and parser details must be specified in the draft consistently with these answers.

#### Existing kernel, module activation, and source provenance

**Question:** Are a kernel rebuild or changed kernel/boot artifacts permitted, and may a one-shot boot command load a kernel module?

**Developer answer:** Do not rebuild or replace the kernel or change its boot selection. Use the existing kernel and flag any missing capabilities that would require modules/rebuild. A boot-time module is allowed. Use official Debian kernel sources obtainable through apt.

**Additional final constraint:** Proceed with the loadable kernel module (LKM) approach now. A built-in implementation delivered by rebuilding the kernel may be mentioned only as a future option requiring explicit customer approval first; it is not an authorized fallback in this round.

**Interpretation of the explicit clarification:** A one-shot boot-time module-loading integration is allowed; monitoring and recording remain kernel-resident and must not depend on monit or another persistent user-space monitoring service. The manually invoked administrative CLI described below is also expressly requested.

**Unverified prerequisite:** The observed target runs the vendor kernel `3.10.105-imx6`, whereas package metadata names `linux-image-3.10.53-lec-imx6`. Availability through apt does not establish that Debian sources, headers, configuration, symbol versions, or build artifacts match the running vendor ABI. The draft must identify source/build compatibility checks and report a concrete blocker if a compatible module cannot be built or required kernel facilities are unavailable. A kernel replacement is not authorized as a fallback.

#### Administrative command and timestamp filtering

**Question:** Is a query/reset interface required, and what does `--since last` mean?

**Developer answer:** Add `scr-reset-monitor --reset`, which removes all reset records matching the required reset-file scope under `/var/log/scr/`, and `scr-reset-monitor --count`, which counts reset events. Support an optional explicit timestamp filter with `--since <timestamp>`, accepting `yyyy-mm-dd[ hh[:mm[:ss]]]`.

**Final amendment:** Remove `--since last` from the requested interface. Retain timestamp-only filtering. The earlier request for `--count [--since <last|timestamp>]` is superseded. Empty reset files count because the reason is best effort. The draft must specify timestamp parsing, omitted-component defaults, comparison boundary, and safe deletion/error behavior without broadening deletion outside reset records.

#### Storage unavailable or failing

**Question:** Should read-only/full/failing storage block boot, or should the system continue and retry?

**Final developer answer:** Continue boot and retry recording when storage is unavailable. This does not authorize rebooting the system as a response to logging failure. The draft must describe retry behavior and state that a further reset before durable creation can lose the pending evidence unless supported hardware retention proves otherwise.

#### Uninstall, generated data, and a busy module

**Question:** Should uninstall retain or delete reset evidence, and may it initiate a reboot to complete rollback?

**Developer answer:** Uninstall deletes generated reset records as `scr-reset-monitor --reset` does. Do not initiate a controlled reboot for uninstall. If module removal fails, leave removal pending until a reboot occurs for another reason.

**Engineering obligation:** Uninstall must not claim completion or restoration while the recorder remains active. The plan must define how pending removal prevents reactivation after a naturally occurring reboot, preserves restoration backups until cleanup finishes, and allows removal to complete afterward. The repository's cleanup/restoration failure quarantine rule still applies to image/package testing; pending removal is not permission to report successful restoration or bypass quarantine.

#### Development baseline and hardware validation

**Question:** Which image and test resources should be used, and are disruptive hardware tests authorized?

**Developer answer:** The available device may run a close image version such as `8.25.0`, with similar relevant components. Use the existing `./bin/lets scr image` commands for development against the image. Real hardware testing is for when the implementation is ready. Disruptive tests are authorized. Console/reflash access exists but is problematic and should be avoided. A mount-capable environment is expected shortly.

**Evidence boundary:** The prior read-only target inspection found a deployed `8.26.0` configuration marker, but did not prove raw-image identity. Exact runtime compatibility must be checked on any test device rather than inferred from a similar image version. The local baseline remains `var/image_8.26.0`; its filesystem has not yet been inspected because loop-device setup lacked permission.

**Workflow boundary:** Image operations during package development/testing remain subject to the continuous SDLC lock, uninstall/restoration verification, and quarantine on cleanup failure. The request to use the existing image commands does not waive those repository requirements. Hardware mutation remains deferred until the implementation is ready.

#### Remaining engineering investigations; no unanswered developer policy question

The accepted scope now permits drafting. Investigation must establish whether a supported i.MX6 counter preserves early resets; whether reset status survives until module load; which causes can be decoded without invented distinctions; whether a compatible module can be built for the existing kernel using available source/build artifacts; how kernel VFS persistence and retry behavior work on this image; and how safe deferred removal completes without an agent-initiated reboot. These are evidence requirements, not assumed capabilities. Missing module prerequisites or inability to implement the required behavior under the accepted constraints must be reported as concrete tooling/technical blockers.

No solution draft has been written or approved by these answers. A near-final reversible Debian-package plan must be committed as DRAFT before presentation, and implementation must await the required developer approval.

### Solution plan — DRAFT revision 1

#### DRAFT revision 1 — existing-kernel reset recorder

This plan implements round 1 of `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. It incorporates every answer in Planner questions and answers, including the final amendments. Those answers resolve the developer policy questions and authorize drafting; they do not approve implementation. There are no prior implementation or hardware-result rounds. Approval of this draft is required before implementation.

#### Evidence, boundaries, and implementation gates

The reviewed sources are the complete requirement ledger through sequence 9, its image-analysis evidence and Q&A, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, and `docs/MONIT.md`. The inspected device reports ADLINK LEC-iMX6, Debian Jessie, SysV init, kernel `3.10.105-imx6`, a writable ext4 root, and an absent `/var/log/scr`. Its image marker says `8.26.0`, but identity with local `var/image_8.26.0` is unproved. The source image is 3,850,371,072 bytes and remains unmounted because loop-device access failed. The kernel package database names `linux-image-3.10.53-lec-imx6` version `7`, which does not prove ABI compatibility.

Deliver one loadable kernel module (LKM) for the existing kernel. The only automatic user-space integration is a one-shot SysV boot loader; all event capture, reset-reason reading, recording, persistence ordering, and storage retries run in kernel context. The requested administrative CLI runs only when invoked. No monit, cron, USB log, watchdog daemon, network time service, or persistent user-space recorder becomes a dependency. Existing monit/watchdog/recovery configurations are preserved. Reset-loop diagnosis, detection, mitigation, automatic reboots, kernel replacement, DT changes, initramfs changes, and boot-selector changes are excluded. A built-in implementation is only a future option requiring explicit customer approval.

Approval permits investigation and implementation within this design, not bypassing these gates:

| Gate | Required evidence before the dependent work proceeds |
| --- | --- |
| Original image and environment | Inspect the actual image read-only under the SDLC lock in a mount-capable environment. Record SHA-256, partition/rootfs identity, dpkg architecture, kernel/config/module artifacts, boot ordering, `/run` lifecycle, path ownership, storage mount topology, and metadata. A similar device image is not substituted silently. |
| Sources and ABI | Obtain official Debian source/header material through apt, recording repository, version and hashes. Compare it with the vendor kernel's configuration, release, symbol versions, exported symbols, compiler/ARM ABI and build artifacts. Build only an external module; never assume generic Debian sources match the vendor tree, never force module loading, and never disable version checks. Missing matching build artifacts or exported interfaces is a concrete blocker requiring coordinator reporting. |
| Hardware registers | Consult the authoritative i.MX6 reference material and matching kernel/bootloader paths. Establish SRC status read/clear ordering, supported access coordination, raw-bit meaning and whether any supported retained hardware event counter exists. Avoid writes to shared reset/watchdog controls. No retained counter is assumed. Missing cause detail permits `unknown`; unsafe register access blocks that access path. |
| Kernel file operations | Establish available/exported 3.10 VFS operations, safe process-context workers, path lookup without symlink traversal, exclusive creation, file and directory synchronization, and safe unload. Demonstrate the empty-file persistence boundary on this ext4/device stack. Unsupported required operations are a blocker, not permission to replace the kernel. |
| Tooling safety | Confirm the supported image/test tooling enforces cleanup, restoration and persistent quarantine across failures. A command returning after releasing an OS lock is not evidence of restoration. Any safety gap blocks image mutation until addressed through the coordinator. |

Failure of a gate leaves an evidence-bearing blocker in the ledger. Implementation must not claim readiness or switch to a rebuilt kernel. Read-only investigation and local build work can continue independently where safe. Hardware mutation begins only after the implementation and restoration tests are ready.

#### Runtime behavior and persistence contract

Each supported boot activation represents the reset leading to that boot, including software reboot, watchdog, external reset, brownout, power-on/power-cycle, panic-associated reset, and an unknown cause. File count is the counter. The module captures available SRC status once at initialization, before asynchronous storage work; it never clears or fabricates status to improve a result. The reason contains a versioned plain-text record with raw status, documented decoded flags, and `unknown` for missing or ambiguous information. Panic must not be labeled uniquely unless a supported retained signal distinguishes it. Multiple status bits do not imply multiple events.

The supported boot loader runs once per boot after root and `/run` are available, using a package-owned `/etc/rcS.d/S99scr-reset-monitor` link. Image inspection must confirm this ordering; an incompatible init layout requires a recorded plan amendment. It checks the persistent removal marker first, checks the expected kernel, then loads the exact private module path with `insmod`. A boot-scoped attempt marker in `/run/scr-reset-monitor/` prevents repeated init invocations or a manual module unload from generating additional records in the same boot. A failed load is logged and leaves boot running; no fake reset file is created by the loader. Installation/configuration does not load the module on the host or retroactively count a reset. Initial activation is at the next boot. Upgrade leaves the running module loaded until a later boot, avoiding duplicate events.

The marker and all module-generated runtime state are package-managed. The marker is not a persistent numerical counter and cannot recover early resets. Direct manual module loading/reloading outside this loader is unsupported and excluded from exact-once claims. Tests must exercise repeated supported starts, install, reconfigure and upgrade within a boot.

Filename grammar is `reset-<epochMs>-<suffix>`: `epochMs` is signed decimal milliseconds since `1970-01-01T00:00:00Z`, and `suffix` is exactly four lower-case ASCII letters `[a-z]{4}`. Kernel wall-clock time is captured on the first recording attempt, without waiting for synchronization. Invalid time remains valid count evidence but cannot establish actual chronological reset rates. The suffix uses nonblocking kernel randomness; exclusive creation, rather than randomness alone, prevents overwrite. Regular files use `0600 root:root`; a newly created `/var/log/scr` uses `0755 root:root`.

The kernel recording procedure is:

1. CAPTURE the available reset status into `resetStatus` during module initialization.
2. QUEUE one recording worker and return from initialization without waiting for storage.
3. GET the first-attempt kernel time into `eventTime`.
4. ***while*** `emptyRecordDurable` is false ***and*** removal has not begun
   1. RESOLVE the approved persistent root and `/var/log/scr` without following unexpected symlinks or writing into an alternate transient mount.
   2. ***if*** the path is absent ***then***
      1. CREATE the package-authorized directory.
      2. SYNCHRONIZE its parent before claiming directory durability.
   3. ***if*** no record has been created ***then***
      1. GENERATE a suffix and attempt exclusive creation without truncation.
      2. ***if*** a name collides ***then***
         1. RETRY with another suffix, at most 64 times per worker invocation.
   4. ***if*** a record was created ***then***
      1. RETAIN that same file identity across synchronization retries.
      2. SYNCHRONIZE the empty file's inode and the containing directory using verified kernel interfaces.
      3. ***if*** every required synchronization succeeds ***then***
         1. SET `emptyRecordDurable` to true.
   5. ***if*** creation or synchronization has not succeeded ***then***
      1. SCHEDULE a delayed retry after 1 second, doubling to a maximum of 60 seconds.
      2. RETURN control without blocking boot or requesting reboot.
5. ***if*** `emptyRecordDurable` is true ***then***
   1. WRITE the bounded reason into that existing record as a distinct second operation.
   2. ATTEMPT a file synchronization for the reason.
   3. MARK this boot's recording complete even when reason writing fails.

The actual worker uses delayed invocations rather than a busy loop. Diagnostics are rate limited. Creation/flush errors including read-only storage, ENOSPC, EIO and permission problems retain one pending event in memory and retry indefinitely while the module remains active. They never cause the creation of a second file after successful creation. A partial or empty reason is counted. An unexpected disappearance or replacement of the retained file fails safely and is diagnosed; it must not overwrite another inode.

Durability means that successful empty-file inode and parent-directory synchronization precedes every reason write, subject to the proven storage flush behavior. Exclusive creation alone is insufficient. Failure before that boundary, device behavior that violates flush guarantees, and another reset before persistence can lose evidence. The module cannot promise recovery of several pre-load resets without an established retained hardware counter. Investigation of that capability is mandatory; absence permits the explicitly accepted limitation. Discovering a usable counter does not authorize inventing timestamps for historical events or changing this one-observable-boot record model without an amendment.

#### Administrative CLI

Implement `scr-reset-monitor --count [--since <timestamp>]` and `scr-reset-monitor --reset`, plus normal help. `--since last`, `--reset --since`, conflicting actions, and malformed arguments fail before any deletion. `--count` prints one nonnegative integer and newline on success; empty and partially written records count.

`--since` accepts exactly `yyyy-mm-dd[ hh[:mm[:ss]]]` in UTC, with a quoted argument when spaces are present. Missing time components default to zero. Validate Gregorian dates and ranges, reject trailing text, timezone suffixes, leap-second notation and invalid dates, and avoid local-time/DST conversion. Compare the filename timestamp inclusively (`eventTime >= sinceTime`), independent of reason content and mtime. Timestamp-only filtering cannot correct invalid or adjusted recording clocks.

The record scope is immediate, non-symlink regular files in `/var/log/scr` whose entire names match the grammar above and whose timestamp parses without overflow. No recursion, glob-based broad deletion, symlink following, or modification of nonmatching files is permitted. Unexpected symlinks or hard-linked matching records are reported as unsafe and left untouched. An absent directory gives count zero and a successful no-op reset; unreadable directories or partial deletion give a nonzero exit and diagnostics, never a misleading successful count/reset.

The module exposes a root-only maintenance control endpoint using a misc device `/dev/scr-reset-monitor`; its minimal versioned ioctl session quiesces worker file activity while the CLI enumerates/counts/deletes using a securely opened directory descriptor and relative operations. Exclusive sessions serialize concurrent CLI invocations. Closing the descriptor, including process death, releases the session; there is no persistent daemon or indefinitely stale pause lock. Counting preserves a pending event. An explicit reset cancels any pending record for the current boot and removes the scoped records; the module must not immediately recreate a cleared event. The next boot counts normally. If the module is absent, a root-only advisory CLI lock suffices because the one-shot loader also honors that lock. The implementation must verify interface availability on 3.10 and use no unexported-symbol tricks.

`--reset` requires root. It reports partial failures and synchronizes the directory after deletion. It does not reset historical hardware status, boot guards, unrelated logs or the package's original-baseline backup. Uninstall uses the same record-selection and deletion rules only after the recorder is stopped.

#### Debian package ownership and conflict contract

Produce exactly one architecture-specific package, `scr-req-0001-goal-count-system-resets`, initial version `1.0.1`, containing the module and compatible native administrative code. Determine `armhf` versus `armel` from the actual image before building; ARMv7 alone does not establish dpkg architecture. Record build inputs, compiler, ABI evidence, source revision, package SHA-256, license/source notices and runtime dependencies. Debian `libc6`, `kmod`, SysV and shell dependencies must use versions available on the baseline; package installation may not silently upgrade the kernel or unrelated dependencies. Missing dependencies are reported before mutation. No DKMS or target-side kernel build is introduced.

Use the approved SDLC package scaffold, then implement and test its required custom lifecycle logic. Dpkg owns the private payload tree at `/usr/lib/scr-req-0001-goal-count-system-resets/payload`; maintainer scripts copy managed destinations only after backup. Managed files are not conffiles and do not use `Replaces` to seize kernel or third-party ownership.

| Managed surface | Ownership and restoration |
| --- | --- |
| `/usr/lib/scr-reset-monitor/scr_reset_monitor.ko` | Kernel-specific module, `0644 root:root`; exact runtime release/build contract documented. Private direct loading avoids changing `/lib/modules` indexes or running `depmod`. |
| `/usr/sbin/scr-reset-monitor` | Administrative binary, `0755 root:root`. |
| `/etc/init.d/scr-reset-monitor` | One-shot boot loader, `0755 root:root`, no shutdown reboot action. |
| `/etc/rcS.d/S99scr-reset-monitor` | Exact package-managed symlink to `../init.d/scr-reset-monitor`; no broad `update-rc.d` changes. |
| `/usr/share/doc/scr-reset-monitor/README` | Operational limits, ABI, CLI and deferred-removal instructions, `0644 root:root`. |
| `/usr/lib/scr-reset-monitor/package-test` | Packaged non-destructive acceptance helper, `0755 root:root`; cannot load the module into an unrelated host kernel. |
| `/var/log/scr` and matching reset records | Snapshot original existence, directory metadata and every pre-existing matching record before first activation. Remove generated records at uninstall, then restore baseline records even if an administrator previously used `--reset`. Preserve unrelated entries. Remove the directory only when originally absent and empty after cleanup. |
| `/run/scr-reset-monitor` and `/dev/scr-reset-monitor` | Boot guard/CLI serialization and dynamic control device; remove package-created state after worker shutdown. Verify no stale kernel registration or device remains. Preserve/refuse unexpected pre-existing ownership. |
| `/var/lib/scr-req-0001-goal-count-system-resets/sdlc-backup` and transaction journal | Root-only original-baseline metadata/content and durable lifecycle phase, including pending-removal marker; retain through upgrades and incomplete removal, delete only after verified restoration. |
| `/var/lib/scr-sdlc/owners` requirement entry | Tooling ownership claims include exact destinations and the reset-record namespace; remove only this package's claims after restoration. Preserve the shared registry and other packages' entries. |

Existing managed destinations are examined with `lstat`, ownership queries and exact hashes. Unexpected pre-existing code/loader/control paths cause preflight refusal rather than arbitrary replacement. Existing log records may be preserved through the baseline backup. Backups capture absence, regular-file contents, symlink targets, uid/gid, modes, timestamps, hard-link relationships where applicable, ACLs/xattrs/capabilities and directory metadata. Unsupported metadata preservation is a blocker. No file move or deletion outside the listed runtime data and package-private transaction surfaces is planned.

The active SDLC ownership registry must reject exact, parent/child and namespace overlap with any other requirement package before mutation. This package exclusively claims the reset recorder and matching record namespace, not unrelated `/var/log/scr` logs. Independent packages may coexist when their paths and lifecycle effects are disjoint. All produced packages means this one package; no hidden helper package remains after removal. Existing boot artifacts, `/etc/modules`, module indexes, monit files, cron entries, `/mnt/usb` counters and kernel package-owned paths must compare unchanged. Unknown ownership is not permission to overwrite.

#### Maintainer scripts, upgrades, interrupted operations, and rollback

| Script / phase | Required behavior |
| --- | --- |
| `preinst install` | Validate platform, dependencies, path/namespace conflicts and backup capacity; durably snapshot the first baseline before touching destinations; journal operation intent and phase. Never replace an existing original backup with a partially installed state. |
| `postinst configure` | Stage payload replacements with validated metadata, then publish each atomically; establish the directory and exact loader link; validate all destinations; commit configured state. Do not load a module from chroot/offline installation or count a live installation as a reset. Reconfiguration is idempotent. |
| `preinst` / `prerm upgrade` | Preserve the first-install baseline and generated records. Validate compatibility with the resident module/control ABI. Keep the old module resident for the remainder of the boot; do not unload/reload to activate an upgrade. Refuse an incompatible upgrade before replacement. Snapshot the previous package payload and journal upgrade progress for failed-upgrade recovery. |
| `postinst` failed/aborted upgrade handling | Restore the previous compatible package payload and activation state on failure, preserving the original-baseline archive and all event data. A new version activates on a later boot. Declared incompatible state-schema or ABI changes require an amended plan. |
| `prerm remove` | Persist and synchronize removal-pending state first; disable the loader link; request worker quiescence/cancellation, close control registration and unload the module safely. Never force unload and never invoke reboot/shutdown. On failure, return nonzero before dpkg discards needed payload; preserve backups, disabled activation, diagnostic evidence and pending state. |
| `postrm remove` / `purge` | Only after confirmed module absence, delete generated records using the CLI scope; restore every baseline path/record and metadata; verify restoration; remove only package-created empty directories, runtime artifacts, ownership entry and backup/journal. Both normal removal and purge perform restoration; purge is not required to recover originals. |
| `abort-install`, `abort-upgrade`, `failed-upgrade`, retry | Resume or reverse the journaled operations idempotently from verified state. Dpkg error-recovery callbacks must not re-enable recording after removal was requested. Never erase the last usable backup on failure. |

A busy module leaves removal explicitly pending. The persisted marker and disabled boot link prevent reactivation after a reboot that occurs for another reason. No agent, maintainer script or cleanup helper initiates that reboot. After the natural reboot, rerunning the ordinary package removal completes restoration with the module absent. If storage prevents a durable pending marker/disabled activation, report that the pending-removal safety condition could not be established; do not claim successful removal. Backups remain until completion.

Transaction state writes use temporary-file publication and required directory synchronization. Removal, failed install and failed upgrade tests include interruption between each mutation and journal update. Package rollback to the original image is complete uninstall plus restoration; rollback from a failed upgrade restores the previous installed payload while retaining its original-baseline archive. No restoration success is declared while recording code is still resident or pending work can recreate files.

#### Validation and acceptance evidence

| Test group | Required results |
| --- | --- |
| Source/platform | Reproducible module build for the verified existing ABI; wrong release, wrong architecture, missing symbols/dependencies and mismatched module versions rejected safely. No forced loading, kernel rebuild, or boot artifact modification. |
| Names/time/CLI | Empty and partial files count; equal/invalid/backward time and forced suffix collisions never overwrite; strict UTC parsing covers omitted components, inclusive boundaries, calendar errors and overflow. `--since last` is rejected. Symlink/hardlink attacks, nonmatching files, unreadable directories and partial reset failure preserve unrelated data and report errors. |
| Recording state machine | Exclusive creation precedes inode+directory synchronization, which precedes reason writing. Fault injection at every boundary preserves the correct pending/durable state and avoids duplicate records. Read-only/full/EIO conditions allow boot and bounded-frequency retries; reason failure still counts. CLI concurrent reset/count and CLI process death safely serialize/resume; reset cannot be immediately undone by pending work. |
| Boot and module lifecycle | Exactly one record for each observable boot despite repeated supported loader starts, reconfigure and upgrades. No records from offline install or host module loading. Pending removal prevents next-boot activation. Clean unload cancels delayed workers and leaves no live control endpoint; simulated busy unload leaves removal pending and fails restoration. |
| Package lifecycle | Fresh install/remove, install/purge, reinstall, v1-to-v2 upgrade/remove, failed upgrade rollback, pre-existing log directory/records, every maintainer interruption phase, and repeated cleanup restore the original managed state. Preserve unrelated files and detect overlapping requirement packages before mutation. Verify backups survive all incomplete operations. |
| Image restoration | Continuous lock evidence, before/after fingerprints, supplemental metadata comparisons, no residual package ownership/runtime recorder, and source raw-image SHA-256 equality. Inject uninstall, verification and unmount failures; each must quarantine and prevent further use. |
| Ready-implementation hardware tests | On the verified compatible device, exercise software reboot, watchdog, external reset, power-on/cycle, supported brownout and panic-associated reset with documented safe controls. Verify count increments and raw reasons; distinguish unknown/combined reasons. Use short reset intervals and interruptions around the empty-file flush/reason-write boundary; validate ext4/device durability. Unsupported or unexercised causes remain explicitly unverified. |

Automated build/CLI/state-machine tests precede image package tests. A mounted ARM root or user-mode emulation cannot load an ARM LKM into the host and does not prove i.MX6 register behavior; the package test helper must recognize that boundary. Hardware tests are deferred until the artifact, safe installation/removal path and non-hardware checks are ready. Disruptive reset tests are authorized, but console/reflash recovery is problematic; start with supported ordinary reboot paths and progress only while recoverability remains established. No forced reboot is used to resolve uninstall. Provide exact hardware commands only after source/device evidence makes them safe and meaningful.

The lock-bounded image procedure is:

1. ACQUIRE the SDLC image lock and verify no quarantine or conflicting mounted-image state exists.
2. RECORD the source image SHA-256.
3. CREATE the tooling-managed disposable image copy.
4. MOUNT the copy through `./bin/lets scr image` within the same lock.
5. CAPTURE the baseline filesystem fingerprint and supplemental metadata/ownership evidence.
6. INSTALL the exact hashed DEB through the supported SDLC verifier.
7. RUN package and applicable functional/failure tests.
8. UNINSTALL every package produced for this requirement, including after a functional-test failure.
9. VERIFY restoration against the baseline, including restored pre-existing records and absence of generated records, backup residue, active recorder and pending removal.
10. UNMOUNT the copy through the supported image tooling.
11. VERIFY the original source SHA-256 is unchanged.
12. ***if*** uninstall, restoration, unmount or source verification failed ***then***
    1. QUARANTINE the affected image identities and retain the phase journal and recovery evidence.
    2. STOP without authorizing unlock/reuse as clean; an OS lock released by process exit does not clear quarantine.
    3. REQUIRE tooling-reported recovery verification before further use; never remove a quarantine marker manually.
13. ***else***
    1. RECORD the successful restoration evidence.
    2. RELEASE the image lock.

The preferred execution entry is `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-reset-monitor/package-test`; it already invokes supported image commands under its lock. Any custom mount workflow must be contained in one `./bin/lets sdlc lock-run` operation covering the whole sequence, not separate lock calls around individual phases. A bare lock wrapper is insufficient unless cleanup/quarantine/restoration are enforced. Use the existing tooling only; report missing capabilities instead of bypassing them.

Proof of restoration has two separate scopes: uninstall restores every managed path, original record, ownership/metadata and original absence on the disposable filesystem; unchanged SHA-256 proves the shared source image remains byte-identical. Dpkg database/log bookkeeping may differ inside the disposable test copy, so filesystem uninstall is not represented as raw-image byte identity. Existing verifier exclusions must be enumerated, and no managed path may be hidden by them. Supplement the verifier for metadata it does not fingerprint, including xattrs/ACLs/capabilities and timestamps as applicable. Parent-directory metadata and all created-directory cleanup are included. Residual pending removal or changed unrelated protected files is failure, not an exclusion.

#### Deliverables and approval gate

After approval, deliver source/build provenance, the single reversible DEB and SHA-256, its full ownership/backup manifest, lifecycle and fault-injection evidence, restoration/source-image proofs, explicit technical limitations, and the ready hardware procedure. Persist implementation and independent validation through `./bin/lets sdlc ...`; no implementation or image state is altered by this draft.

The deterministic policy input is six payload destinations, tests defined, custom maintainer scripts, boot activation, kernel privilege/security surface, and persistent storage changes. This is not a trivial plan. Only tooling may decide approval waiver; otherwise the committed DRAFT revision/hash waits for developer approval or amendments. Approval authorizes the specified LKM work, not a kernel rebuild or a reduced durability claim.

### Approval

Pending.

### Implementation

Pending. Every realization must be a reversible Debian package.

### Validation

Pending.

### Hardware follow-up

Pending.

### Event log

- `2026-09-17T08:55:39+00:00` [requirements-analysis] Round 1 created from customer requirements

- `2026-09-17T08:56:47+00:00` [requirements-analysis] Updated round 1 requirements-analysis section

- `2026-09-17T09:22:24+00:00` [requirements-analysis] Updated round 1 requirements-analysis section

- `2026-09-17T09:48:20+00:00` [image-analysis] Round 1 requirements analysis reviewed at sequence 3 against the Customer requirements section: distinct reset records in /var/log/scr with UTC millisecond filenames, creation before separate reason write, and only i.MX6 registers/kernel subsystems. Facts, assumptions, constraints, acceptance criteria, non-goals, and four material questions are already persisted. Reset coverage, count interface, durability boundary, and unavailable/colliding UTC remain unresolved; none blocks read-only image/kernel analysis. Coordinator now reports SSH access available at 192.168.68.56; target identity, image v8.26.0, kernel capabilities, and filesystem guarantees require verification. No new customer answers or image changes are asserted.

- `2026-09-17T12:20:03+00:00` [image-analysis] Updated round 1 image-analysis section

- `2026-09-17T12:20:28+00:00` [image-analysis] Updated round 1 image-analysis section

- `2026-09-17T12:20:34+00:00` [planner-questions] Read-only target analysis recorded: i.MX6 SRC/WDOG facilities verified; /var/log/scr absent on root ext4; existing monit/USB counter conflicts with scope; local image loop access blocked by missing permission; kernel provenance and reset semantics need planner questions.

- `2026-09-17T12:51:55+00:00` [planner-questions] Updated round 1 planner-questions section

- `2026-09-17T12:52:14+00:00` [drafting-plan] Developer answers committed in planner-questions: use existing-kernel LKM with one-shot boot loading; no kernel rebuild or boot selection change, and any future built-in implementation requires explicit customer approval. Count all causes including unknown; durable empty creation precedes best-effort reason; UTC-millisecond names have random four-letter suffixes and never overwrite; invalid UTC uses current kernel time. CLI provides reset/count and timestamp-only since filtering; storage failure continues boot with retries; uninstall deletes records and remains pending if unload fails without initiating reboot. Investigate supported i.MX6 retained reset counter; absent capability permits documented missed pre-module resets. Developer questions resolved; source/ABI, status retention, image access, persistence, and deferred cleanup remain explicit engineering evidence requirements. Next: draft the reversible LKM package plan against these constraints; no approval or implementation authorized by this transition.

- `2026-09-17T12:57:59+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-17T12:58:11+00:00` [draft-ready] Committed DRAFT revision 1 after complete ledger/Q&A, image evidence and guideline review. Specifies one reversible existing-kernel LKM package, ABI/source and VFS durability gates, one-shot boot activation, durable empty creation before best-effort reason, timestamp-only CLI, nonblocking storage retry, preserved original backups across upgrades, deferred busy-module removal without reboot, namespace conflict refusal, lifecycle/fault/hardware tests, and continuous-lock restoration with quarantine on cleanup failure. No unanswered developer policy question and no implementation performed.

- `2026-09-17T12:58:20+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-17T13:04:19+00:00` [drafting-plan] Amend DRAFT: use caveman full for all authored REQ sections and subagent instructions; make kernel module sole reset-state authority; make scr-resets-monitor a Bash administrative frontend. Preserve source requirements, evidence, safety, reversibility, and traceability.
