---
schema: 1
id: REQ-0001-GOAL-COUNT-SYSTEM-RESETS
title: Count system resets reliably
state: approved
round: 1
sequence: 22
approval: approved
implementation_branch: sdlc-req/req-0001-goal-count-system-resets
implementation_commit: 
updated: 2026-09-17T13:41:54+00:00
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

- Round 1 source: Customer requirements, “Count system resets reliably”, SCR image `v8.26.0`; groundwork for future reset-loop detection. No prior hardware-result round.
- Customer reports resets/reset loops; cites `docs/MONIT.md`. At requirements-analysis stage, symptoms/document applicability unverified; later Image analysis records verification boundary.
- “After each reset, create a new reset-XXXX file”: distinct record under `/var/log/scr/reset-<UTC timestamp in milliseconds>`, reset reason inside.
- “Perform file creation first, then reason write as a distinct second step”: creation precedes reason write; empty-file fallback preserves event evidence.
- Coordinator supplied target endpoint `192.168.68.56`. At intake, hardware identity, running image, reset behavior/filesystem properties unverified. Credentials intentionally omitted.
- Refines round 1 analysis; assumptions/open questions never promoted to customer answers. Later Planner questions and answers supersedes unresolved intake choices; sequence 13 amendment makes module sole state/behavior authority, `/usr/sbin/scr-resets-monitor` Bash frontend only.

#### Constraints

- Only “i.MX6 CPU registers and kernel subsystems”; detection/counting cannot depend on `monit` or another user-space service.
- Explicit constraints: record location, UTC millisecond name, atomic file operations, separate creation/reason-writing steps. Later accepted suffix amendment recorded below.
- Review image contents/kernel capabilities before planning.
- Every image change: reversible Debian package. Package tests: continuous image lock, verified restoration, quarantine on cleanup failure. Requirements analysis changes no image.

#### Intake assumptions; later answers govern

- Reset files expected to preserve evidence across resets; durability/boot-stage storage availability require proof.
- File count could satisfy counter; initial source requested no separate numeric state/interface. Later answers confirm file count + administrative CLI.
- Recording could occur on boot after reset; initial source left lifecycle/early-reset coverage open.
- Exactly one record per reset = reliability interpretation; initial source supplied no qualifying-cause list.
- Valid UTC, unique timestamps, storage availability, retained readable reset cause never assumed proven.

#### Acceptance criteria

- Confirmed target image: each agreed observable reset produces distinct regular file in required directory/name grammar, including later suffix amendment. Exercised resets neither overwrite earlier records nor duplicate counts.
- Evidence proves creation completes before separate reason write.
- Completed reason derives from allowed low-level source; unknown/combined causes never fabricated as known single cause.
- Interrupted/failed reason write leaves created file as event evidence within agreed durability boundary.
- Detection/counting uses only authorized low-level primitives; no `monit`/other service dependency.
- Validation maps agreed reset classes to observed counts/reasons. Unexercised classes/intervals before recording possible remain explicit; ordinary boots never prove universal coverage.
- Initial criteria conditional on material answers + image/kernel evidence. Recorded answers now govern limits, durable empty creation, CLI and module authority; engineering gates still require proof.

#### Non-goals

- Reset-loop detection, mitigation, recovery; underlying reset-cause diagnosis/repair.
- Separate persistent numeric counter or retention policy. Additional interface only as later expressly requested.

#### Material intake questions; resolved through coordinator below

- Count watchdog, software reboot/reset, external reset, brownout, power-on/power-cycle, panic-associated reset, other causes? Count events before persistent recording individually?
- File count sufficient, or separate persistent numeric counter/exposed count needed?
- “Atomic file functions”: operation atomicity, survival through immediate reset, abrupt power loss, or all? Exact creation/reason failure boundary?
- Invalid UTC/timestamp collision behavior while preserving every record and required names?

Reset-reason vocabulary initially unspecified. Hardware inspection must establish distinguishable causes; new customer question needed only when representation changes accepted count/cause semantics. None blocked read-only image analysis. Full answers + amendments retained in Planner questions and answers; no unanswered developer policy question carried forward.

### Image analysis

#### Scope and method

- Verified: supplied target inspected read-only over SSH. No reset, reboot, mount, package operation, image write.
- Verified: local `var/image_8.26.0` regular file, 3,850,371,072 bytes. `./bin/lets scr image parts --image var/image_8.26.0` attempted LETS read-only loop setup; `losetup` failed `Operation not permitted`; image never mounted. No raw-image filesystem facts claimed.
- Verified: `/etc/monit/conf-available/10-imagenumber` regular, `0755`, `root:root`, 20 bytes; exact content `check system 8.26.0`. `/etc/monit/conf-enabled/10-imagenumber` = `0777` symlink to it. Proves deployed configuration marker, not raw-image identity/cryptographic match with `var/image_8.26.0`.

#### Verified target identity, storage, boot

- `ADLINK LEC-iMX6 (Quad/Dual) SMARC module`; root compatible `adlink,lec-imx6,fsl,imx6q`; Debian 8 (jessie), `3.10.105-imx6`, ARMv7, built 2018-05-16.
- `/`: `/dev/root`, `ext4`, `rw,noatime,errors=remount-ro,data=ordered`. `/var`, `/var/log`: ordinary rootfs directories, both `0755 root:root`; no separate mounts. `/boot`: `/dev/mmcblk0p1`, `ext2`. `/var/log/scr` absent. New directory would reside on writable root ext4. Sudden-power-loss durability, boot free space, atomic/durable semantics unproved.
- `/etc/fstab`: root `/dev/mmcblk0p2` ext4, boot `/dev/mmcblk0p1` ext2, `/dev/mmcblk1p1` at `/mnt/usb`. PID 1: SysV `init [2]`.
- `/boot/uImage`: `0777` symlink to `/boot/uImage-3.10.105-imx6`; both MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`. Matches running release. Yet `dpkg-query -S` assigns `/boot/uImage`, `/boot/config-3.10.105-imx6` to installed `linux-image-3.10.53-lec-imx6` version `7`. Material provenance/packaging mismatch; Debian metadata cannot prove running ABI. Preserve boot artifacts.

#### Verified reset facilities and limits

- Live DT: `fsl,imx6q-src,fsl,imx51-src` at `/proc/device-tree/soc/aips-bus@02000000/src@020d8000`; `fsl,imx6q-wdt,fsl,imx21-wdt` at `wdog@020bc000`, `wdog@020c0000`. First watchdog `status = "disabled"`; second `status = "okay"`. `/proc/iomem`: enabled watchdog `0x020c0000-0x020c3fff`.
- `/boot/config-3.10.105-imx6`: `CONFIG_WATCHDOG=y`, `CONFIG_IMX2_WDT=y`, `CONFIG_MFD_SYSCON=y`, `CONFIG_RESET_CONTROLLER=y`, `CONFIG_EXT4_FS=y`, `CONFIG_DEBUG_FS=y`, `CONFIG_MODULES=y`, `CONFIG_RTC_DRV_SNVS=m`. No enabled `PSTORE`, `RAMOOPS`, `NVMEM` shown. `/dev/watchdog`: character `10:130`, `0600 root:root`. Dmesg: `Use WDOG2 as reset source`; `imx2-wdt 20c0000.wdog` enabled, 60-second timeout, non-nowayout.
- `/proc/kallsyms` lists internal `imx_src_init`, `imx_src_reset_module`, reboot-notifier interface. Confirms kernel SRC path; symbol visibility alone does not prove LKM export availability. SRC reset-status lifecycle, bit/cause mapping, power-loss retention still require exact vendor source + hardware exercises.
- Historical planning inference: service-free regular-file recording needs kernel-resident VFS/ext4 code; built-in code initially considered likely because late module could miss status/storage timing. Later developer decision restricts current scope to LKM; built-in remains future customer-approved option only. Kernel-context I/O and metadata/data flush ordering high risk on 3.10. `O_CREAT|O_EXCL` prevents name overwrite; never proves power-loss persistence.
- Feasibility limits: SRC/watchdog alone cannot guarantee UTC-millisecond names. SNVS RTC support establishes clock device, not valid boot-time UTC/collision handling. Every individual power-cycle count unproved until SRC retention semantics tested.

#### Existing reset configuration; forbidden implementation dependencies

- Active: `/usr/bin/monit -c /etc/monit/monitrc`, `/usr/sbin/watchdog`. Installed `watchdog` version `5.14-3`; monit metadata/ownership unavailable because dpkg file-list database incomplete.
- `/etc/monit/conf-enabled/99-watchdog`: `0777` symlink to `/etc/monit/conf-available/99-watchdog`, regular `0755`, 390 bytes. Starts/stops `/etc/init.d/watchdog`; runs `/sbin/monit-watchdog.sh` after four restarts in ten cycles. That script: regular `0755`, 143 bytes; stops monit, removes `/var/lib/monit/state`, calls `/sbin/reboot`.
- `/sbin/monit-recover.sh`: regular `0755`, 1,204 bytes; creates/appends `/mnt/usb/number_of_resets`, counts lines, may call `shutdown -r +1`. Target counter currently regular, 29 bytes. `/root/scripts/restartsdatetime.sh`: regular `0755`, 1,241 bytes; appends UTC text to `/mnt/usb/restarts.log`; root crontab invokes at `@reboot`, also removes `/var/lib/monit/state` at `@reboot`.
- `dpkg-query -S` reports no owners, or incomplete metadata prevents proof. Service/script/`/mnt/usb` dependence violates new mechanism constraint. Never reuse as reset authority or silently replace. `docs/MONIT.md` identifies their reset-loop risk; mitigation stays out of scope.
- Ledger records no earlier SDLC implementation/requirement package, hence no known prior SDLC overlap. Unmanaged/custom target paths + mismatched kernel metadata remain conflicts to preserve/test.

#### Planning evidence and decision history

- Built-in kernel change needs explicit kernel-build/boot strategy, version provenance, ABI handling, recovery/rollback testing; ordinary file-only DEB insufficient. Later answers exclude kernel rebuild/boot replacement now; future built-in option requires explicit customer approval.
- Original material decisions: reset classes including power events; file-derived count; atomicity/power-loss boundary; invalid/colliding UTC; kernel rebuild permission; matching source/config provenance. Coordinator-recorded answers below resolve policy choices. Source/ABI evidence remains prerequisite.
- Required validation: decode/exercise SRC bits on exact hardware/kernel; prove read-before-clear timing; observe software reboot, watchdog, external reset, authorized power events; verify distinct `reset-<UTC-ms>` records with later approved suffix; inject failure between creation/reason write; test ext4 persistence against agreed boundary.
- Sequence 13 amendment changes planned authority/frontend, not these measured facts. `/usr/sbin/scr-resets-monitor` Bash only; module owns all reset behavior/state. No new hardware/image inspection claimed by prose rewrite.

### Planner questions and answers

#### Scope and provenance

Coordinator relayed developer intake answers + clarifications on 2026-09-17. Below preserves full meaning, compresses agent-authored prose. Answers amend source where explicit; authorize drafting, never implementation approval. No prior hardware-result round/implementation. Sequence 13 adds sole-module authority + exact plural Bash frontend name.

#### Reset classes, early resets, reasons

Question: Which classes count? Must resets before recording code/persistent storage count individually?

Developer answer: Count software reboot/reset, watchdog, external reset, brownout, power-on/power-cycle, panic-associated reset, unknown causes. Every reset should create new file for future interval counts. Reset-loop detection/mitigation excluded.

Clarification: Reset may precede kernel/module recording. Several early resets cannot necessarily be reconstructed from cause register; retained hardware event counter unproved.

Final answer: Investigate i.MX6 reset counter register preserving/counting early resets. Absent supported capability, pre-module resets may be clobbered/missed; document limit, do not block solely for absent early-event counter. Never claim exact counts for events hardware cannot preserve. Reason best effort; unknown cause still event evidence.

#### Counter and durability

Question: File count sufficient? What survives interruption between creation/reason write?

Answer: File count = counter. Durable empty creation required before distinct reason write. Reason best effort; empty file counts. No separate persistent numeric counter.

Engineering obligation: Prove actual creation/flush boundary + storage behavior. Accepted intended guarantee does not establish filesystem/device capability. Exclusive creation alone never proves power-loss persistence.

#### Names, collision, invalid UTC

Question: Filename + invalid/colliding time behavior?

Answer: `/var/log/scr/reset-<UTC timestamp milliseconds>-<random 4 letters>`; never overwrite. Invalid UTC: record immediately using current kernel time, no synchronization wait.

Consequence: Suffix supports equal timestamps; explicit collision handling still required. Invalid/adjusted clock cannot establish accurate real-world interval rates. Draft specifies timestamp representation, suffix alphabet/parser.

#### Existing kernel, activation, source

Question: Kernel rebuild/boot changes allowed? One-shot module load allowed?

Answer: Existing kernel only; no rebuild, replacement, boot-selection change. Flag missing capabilities needing modules/rebuild. Boot-time module allowed. Use official Debian kernel sources obtainable through apt.

Final constraint: LKM now. Built-in implementation through rebuild = future option requiring explicit customer approval first; never current fallback.

Interpretation: One-shot boot loading allowed; module owns monitoring/recording. No monit/persistent userspace monitoring service. Manually invoked administrative CLI expressly requested.

Unverified prerequisite: Running vendor `3.10.105-imx6` versus package `linux-image-3.10.53-lec-imx6`. Apt availability does not establish matching source, headers, config, symbol versions, build artifacts/ABI. Draft must gate compatibility; incompatible build/missing required facilities = concrete blocker, never implicit kernel-replacement permission.

#### Administrative command and filtering

Question: Query/reset interface needed? Meaning of `--since last`?

Answer: Add reset/count commands; reset removes scoped reset records under `/var/log/scr/`; count reports events. Optional `--since <timestamp>` accepts `yyyy-mm-dd[ hh[:mm[:ss]]]`.

Final filter amendment: Remove `--since last`; timestamp-only. Earlier `--count [--since <last|timestamp>]` superseded. Empty records count. Draft must specify omitted components, timestamp parsing, comparison boundary, safe deletion/errors; no deletion beyond record scope.

Sequence 13 naming/authority amendment: Final commands `scr-resets-monitor --reset`, `scr-resets-monitor --count [--since <timestamp>]`; exact frontend `/usr/sbin/scr-resets-monitor`, Bash. Earlier singular command spelling superseded. Kernel module sole reset-monitor state/behavior authority: detection, cause, create/write/retry, serialization, count/filter/reset semantics, pending event, boot guard. Bash only validates command shape/transports requests/displays module result; no event state, filesystem count/delete, retry or truth. Durable `reset-*` files remain event evidence consumed/managed under module authority. Unsafe/duplicating Bash parsing moves entirely into module.

#### Storage unavailable/failing

Question: Block boot or continue + retry on read-only/full/failing storage?

Final answer: Continue boot, retry recording. Never reboot for logging failure. Further reset before durable creation may lose pending evidence unless supported hardware retention proves otherwise; draft must say so.

#### Uninstall, generated data, busy module

Question: Retain/delete reset evidence? Reboot allowed to finish rollback?

Answer: Uninstall deletes generated records with same scope as `scr-resets-monitor --reset`. Never initiate controlled reboot for uninstall. Failed module removal stays pending until reboot occurs for another reason.

Engineering obligation: No restoration/completion claim while recorder active. Pending removal must prevent reactivation after natural reboot; preserve backups until cleanup completes; ordinary removal retry completes afterward. During image/package testing, failed cleanup/restoration still quarantines image. Pending removal never counts as successful restoration.

#### Development baseline and hardware tests

Question: Image/resources? Disruptive hardware tests authorized?

Answer: Available device may run close image such as `8.25.0` with similar relevant components. Use existing `./bin/lets scr image` for image development. Hardware tests when implementation ready. Disruptive tests authorized; console/reflash exists but problematic, avoid reliance. Mount-capable environment expected shortly.

Evidence boundary: Earlier target marker `8.26.0` did not prove raw-image identity. Recheck exact runtime compatibility on any test device; similar version insufficient. Local baseline `var/image_8.26.0`; filesystem uninspected due loop permission failure.

Workflow boundary: Existing image commands remain inside continuous SDLC lock + uninstall/restoration/quarantine sequence. Hardware mutation deferred until implementation ready.

#### Decisions resolved; engineering proof pending

Load-bearing decisions reviewed together: classes/early-event limit; counter/durability; filename/collisions/UTC; existing-kernel LKM/source/activation; CLI/filtering; boot continuation/retry; uninstall data/busy unload/no reboot; development/hardware access; module authority/Bash frontend amendment. Answers above permit revised drafting. No outstanding developer policy question.

Engineering investigations: supported retained counter; SRC status survival to module load; distinguishable causes; existing vendor-ABI module build from available source/artifacts; 3.10 VFS/control/persistence/retry; module-owned guard; deferred restoration without initiated reboot. Evidence required, capabilities never assumed. Missing prerequisites/accepted-behavior infeasibility = concrete technical/tooling blocker through coordinator.

Earlier answers preceded DRAFT revision 1. Sequence 13 now requests amended DRAFT; answers/amendment still not approval. Commit revised near-final reversible-DEB plan before display; wait required developer approval before implementation.

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

### Solution plan — DRAFT revision 2

#### DRAFT revision 2 — module authority, Bash frontend

Round 1, `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. Incorporates complete recorded answers + sequence 13 amendment. Supersedes DRAFT revision 1, retained verbatim by tooling as historical audit; old frontend names/native-CLI authority no longer operative. No prior implementation/hardware-result rounds. All load-bearing policy decisions answered through coordinator before drafting; technical evidence gates below remain. DRAFT requires developer approval before implementation.

#### Sources, boundaries, gates

Reviewed complete ledger through sequence 13, image evidence, prior DRAFT, all Q&A, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/MONIT.md`. Measured target: ADLINK LEC-iMX6, Debian Jessie, SysV, `3.10.105-imx6`, writable ext4 root, absent `/var/log/scr`. Marker `8.26.0` proves no identity with local `var/image_8.26.0`; local file 3,850,371,072 bytes, unmounted after loop permission failure. Package metadata `linux-image-3.10.53-lec-imx6` version `7` proves no ABI match. Image analysis retains exact paths, modes, sizes, MD5 and configuration evidence.

Deliver one existing-kernel loadable kernel module (LKM). Module sole reset-state/behavior authority: detection, cause, record create/write/retry, serialization, count/filter/reset semantics, pending event, boot guard. Durable `reset-*` files = event evidence module consumes/manages; no separate numeric counter. `/usr/sbin/scr-resets-monitor` = Bash administrative frontend, invoked manually. One-shot SysV loader activates module at boot. Neither script owns reset state or filesystem semantics.

No monit, cron, USB counter, watchdog daemon, network-time service, persistent userspace recorder dependency. Preserve existing monit/watchdog/recovery configuration. Reset-loop diagnosis/detection/mitigation, automatic reboot, kernel replacement, DT/initramfs/boot-selector changes excluded. Built-in implementation = future option needing explicit customer approval; never fallback here.

| Gate | Evidence required before dependent work |
| --- | --- |
| Original image/environment | Inspect actual image read-only under SDLC lock in mount-capable environment. Record SHA-256, partition/rootfs identity, dpkg architecture, kernel/config/modules, boot ordering, `/run` lifecycle, ownership, mount topology, metadata. No silent substitution with similar device image. |
| Sources/ABI | Obtain official Debian source/header material through apt; record repository/version/hashes. Compare vendor config, release, symbol versions, exported interfaces, compiler/ARM ABI, build artifacts. External module only. No assumed generic-source match, force loading, disabled version checks or unexported-symbol tricks. Missing matching artifacts/interfaces = blocker through coordinator. |
| Registers | Inspect authoritative i.MX6 reference + matching kernel/bootloader paths. Establish SRC read/clear ordering, coordinated safe access, raw-bit meaning, supported retained event counter availability. No assumed counter; no shared reset/watchdog-control writes. Missing detail permits `unknown`; unsafe access blocks access path. |
| Kernel VFS/control | Establish exported 3.10 process-context VFS, secure path lookup, exclusive creation, inode/directory synchronization, directory iteration/unlink, misc-device read/write, bounded request parsing, cancellation/unload. Prove required flush boundary on actual ext4/device. Unavailable operation = blocker, not kernel rebuild permission. |
| Module authority/guard | Prove module can own boot-scoped guard, request state and serialization without frontend lock/marker/count fallback. Verify `/run` cleared exactly once per boot before loader; preserve guard across supported same-boot reload. Missing safe implementation = blocker through coordinator. |
| Tooling safety | Confirm supported test/image tooling enforces cleanup/restoration/persistent quarantine through faults. OS lock release alone proves nothing. Safety gap blocks image mutation; report through coordinator. |

Failed gate leaves evidence-bearing blocker. No readiness claim/kernel rebuild substitution. Independent read-only investigation/local builds may continue safely. Hardware mutation only after implementation + restoration tests ready.

#### Boot, event, file contract

Each supported boot activation records reset leading to boot: software reboot/reset, watchdog, external reset, brownout, power-on/power-cycle, panic-associated reset, unknown. Module captures available SRC status once during initialization before asynchronous storage work. Never clear/fabricate status to improve result. Versioned bounded plain-text reason carries raw status, documented decoded flags, `unknown` for missing/ambiguous evidence. Distinct panic label requires supported retained signal; multiple bits never imply multiple events.

One-shot `/etc/rcS.d/S99scr-resets-monitor` runs after root + `/run` ready; image inspection must prove ordering. Incompatible init layout needs recorded amendment. Loader checks durable removal-pending marker + expected kernel, then `insmod` exact private module. Loader creates no reset file/guard, performs no count, cause decoding or retry. Failed load logs error, permits boot. Offline/live package configuration never loads module or retroactively counts installation; first activation next boot. Upgrade keeps resident version through current boot.

Module alone creates/reads `/run/scr-resets-monitor/` boot guard, owns accepted/completed/cancelled states, serializes initialization, and rejects duplicate recording after repeated supported starts. Guard persists across supported same-boot unload/reload; boot-time `/run` reset opens next boot. Module must not mark successful capture before initialization reaches recoverable accepted state. Control cannot clear guard. Failed initialization/retry cases explicitly tested. Loader never reads guard to decide event identity; package scripts only restore/remove runtime artifacts after confirmed shutdown. Guard not numeric counter; cannot recover early resets. Direct unsupported `insmod` parameter manipulation excluded from exact-once claims; supported reload remains module-deduplicated.

Filename: `reset-<epochMs>-<suffix>`; `epochMs` signed decimal milliseconds since `1970-01-01T00:00:00Z`, suffix exactly four lowercase ASCII letters `[a-z]{4}`. Module captures wall clock at first recording attempt, never waits for synchronization. Invalid/adjusted clock still count evidence; cannot prove actual event rates. Nonblocking kernel randomness supplies suffix; exclusive creation enforces no overwrite. Record `0600 root:root`; newly created `/var/log/scr` `0755 root:root`.

Module recording procedure:

1. CAPTURE available reset status into `resetStatus` during initialization.
2. ESTABLISH module-owned boot guard under verified `/run` lifecycle.
3. QUEUE one recording worker for accepted boot.
4. RETURN from initialization without waiting for persistent storage.
5. GET first-attempt kernel time into `eventTime`.
6. ***while*** `emptyRecordDurable` false ***and*** removal not begun
   1. RESOLVE approved persistent root + `/var/log/scr` without unexpected symlinks/alternate transient mount.
   2. ***if*** directory absent ***then***
      1. CREATE package-authorized directory.
      2. SYNCHRONIZE parent before claiming directory durability.
   3. ***if*** no record created ***then***
      1. GENERATE four-letter suffix.
      2. ATTEMPT exclusive creation without truncation.
      3. ***if*** name collides ***then***
         1. RETRY different suffix, maximum 64 attempts per worker invocation.
   4. ***if*** record created ***then***
      1. RETAIN same file identity through synchronization retries.
      2. SYNCHRONIZE empty inode through verified interface.
      3. SYNCHRONIZE containing directory through verified interface.
      4. ***if*** all required synchronization succeeds ***then***
         1. SET `emptyRecordDurable` true.
   5. ***if*** creation/synchronization incomplete ***then***
      1. SCHEDULE delayed retry after 1 second, doubling to maximum 60 seconds.
      2. RETURN without blocking boot/requesting reboot.
7. ***if*** `emptyRecordDurable` true ***then***
   1. WRITE bounded reason into same record as distinct second operation.
   2. ATTEMPT reason-file synchronization.
   3. MARK boot recording complete even when reason writing fails.

Delayed invocations, no busy loop; rate-limited diagnostics. Read-only, ENOSPC, EIO, permission/flush failures retain one in-memory pending event; retry indefinitely while active. Successful creation never followed by second-file creation for same event. Missing/replaced retained inode fails safely + diagnostic; never overwrite replacement. Empty/partial reason counts. All pending state, timing, retries, record identity and cancellation stay inside module.

Durability boundary: successful empty inode + parent-directory synchronization before every reason write, subject to proven device flush behavior. Exclusive creation insufficient. Failure before boundary, device violating flush guarantee, further reset before persistence can lose event. Several pre-load resets unrecoverable absent supported retained counter. Investigating counter mandatory; absence permits accepted limitation. Discovering counter never authorizes invented historical timestamps or changing one-observable-boot model without amendment.

#### Bash frontend and kernel control

Final commands: `scr-resets-monitor --count [--since <timestamp>]`, `scr-resets-monitor --reset`, normal help. Reject `--since last`, `--reset --since`, conflicting actions, malformed arguments before mutation. Count success prints one nonnegative integer + newline; empty/partial records count. All control operations root-only because endpoint `0600 root:root`.

Module parses `--since` value exactly `yyyy-mm-dd[ hh[:mm[:ss]]]` UTC. Spaces require quoted shell argument; omitted time components zero. Strict Gregorian date/range/overflow validation; reject trailing text, timezone suffixes, leap-second notation, invalid dates. No locale/DST conversion. Inclusive filename comparison `eventTime >= sinceTime`, independent of mtime/reason. Module owns parsing/filter result; Bash never converts dates or computes counts.

Module record scope: immediate non-symlink regular files in `/var/log/scr`, whole name matches grammar, timestamp parses without overflow. No recursion, broad glob deletion, symlink following, nonmatching-file mutation. Matching symlinks/hard links unsafe: report, preserve. Absent directory => count zero/reset success no-op when module available. Unreadable directory/partial deletion => nonzero + diagnostic, never misleading success. Module resolves directory securely and uses validated relative operations; handles replacement races safely.

`/dev/scr-resets-monitor` root-only misc-device offers versioned bounded text request/response sessions through ordinary `read`/`write`, usable by Bash builtins. No ioctl helper/native administrative binary. Request limited to 256 bytes including newline; reject overlength, embedded NUL, unsupported protocol, extra commands, incomplete/invalid framing before execution. Per-open state accumulates partial writes safely; one complete request per session, one bounded terminal response. Module returns explicit success/error + count when applicable. Kernel rechecks privilege; pin module during active file descriptors. Wire grammar/version, maximum response size and errno mapping documented/tested during implementation; malformed input cannot reach VFS mutation.

Bash validates argument shape/transport bounds, sends literal request using quoted builtin `printf`, reads bounded response with builtin `read -r`, displays module count/diagnostic, maps status to exit code. No `eval`, date arithmetic, record enumeration, `find`, `wc`, deletion, own locks, retry loop, marker, cached count or truth. Semantic validation stays module-side. Absent/incompatible module or transport failure => explicit nonzero; no userspace filesystem fallback, implicit load or request replay. Lost response after reset reports outcome uncertain; never automatic retry.

Module serializes complete count/reset operations with recording worker through internal mutex/work cancellation. Frontend never holds persistent pause. Closing descriptor/process death releases transport resources; committed reset remains committed. Unexecuted incomplete request discarded. Count leaves pending event intact. Reset validates request first, cancels current-boot pending work, deletes scoped records, synchronizes directory, retains boot guard; pending work cannot recreate cleared event. Partial reset failure leaves cancellation active + explicit error; repeated explicit reset may finish deletion. No reset of hardware status, unrelated logs, baseline backup. Next boot counts normally.

Package removal uses generic baseline restoration after recorder shutdown; this is package lifecycle, never second administrative reset implementation. No monitor semantics delegated to Bash/frontend when module absent. Restoration manifest/namespace contract below supplies offline removal scope.

#### Debian ownership, backups, conflicts

Exactly one architecture-specific DEB: `scr-req-0001-goal-count-system-resets`, initial version `1.0.1`. Contains LKM + Bash frontend/boot integration/documentation/test helper. Internal module basename `scr_reset_monitor.ko` retained; user-facing component/paths consistently plural `scr-resets-monitor`. No published singular frontend alias; previous DRAFT never implemented, so no migration package needed.

Determine `armhf` versus `armel` from actual image; ARMv7 insufficient. Record build inputs/compiler/ABI/source revision, SHA-256, source/license notices, dependencies. `bash`, `kmod`, SysV and required shell/core filesystem utilities, including their `libc6` requirements, must exist in baseline-compatible versions; declare actual direct dependencies. No additional native administrative component, kernel/unrelated dependency upgrades, DKMS, target-side build. Missing dependencies reported before mutation.

Use approved SDLC scaffold; custom lifecycle reviewed/tested. Dpkg owns private `/usr/lib/scr-req-0001-goal-count-system-resets/payload`; maintainer scripts publish destinations only after backup. No managed conffiles; no `Replaces` seizure of third-party/kernel ownership.

| Managed surface | Ownership/restoration |
| --- | --- |
| `/usr/lib/scr-resets-monitor/scr_reset_monitor.ko` | Kernel-specific LKM, `0644 root:root`; documented runtime/build ABI. Direct private loading avoids `/lib/modules` index changes/`depmod`. |
| `/usr/sbin/scr-resets-monitor` | Bash frontend only, `0755 root:root`. |
| `/etc/init.d/scr-resets-monitor` | One-shot loader, `0755 root:root`; no reboot/shutdown action or reset-state decisions. |
| `/etc/rcS.d/S99scr-resets-monitor` | Exact symlink `../init.d/scr-resets-monitor`; no broad `update-rc.d` changes. |
| `/usr/share/doc/scr-resets-monitor/README` | ABI, control protocol, CLI, limits, deferred removal, `0644 root:root`. |
| `/usr/lib/scr-resets-monitor/package-test` | Non-destructive acceptance helper, `0755 root:root`; never loads ARM module into unrelated host kernel. |
| `/var/log/scr`, scoped reset records | Snapshot original directory existence/metadata + pre-existing scoped records before activation. Uninstall removes generated scoped records, restores baseline even after administrative reset. Preserve unrelated entries. Remove originally absent directory only when empty. |
| `/run/scr-resets-monitor`, `/dev/scr-resets-monitor` | Module-owned boot guard + dynamic device; remove created artifacts after worker shutdown/module absence. Verify no live registration. Preserve/refuse unexpected pre-existing ownership. |
| `/var/lib/scr-req-0001-goal-count-system-resets/sdlc-backup`, transaction journal | Root-only original-baseline contents/metadata + durable lifecycle phases/removal-pending marker. Retain through upgrades/incomplete removal; delete only after verified restoration. |
| `/var/lib/scr-sdlc/owners` requirement entry | Exact destinations + record-namespace claim. Remove only this package's claim after restoration; preserve shared registry/other entries. |

Preflight uses `lstat`, ownership queries, hashes. Unexpected code/loader/control paths => refusal, not replacement. Existing reset records backed up. Snapshot original absence, regular bytes, symlink targets, uid/gid, modes, timestamps, hard-link relationships where applicable, ACLs/xattrs/capabilities, directory metadata. Unsupported preservation = blocker. No move/delete outside listed runtime/package-transaction surfaces.

Backup/restore engine treats approved record namespace as package-managed dynamic surface; no count, filter, reason, boot or retry semantics. Initial baseline manifest records all scoped original paths. After confirmed recorder shutdown, compare final scoped surface against baseline: remove generated entries, restore original entries/metadata. Secure no-follow/identity checks and refusal on unsafe changes mandatory. Offline cleanup requires no LKM execution, and no frontend fallback. Module reset never touches baseline archive; package restoration never claims current reset count. Concurrent unrelated privileged edits cannot be silently overwritten; stop/report conflict, keep backups.

Registry rejects exact, parent/child, namespace overlap before mutation. Exclusive recorder + scoped-record claim does not claim unrelated `/var/log/scr` logs. Disjoint packages may coexist; test coexistence + overlap refusal. All produced packages = this single DEB; no hidden helper remains. Boot artifacts, `/etc/modules`, indexes, monit files, cron, `/mnt/usb` counters, kernel-owned paths must compare unchanged. Unknown ownership never grants overwrite permission.

#### Maintainer lifecycle, upgrades, interruption, rollback

| Script/phase | Required behavior |
| --- | --- |
| `preinst install` | Validate platform/dependencies/conflicts/backup capacity. Durably snapshot first baseline before destination mutation; journal intent/phase. Never replace original backup with partially installed state. |
| `postinst configure` | Stage payload + metadata, atomically publish destinations, establish directory/exact loader link, validate results, commit configured state. No module load from chroot/offline/live configuration; no install event. Idempotent reconfigure. |
| `preinst` / `prerm upgrade` | Preserve original baseline + generated records. Validate resident-module/control compatibility. Keep resident old module/guard through boot; no activation unload/reload. Reject incompatible upgrade before replacement. Snapshot previous payload; journal upgrade. |
| `postinst` failed/aborted upgrade | Restore prior compatible payload/activation state; preserve original archive + all events. New version activates next boot. Incompatible state/control ABI change requires amended plan. |
| `prerm remove` | Durably persist removal-pending first, disable loader link, request module quiescence/cancellation, close caller's control descriptors, unload safely. Module deregisters endpoint on successful exit. No force unload/reboot/shutdown. Failure returns nonzero before dpkg discards needed payload; keep backups, disabled activation, evidence, pending state. |
| `postrm remove` / `purge` | Confirm module absence, restore scoped dynamic surface + every baseline path/metadata through generic package engine, verify results, remove only created empty directories/runtime artifacts/own registry entry/backup/journal. Both remove/purge restore originals; purge never prerequisite. |
| `abort-install`, `abort-upgrade`, `failed-upgrade`, retries | Resume/reverse durable journal from verified state idempotently. Dpkg callbacks never reactivate after removal requested. Preserve last usable backup on every failure. |

Busy module => removal pending. Durable marker + disabled boot link prevent activation after reboot for unrelated reason. No agent/script/helper initiates reboot. Ordinary package removal retry after natural reboot completes with module absent. Failure to persist marker/disabled activation => explicit safety-condition failure; never claim removal success. Backups retained.

Transaction writes use temporary-file publication + required directory sync. Test interruption between every mutation/journal update, failed install/upgrade/removal. Rollback to original image = complete uninstall + verified restoration. Failed-upgrade rollback = previous installed payload + preserved first baseline. No restoration success with resident recorder, live endpoint, pending-removal flag or work capable of recreating files.

#### Tests and acceptance evidence

| Group | Required result |
| --- | --- |
| Source/platform | Reproducible existing-ABI module build. Safely reject wrong architecture/release/symbol versions/dependencies. No force load, rebuild, boot changes. |
| Authority/frontend | Bash source contains transport/help/shape checks only. Module alone performs cause/guard/create/retry/count/filter/reset. Direct protocol tests enforce same rules without frontend. Module absent gives frontend error; no filesystem fallback. Bounded malformed/fragmented/NUL/overlength/unsupported requests cannot mutate. Process death/lost response cannot replay reset or leave stale lock. |
| Names/time/filter | Empty/partial records count. Equal/invalid/backward time + forced suffix collisions never overwrite. Omitted components, inclusive UTC boundary, Gregorian errors/overflow tested. `--since last` rejected. Symlink/hardlink/replacement attacks, nonmatching files, unreadable directory, partial deletion preserve unrelated data + report failure. |
| Recording | Exclusive create before inode/directory sync before reason write. Fault every boundary; preserve correct pending/durable state, never duplicate. Read-only/full/EIO allow boot + bounded-frequency retry. Reason failure still counts. Count preserves pending; reset cancellation prevents recreation. |
| Boot/module | One observable-boot record across repeated starts, supported same-boot reload, reconfigure/upgrade. Module owns guard; no loader/frontend state authority. No offline-install/host-load events. Failed initialization tested. Pending removal suppresses next-boot activation. Clean unload cancels workers/removes endpoint; busy unload fails restoration + stays pending. |
| Package lifecycle | Fresh install/remove, install/purge, reinstall, v1-to-v2 upgrade/remove, failed-upgrade rollback, baseline directory/records, every interruption phase, repeated cleanup restore original managed state. Baseline survives operational reset/upgrade/failure. Overlap rejected; disjoint package/unrelated files preserved. Offline generic restoration works without module. |
| Image restoration | Continuous lock journal, before/after fingerprint + supplemental metadata, no leftover package claims/runtime recorder, original raw-image SHA-256 equality. Inject uninstall/restoration/unmount/source-verification failures; quarantine + block use. |
| Ready hardware | Compatible device: software reboot, watchdog, external reset, power-on/cycle, supported brownout/panic-associated reset with documented safe controls. Verify increments/raw reasons, unknown/combined handling. Short reset intervals + interruption around empty flush/reason write prove ext4/device boundary. Unexercised/unsupported causes explicitly unverified. |

Automated build, protocol/frontend, kernel-logic/state tests precede image package tests. Mounted ARM root/user-mode emulation cannot load ARM LKM into host or prove i.MX6 registers; helper detects boundary. Hardware tests deferred until artifact + safe lifecycle/non-hardware checks ready. Disruptive resets authorized; console/reflash problematic. Start supported ordinary reboot tests, advance only while recoverability established. Never reboot to fix uninstall. Exact hardware commands supplied only after source/device evidence makes them safe/meaningful.

#### Continuous-lock test and restoration proof

1. ACQUIRE SDLC image lock.
2. VERIFY no quarantine/conflicting mount.
3. RECORD original source SHA-256.
4. CREATE tooling-managed disposable image copy.
5. MOUNT copy through `./bin/lets scr image` within same lock.
6. CAPTURE baseline filesystem fingerprint + metadata/ownership evidence.
7. INSTALL exact hashed DEB through supported SDLC verifier.
8. RUN package + applicable functional/failure tests.
9. UNINSTALL every produced package, including after functional-test failure.
10. VERIFY baseline restoration, original records, no generated records/backup residue/active recorder/pending removal.
11. UNMOUNT copy through supported image tooling.
12. VERIFY original source SHA-256 unchanged.
13. ***if*** uninstall, restoration, unmount, source verification or cleanup failed ***then***
    1. QUARANTINE affected image identities.
    2. RETAIN phase journal/recovery evidence.
    3. STOP without clean unlock/reuse authorization; process-exit OS lock release never clears quarantine.
    4. REQUIRE tooling-reported recovery verification before reuse; never remove marker manually.
14. ***else***
    1. RECORD successful restoration evidence.
    2. RELEASE image lock.

Preferred entry: `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-resets-monitor/package-test`. Supported image commands run inside its lock. Custom workflow only within one `./bin/lets sdlc lock-run` spanning mount/install/test/uninstall/restoration/unmount/unlock. Separate phase locks forbidden. Bare lock wrapper insufficient without enforced cleanup/quarantine/restoration. Existing tooling only; missing capability reported, never bypassed.

Proof scopes distinct: uninstall restores every managed path, original record, metadata/ownership and original absence on disposable filesystem; unchanged source SHA-256 proves shared raw image byte-identical. Dpkg DB/log bookkeeping may differ inside disposable copy; never claim uninstall yields raw-byte identity. Enumerate verifier exclusions; no managed path hidden. Supplement timestamps, hard links, xattrs/ACLs/capabilities, parent-directory metadata and created-directory cleanup beyond default fingerprint. Pending removal/changed unrelated protected paths = failure, never exclusion.

#### Deliverables and gate

After approval: source/build provenance; single reversible DEB + SHA-256; full ownership/backup manifest; lifecycle/fault tests; restoration + source-image proofs; technical limits; ready hardware procedure. Persist implementation/independent validation only through `./bin/lets sdlc ...`. DRAFT changes no implementation/image.

Deterministic policy facts: six payload destinations, defined tests, custom maintainer scripts, boot/service activation, kernel privilege/security, persistent storage. No known existing SDLC overlap; preflight must prove absence. Nontrivial risks explicit. Only tooling may waive approval; otherwise committed DRAFT revision/hash waits developer approval/amendment. Approval covers specified LKM/module-authority/Bash work, never kernel rebuild or reduced durability.

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

- `2026-09-17T13:12:49+00:00` [drafting-plan] Updated round 1 requirements-analysis section

- `2026-09-17T13:12:58+00:00` [drafting-plan] Updated round 1 image-analysis section

- `2026-09-17T13:13:08+00:00` [drafting-plan] Updated round 1 planner-questions section

- `2026-09-17T13:13:18+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-17T13:13:48+00:00` [draft-ready] Committed DRAFT revision 2: module sole detection/cause/record/retry/count/filter/reset/serialization/pending-event/boot-guard authority; scr-resets-monitor Bash transport only. Current analysis/Q&A compressed, exact evidence/source/history preserved; prior DRAFT retained as superseded audit. Existing-kernel LKM only; six payload paths, custom reversible lifecycle, original backups across upgrades, generic offline restoration after unload, continuous image lock and quarantine tests defined. Recorded developer answers resolve policy choices; ABI/VFS/durability/tooling gates remain. No implementation.

- `2026-09-17T13:13:57+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-17T13:41:05+00:00` [awaiting-approval] Split approved-plan candidate into 8 bounded tasks

- `2026-09-17T13:41:09+00:00` [approved] Developer directed pipeline task split and sequential execution; approving DRAFT revision 2 bound to task manifest.

- `2026-09-17T13:41:54+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets
