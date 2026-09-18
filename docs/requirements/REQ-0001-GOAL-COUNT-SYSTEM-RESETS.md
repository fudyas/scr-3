---
schema: 1
id: REQ-0001-GOAL-COUNT-SYSTEM-RESETS
title: Count system resets reliably
state: implementing
round: 1
sequence: 88
approval: approved
implementation_branch: sdlc-req/req-0001-goal-count-system-resets
implementation_commit: 7610f9249db5640e7db82fbed20d23ff1f3b6c6d
updated: 2026-09-18T16:40:55+00:00
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

#### Revision 6 implementation checkpoint

Approved DRAFT revision 6 SHA-256 `eaa5b1ea6f36bf64e3c18d9301ffbb90f6581fdbea3c0198907ae814315e4242` implemented through bounded diagnostic probe in designated worktree. No production release, DEB, image mutation, boot, or reboot.

LETS environment:

- `./bin/lets devenv init` owns pinned Linaro archive plus seven pinned Ubuntu Trusty i386 packages under `.lets/toolchains`.
- Exact URLs/versions/architectures/sizes/SHA-256 values match revision 6. Safe ar/tar inspection rejects unexpected members, traversal, special files, escaped links, wrong metadata, missing license evidence. No APT/dpkg/scripts/triggers/`ldconfig`/`sudo`/global install.
- Managed loader/library path runs allowlisted ELF32 i386 tools and GCC subprograms. Environment strips overrides; locale `C`. All compiler/binutils calls use `./bin/lets toolchain`.
- Functional suite passes all 13 allowlisted tools plus ELF32 ARM smoke compile. Idempotent second init skips verified generation; sentinel mtime `1789733939` unchanged.
- Toolchain archive size `51126392`; SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`.
- GCC `4.8.3 20140401 (prerelease)`; binutils `2.24.0.20140311 Linaro 2014.03`.

Old endpoint `192.168.68.56` failed config reacquisition: one `scp` close; SSH `ConnectTimeout=10`, three `ConnectTimeout=5`, later `ConnectTimeout=10` timed out. Empty partial SHA `e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855` rejected. Developer changed endpoint to `192.168.68.55`; ignored credential host updated, secret preserved, mode `0600`.

New endpoint gates:

- Identity `SCR-7CCC91`; kernel `3.10.105-imx6 #5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018 armv7l`; root.
- Config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; uImage MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`.
- NXP source commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`; reconstructed release `3.10.105-imx6`.
- Two builds matched SHA-256 `1377d6cae2339aedf00647a8e78b7aefed54c206a40927fb241cae0e12245334`.
- ELF/attributes/vermagic/symbol/disassembly gate passed. Relocation `3` absent; emitted `R_ARM_NONE`, `R_ARM_ABS32`, `R_ARM_CALL`, `R_ARM_JUMP24`, `R_ARM_PREL31` supported by reconstructed loader.

Sole live retry consumed:

- Baseline taint `4096`; probe/path absent; `/proc/modules` SHA-256 `4ad4f5e875ed244ec909d71af3857132e1b663aef98c6c0a11bfcaaf350e9b2c`.
- Transient root-owned mode `0600`; remote SHA exact.
- Ordinary `insmod` rc `0`; exact init log only; live refcount `0`; taint `4096`.
- Ordinary `rmmod` rc `0`; exact exit log only; module absent; taint `4096`.
- Transient removed. Final module-table/config/uImage hashes exactly baseline; connectivity healthy. No anomaly or quarantine condition.

Current blocker: diagnostic success proves callbacks only. Approximate source, Linaro GCC 4.8.3 prerelease versus live GCC 4.8.4, missing exact vendor tree/build recipe/generated headers/`Module.symvers` prevent stronger production-specific ABI/integration proof. Stop before production source/package/DEB/image test. Live retry exhausted.

Safety preserved: no host/target APT, direct compatibility tools, force, VFS/MMIO probe behavior, persistence, activation, boot/reboot, kernel/U-Boot patch, image mount/install, package action. Evidence: `evidence/revision-6/toolchain-runtime.md`, `evidence/revision-6/probe-live.md`; boundary: `RELEASE.md`.

## Revision 4 approximate ABI probe — live result

Result: clean compatibility FAIL. Production module/DEB blocked.

Target reachable `2026-09-17T16:43:55Z`: `SCR-7CCC91`, kernel `3.10.105-imx6`, ARMv7, uptime `27754.52s`. Pre-existing taint `4096`; root usage 38%; active `ttymxc0` + operator SSH; recovery path unchanged. Live config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; `/boot/uImage-3.10.105-imx6` MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`; pre-test dmesg 978 lines, SHA-256 `65074e0b80decd7e730bdf020f093b9aed5ec57c9f92f17263d20668607b4919`.

Initial ARMv5T artifact rejected before target use. Rebuilt host-only GCC 12/binutils 2.42 probe with `KCFLAGS=-march=armv7-a`. Final artifact: `evidence/revision-4/probe/scr_approx_abi_probe-87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07.ko`; SHA-256 `87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07`. `readelf -A` exactly matched deployed sample (`cmp=0`): 7-A/v7/Thumb-2/v6 unaligned. Vermagic exact. Undefined symbols only `printk`, `__aeabi_unwind_cpp_pr0`; both live exports.

Copied only `/root/.scr-req-0001-approx-abi-probe.ko`, mode `0600 root:root`; remote hash verified. Ordinary `insmod` returned rc `1`:

`insmod: ERROR: could not insert module /root/.scr-req-0001-approx-abi-probe.ko: Invalid module format`

Sole dmesg delta:

`[27840.175560] scr_approx_abi_probe: unknown relocation: 3`

Module never initialized/loaded. Taint stayed `4096`. No init log or kernel anomaly. Per approved clean-rejection branch: no altered rebuild/retry; `rmmod` skipped because module absent. Removed transient file and verified absence. Config/uImage unchanged. SSH/console/recovery usable. `/proc/modules` delta only unrelated `ipv6` refcount `53` to `56` during SSH; probe absent.

No APT, reboot, boot activation, package, kernel, U-Boot, image change, quarantine condition, or residue. Evidence hashes: `RELEASE.md` `e155e39610b1384106a084dd9cd2d6e503c1f5187a047bd71f264935e58c0ad1`; live `16836d9af2ff5f7da2257487efeda7ec3b29c9ae470604b1b95f3559eace2f9d`; reconstruction `95be0754198d97de3d99819ec6fcd7e6c3b6675ef035e348b6329ec0a3ca5470`; static `ad13f1a8ce33bc871ff8310c419c7cf3c2c18dc63198c6589290fddfe3d8bc4f`.

`./bin/lets sdlc test`: `26 passed in 1.66s`. No implementation commit. Next technical gate: build with ARM GCC/binutils compatible with 2018 Ubuntu/Linaro GCC 4.8.4 kernel so output uses relocations accepted by target 3.10 module loader; repeat only under newly approved probe plan.

## Revision 4 probe implementation — blocked at live connectivity

Built bounded approximate-source diagnostic module only. No production counter DEB.

Source reconstruction: NXP `imx_3.10.53_1.1.0_ga_caf` tag peel `39b048b9e31e14ecd7beb05e6f5cdd93d6323699`, checkout `e35e57f24ef5851787812a18a38feeb9deb6ea46`, stable `v3.10.105` tag object `4d6dc2538f6ede3b25fdf30abdf2cda0f1b072c3`, live config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`, reconstructed `PAGE_OFFSET=0x6C000000`. Host build used GCC 12/binutils 2.42; target APT unchanged.

Artifact: `evidence/revision-4/probe/scr_approx_abi_probe-d9637c9a40bdfc38fd245027c1fb226eec653bf9f44275be823e3246a1bf1619.ko`. SHA-256: `d9637c9a40bdfc38fd245027c1fb226eec653bf9f44275be823e3246a1bf1619`.

Static gates: ELF32 little-endian ARM EABI5; vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `; undefined symbols only `printk`, `__aeabi_unwind_cpp_pr0`; disassembly shows fixed-log `module_init` returning `0` and fixed-log `module_exit`; no VFS, MMIO, worker, timer, persistence, boot activation, counter logic, force-load behavior.

Live preflight blocked before copy/load. SSH attempts:

- `2026-09-17T16:38:59Z`: `ssh: connect to host 192.168.68.56 port 22: Connection timed out`, rc `255`.
- `2026-09-17T16:39:04Z`: same timeout, rc `255`.
- `2026-09-17T16:39:09Z`: `ssh: connect to host 192.168.68.56 port 22: Connection refused`, rc `255`.

No remote command, target/image mutation, probe copy, `insmod`, `rmmod`, APT change, reboot, or DEB. Credentials stayed environment-only; secret not persisted in evidence. Live blocker evidence SHA-256: `ab24687b722a3fefd3f075640f266eafb425a6672f49cfc011282514fbe65cf8`.

Added `RELEASE.md`, reconstruction/static/blocker evidence, probe source/Makefile/artifact. `./bin/lets sdlc test`: `26 passed in 2.03s`. Production remains blocked until live probe completes and stronger production ABI gates pass.

## Revision 3 implementation attempt — blocked before build

Approved DRAFT revision 3 SHA-256: `42a33ec51bfd585df1d382afc984fb5ee1eddc418eae51dea0e99368ca0e8d7c`.

Result: BLOCKED. No DEB produced. No image/target mutation, module load/unload, reboot, APT mutation, kernel/U-Boot/boot-artifact change, monit/cron/watchdog change, or reset-record creation.

Read-only live baseline confirms exact target: `root@192.168.68.56`, hostname `SCR-7CCC91`, running `3.10.105-imx6`; `/proc/version` build `developer@scr-dev-Eldad`, GCC `4.8.4 (Ubuntu/Linaro 4.8.4-2ubuntu1~14.04.1)`, `#5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018`. `/boot/config-3.10.105-imx6` and decompressed `/proc/config.gz` SHA-256 both `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`. GNU build-id: `f7b0840244f238080194bd87ce76c704a67db004`. Sample module vermagic: `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `. `CONFIG_MODVERSIONS` and `CONFIG_MODULE_SIG` unset; custom `CONFIG_VMSPLIT_2G_OPT=y`, `CONFIG_PAGE_OFFSET=0x6C000000`. `/run` verified tmpfs `0755 root:root`, 10 MiB.

Exact ABI inputs absent: no live `/lib/modules/3.10.105-imx6/{build,source}`; no matching headers/generated headers/build tree/`Module.symvers`; `/usr/src` lacks inputs; installed dpkg kernel remains `linux-image-3.10.53-lec-imx6` version `7`; target Debian Jessie APT sources expose no `linux-source` or `linux-headers-3.10.105-imx6` candidate; no target APT update/install performed. Matching Ubuntu/Linaro GCC binary/build recipe absent.

Non-mutating public provenance exhausted: official `https://github.com/ADLINK/linux.git` refs expose current 5.15/6.6/6.18 branches plus `master`, no 3.10/i.MX6 branch/tag; public recursive tree/commit search yields no exact `3.10.105-imx6` source binding. NXP `imx_3.10.53_1.1.0_ga_caf` remains near-match only; custom config and unresolved ADLINK patches prevent exact-source claim.

Live `/proc/kallsyms` proves `__ksymtab_*` entries for candidate VFS/misc/workqueue/random calls, but export presence cannot prove prototypes, layouts, generated-header compatibility, compiler ABI, or safe build. `CONFIG_MODVERSIONS=n` removes CRC checks; matching vermagic from approximate source would still not satisfy approved exact-ABI-before-load gate. No force load, version bypass, unexported-symbol trick, speculative compile, package, transfer, or live load attempted.

Evidence: implementation worktree `evidence/revision-3/abi-blocker.md` and `evidence/revision-3/safety.json`. Required unblock: source commit/tree and recipe demonstrably producing build-id `f7b0840244f238080194bd87ce76c704a67db004`, or coordinator-approved equivalent exact provenance, plus exact generated headers/config/toolchain and successful external-module compile/modpost/ELF/vermagic/undefined-symbol verification. Then module/package/live controlled checks may proceed.

Deviation: worktree-local LETS runtime absent; SDLC operations executed only as `/home/fudya/devel/scr/./bin/lets sdlc ...` from main project, targeting same durable ledger/worktree. No `implementation-commit` run; coordinator owns commit and next gate.

## Attempt 2 — blocked

Result: BLOCKED. No DEB produced. No image mutation, module load, or reboot.

Mount blocker resolved. Command:

`./bin/lets sdlc lock-run --image /home/fudya/devel/scr/var/image_8.26.0 ./bin/lets scr image parts --image /home/fudya/devel/scr/var/image_8.26.0`

Exit: `0`. Result: `whole /dev/loop2 3.6GB`. Image SHA-256 unchanged: `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`.

Hard blockers remain:

- Exact vendor `3.10.105-imx6` source/build tree absent.
- Matching build `.config`, generated headers, and `Module.symvers` absent.
- Matching Ubuntu/Linaro GCC 4.8.4 binary/build recipe absent.
- `/lib/modules/3.10.105-imx6/{build,source}` absent.
- `/usr/src` empty.
- Installed GCC: `4.9.2`.
- dpkg kernel: `3.10.53`.

Cannot pass compile/modpost/link ABI probe. Building DEB would violate approved plan. SRC exact-target read lifetime and retained-counter absence remain unproved. Restoration fingerprint still omits timestamps, hard links, ACLs, xattrs, capabilities.

Corrected T01 contracts: fallible `PREPARE_REMOVE` before unload because `module_exit` cannot veto; guard I/O retains one unverified pending event; created-unsynced inode retries same inode, never duplicates. Updated owned `contracts/*` and `evidence/feasibility/*` only.

Test: `./bin/lets sdlc test` => `25 passed in 1.34s`.

No `task-result` or `implementation-commit` run. Pipeline must remain `implementing` until required kernel inputs, toolchain recipe, and remaining proof gaps are resolved.

## Attempt 2 — blocked

Result: BLOCKED. No DEB produced. No image mutation, module load, or reboot.

Mount blocker resolved. Command:

`./bin/lets sdlc lock-run --image /home/fudya/devel/scr/var/image_8.26.0 ./bin/lets scr image parts --image /home/fudya/devel/scr/var/image_8.26.0`

Exit: `0`. Result: `whole /dev/loop2 3.6GB`. Image SHA-256 unchanged: `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`.

Hard blockers remain:

- Exact vendor `3.10.105-imx6` source/build tree absent.
- Matching build `.config`, generated headers, and `Module.symvers` absent.
- Matching Ubuntu/Linaro GCC 4.8.4 binary/build recipe absent.
- `/lib/modules/3.10.105-imx6/{build,source}` absent.
- `/usr/src` empty.
- Installed GCC: `4.9.2`.
- dpkg kernel: `3.10.53`.

Cannot pass compile/modpost/link ABI probe. Building DEB would violate approved plan. SRC exact-target read lifetime and retained-counter absence remain unproved. Restoration fingerprint still omits timestamps, hard links, ACLs, xattrs, capabilities.

Corrected T01 contracts: fallible `PREPARE_REMOVE` before unload because `module_exit` cannot veto; guard I/O retains one unverified pending event; created-unsynced inode retries same inode, never duplicates. Updated owned `contracts/*` and `evidence/feasibility/*` only.

Test: `./bin/lets sdlc test` => `25 passed in 1.34s`.

No `task-result` or `implementation-commit` run. Pipeline must remain `implementing` until required kernel inputs, toolchain recipe, and remaining proof gaps are resolved.

## Attempt 2 — blocked

Result: BLOCKED. No DEB produced. No image mutation, module load, or reboot.

Mount blocker resolved. Command:

`./bin/lets sdlc lock-run --image /home/fudya/devel/scr/var/image_8.26.0 ./bin/lets scr image parts --image /home/fudya/devel/scr/var/image_8.26.0`

Exit: `0`. Result: `whole /dev/loop2 3.6GB`. Image SHA-256 unchanged: `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`.

Hard blockers remain:

- Exact vendor `3.10.105-imx6` source/build tree absent.
- Matching build `.config`, generated headers, and `Module.symvers` absent.
- Matching Ubuntu/Linaro GCC 4.8.4 binary/build recipe absent.
- `/lib/modules/3.10.105-imx6/{build,source}` absent.
- `/usr/src` empty.
- Installed GCC: `4.9.2`.
- dpkg kernel: `3.10.53`.

Cannot pass compile/modpost/link ABI probe. Building DEB would violate approved plan. SRC exact-target read lifetime and retained-counter absence remain unproved. Restoration fingerprint still omits timestamps, hard links, ACLs, xattrs, capabilities.

Corrected T01 contracts: fallible `PREPARE_REMOVE` before unload because `module_exit` cannot veto; guard I/O retains one unverified pending event; created-unsynced inode retries same inode, never duplicates. Updated owned `contracts/*` and `evidence/feasibility/*` only.

Test: `./bin/lets sdlc test` => `25 passed in 1.34s`.

No `task-result` or `implementation-commit` run. Pipeline must remain `implementing` until required kernel inputs, toolchain recipe, and remaining proof gaps are resolved.

## Attempt 2 — blocked

Result: BLOCKED. No DEB produced. No image mutation, module load, or reboot.

Mount blocker resolved. Command:

`./bin/lets sdlc lock-run --image /home/fudya/devel/scr/var/image_8.26.0 ./bin/lets scr image parts --image /home/fudya/devel/scr/var/image_8.26.0`

Exit: `0`. Result: `whole /dev/loop2 3.6GB`. Image SHA-256 unchanged: `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`.

Hard blockers remain:

- Exact vendor `3.10.105-imx6` source/build tree absent.
- Matching build `.config`, generated headers, and `Module.symvers` absent.
- Matching Ubuntu/Linaro GCC 4.8.4 binary/build recipe absent.
- `/lib/modules/3.10.105-imx6/{build,source}` absent.
- `/usr/src` empty.
- Installed GCC: `4.9.2`.
- dpkg kernel: `3.10.53`.

Cannot pass compile/modpost/link ABI probe. Building DEB would violate approved plan. SRC exact-target read lifetime and retained-counter absence remain unproved. Restoration fingerprint still omits timestamps, hard links, ACLs, xattrs, capabilities.

Corrected T01 contracts: fallible `PREPARE_REMOVE` before unload because `module_exit` cannot veto; guard I/O retains one unverified pending event; created-unsynced inode retries same inode, never duplicates. Updated owned `contracts/*` and `evidence/feasibility/*` only.

Test: `./bin/lets sdlc test` => `25 passed in 1.34s`.

No `task-result` or `implementation-commit` run. Pipeline must remain `implementing` until required kernel inputs, toolchain recipe, and remaining proof gaps are resolved.

### Validation

Result: fail

# Revision 7 independent validation

Result: FAIL. Do not merge commit `7610f9249db5640e7db82fbed20d23ff1f3b6c6d`. Do not release DEB SHA-256 `119b0c760bf76e8e765f92877f232f99170648c0562fc75d7092edb351be1f50`.

Validated binding: approved plan revision 7 SHA-256 `3b397ef90c63e6037302d7ca4eab7dd47773017ba26c538e24be60e811300ad6`; implementation commit `7610f9249db5640e7db82fbed20d23ff1f3b6c6d`; module SHA-256 `091a20b51f95b1f56110aa89ce1830b0cfb59bec8a9bfa1e17065732e26ce15d`; final DEB SHA-256 `119b0c760bf76e8e765f92877f232f99170648c0562fc75d7092edb351be1f50`.

## Evidence mapping

- Reproducible/static build: PASS in implementation evidence. Two production builds matched. Module is ELF32 little-endian ARM EABI5. Vermagic exactly `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `. Relocation type `3` absent. Undefined symbols mapped to target `System.map` exports. No MMIO/register/reset-reason code. LETS-managed approximate NXP source/toolchain boundary documented.
- Manual HW lifecycle: PASS for exercised path on `192.168.68.55`. Ordinary load/unload/reload passed. First init made one empty mode `0600` record; repeated loader and same-boot reload made zero. Count, timestamp filter, reset passed. Taint stayed `4096`; expected logs only.
- Disposable-image lifecycle: PASS in recorded evidence. Continuous `lock-run`, install/test/remove, full managed-surface fingerprint restoration, unmount, unchanged source SHA-256 `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`. Quarantine recovered through tooling `--recover`; no manual marker removal.
- Target cleanup: PASS for exercised failed-boot test state. Package removed/purged. Module, device, guard, records, transient DEB, payload, package status/info absent. Config SHA-256 and uImage MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c` unchanged. Taint `4096`; connectivity healthy.
- RELEASE boundary: PASS. States observable module-init count only; pre-init events, reasons, MMIO, kernel/U-Boot patching, exact-vendor ABI certainty, storage/clock limits excluded.
- SDLC tests: PASS, `26 passed in 1.44s`.

## Blocking findings

1. Automatic boot acceptance FAIL. After sole authorized ordinary reboot, target returned healthy, but module, `/run/scr-resets-monitor.boot-guard`, `/dev/scr-resets-monitor`, and boot record were absent. `/etc/rcS.d/S10scr-resets-monitor` existed. Requirement needs exactly one event on next boot reaching module initialization; observed delta was zero. Manual load success cannot substitute.

2. Exact activation cause unproved. Current init metadata says `Default-Start: S`; package installs only `/etc/rcS.d/S10scr-resets-monitor`. Evidence proves this path ineffective on target, not why. Do not blindly rename link. Revision 8 must inspect exact target SysV sequence/runlevel/logs read-only, then choose dependency-correct registration. Target PID 1 previously reported SysV runlevel `2`; `/etc/rc2.d` activation is likely, but must be proven. Use package-managed `update-rc.d` only if target behavior and reversible baseline handling are proven. Another bounded reboot is required because boot acceptance cannot be established otherwise.

3. Retry can duplicate one boot event. `scr_create_record()` creates/closes new random record, then syncs parent. If record fsync succeeds but parent sync fails, function returns error while first inode remains. Worker retries `scr_create_record()` with new random path. Result: two or more countable files for one module init. This violates one-event-per-observable-boot and earlier created-unsynced-inode retry contract. Persist pending pathname/state and retry same inode/parent sync; add injected parent-sync-failure test proving no duplicate.

4. Guard sync errors discarded. `scr_claim_guard()` logs fsync/parent-sync error then returns `0`. Module treats guard as durable and stops guard retry. Crash can lose guard and allow same-boot recount. Return real error; retain/retry exact guard claim state without converting existing same-boot guard into completed event loss. Add file-sync and parent-sync fault tests.

5. Uninstall restoration incomplete when module absent. `prerm` runs `--reset` only when `scr_reset_monitor` is loaded. If records exist but module is absent, remove/purge leaves records; `postrm` only attempts `rmdir /var/log/scr`, which fails silently when nonempty. Violates uninstall-generated-record deletion and universal restoration invariant. Add safe package-owned record cleanup for absent-module path, bounded exact-name/type checks, baseline preservation, failure-stop behavior, and lifecycle tests for module-loaded, module-absent, failed-activation, upgrade, remove, purge, abort.

6. Package metadata wrong for architecture-specific payload. Final artifact is `_all.deb` and declares `Architecture: all`, but contains ARM kernel module. Set `Architecture: armhf`; eliminate stale alternate DEB ambiguity; reproduce one canonical artifact/hash.

7. Acceptance tooling FAIL: `./bin/lets sdlc acceptance REQ-0001-GOAL-COUNT-SYSTEM-RESETS` reports `task manifest approved-plan hash does not match current approval`. Rebind/regenerate task manifest through SDLC tooling before next validation; never edit ledger manually.

## Safest next round

Revision 8: fix record/guard retry state; fix absent-module uninstall cleanup; emit one `armhf` DEB; inspect target SysV boot path; install dependency-correct reversible activation; rerun static/reproducibility tests, full locked disposable-image install/upgrade/remove/purge/abort restoration, then exact-HW manual lifecycle. Authorize one bounded ordinary reboot only after preflight. Require module + guard + device + exactly one new record after reconnect; then disable activation, unload, uninstall all produced packages, remove transient artifact, and prove exact baseline restoration. Any cleanup/restoration failure quarantines image/device; no force, target APT, kernel/U-Boot/boot-artifact mutation, or credential persistence.

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

### Solution plan — DRAFT revision 3

#### DRAFT revision 3 — observable module-initialization boot counter

Round 1, `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. Supersedes approved DRAFT revision 2 after developer amendment checkpoint at sequence 33. Earlier drafts, approval, task evidence, failures remain audit history; none authorizes old reset-cause/MMIO/kernel-source/U-Boot work. No implementation/image mutation authorized by this DRAFT. All load-bearing decisions answered. No new developer question.

#### Sources, evidence, revised boundary

Reviewed full durable REQ, customer source, image analysis, Q&A, DRAFT revisions 1-2, approval/task history, implementation Attempt 2 evidence, amendment checkpoint, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/MONIT.md`.

Verified target evidence remains: ADLINK LEC-iMX6 Quad/Dual SMARC, Debian 8 Jessie, ARMv7, SysV, running `3.10.105-imx6`; `/` = `/dev/root` ext4 `rw,noatime,errors=remount-ro,data=ordered`; `/var/log/scr` absent; `/boot` ext2; image marker `8.26.0`; `/boot/uImage-3.10.105-imx6` MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`; installed kernel package metadata says `linux-image-3.10.53-lec-imx6` version `7`, so metadata does not prove running ABI. Local `var/image_8.26.0` = 3,850,371,072 bytes. Later locked partition probe succeeded: `whole /dev/loop2 3.6GB`; source SHA-256 stayed `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`.

Attempt 2 found exact vendor `3.10.105-imx6` source/build tree, matching generated headers, `Module.symvers`, Ubuntu/Linaro GCC 4.8.4 binary/recipe absent; `/lib/modules/3.10.105-imx6/{build,source}` absent; `/usr/src` empty; installed GCC `4.9.2`; dpkg kernel `3.10.53`. Old compile/modpost/link ABI probe therefore blocked. `./bin/lets sdlc test` result: `25 passed in 1.34s`. Restoration fingerprint omitted timestamps, hard links, ACLs, xattrs, capabilities. No DEB, image mutation, module load, reboot, `task-result`, or `implementation-commit` occurred.

New binding semantics: counter measures exactly one observable boot reaching `scr_reset_monitor` module initialization. It does not measure every physical reset. Resets/boots ending before module initialization remain uncounted. Supported same-boot unload/reload must not add another event. Record has no reset cause/reason. Drop all i.MX6 SRC/register access, direct MMIO, reset decoding, retained-reset-counter research, kernel-source patching, U-Boot-source/bootloader patching, kernel/U-Boot replacement, and claims about physical-reset completeness. EOL platform lacks supported source route. Reset-loop detection/mitigation remains out of scope.

Proceed with minimal OOT test module, reversible DEB, Bash administration frontend only where needed, and controlled live-device load/unload/reload/boot checks under approved safety/recovery rules. OOT means separately built loadable module, never kernel-tree patch. Exact running-ABI load compatibility still must be demonstrated before live `insmod`; missing compatible build inputs blocks load test, never permits force load, source patching, kernel replacement, target APT mutation, or unsupported claim.

#### Deliverable and package ownership

Produce exactly one architecture-specific Debian package: `scr-req-0001-goal-count-system-resets`, next implementation version chosen above abandoned/unpublished artifact version and recorded. Determine `armhf`/`armel` from target dpkg evidence. No DKMS, target build, target `apt-get`, dependency upgrade, kernel package, U-Boot package, initramfs/DT/boot-selector edit, `/lib/modules` index change, `depmod`, monit/cron/watchdog/USB-counter change.

Package private payload root: `/usr/lib/scr-req-0001-goal-count-system-resets/payload`. Dpkg owns payload there; maintainer scripts publish managed destinations only after baseline backup.

| Managed surface | Owner and restoration |
| --- | --- |
| `/usr/lib/scr-resets-monitor/scr_reset_monitor.ko` | Minimal OOT module, `0644 root:root`; exact build/runtime ABI evidence. Direct `insmod`; no force/version bypass. |
| `/usr/sbin/scr-resets-monitor` | Bash frontend, `0755 root:root`; argument validation, request transport, output only. No count/delete/guard/event truth. |
| `/etc/init.d/scr-resets-monitor` | One-shot SysV loader, `0755 root:root`; checks removal-pending + ABI, loads exact module. No event/guard decision, reboot, package install, APT action. |
| `/etc/rcS.d/S99scr-resets-monitor` | Exact symlink `../init.d/scr-resets-monitor`; prove root and guard storage ready before load. No broad `update-rc.d`. |
| `/usr/share/doc/scr-resets-monitor/RELEASE.md` | `0644 root:root`; explicit in-scope/out-of-scope, observable initialization boundary, early-boot/physical-reset limits, same-boot reload rule, storage/clock/ABI limits, install/remove/upgrade/test/live-device notes, safety/recovery rules. |
| `/usr/lib/scr-resets-monitor/package-test` | `0755 root:root`; non-destructive package checks; never loads ARM module into unrelated host. |
| `/var/log/scr/reset-<epochMs>-<suffix>` | Module-created empty event files only. `epochMs` signed decimal UTC kernel-wall-clock milliseconds; suffix `[a-z]{4}`; `0600 root:root`; exclusive create/no overwrite. |
| `/run/scr-resets-monitor/boot-guard` and `/dev/scr-resets-monitor` | Module-owned same-boot guard semantics + root-only dynamic control endpoint. Package scripts touch runtime artifact only after confirmed module absence during restoration. |
| `/var/lib/scr-req-0001-goal-count-system-resets/` | Root-only first-baseline backup, ownership manifest, durable package journal, removal-pending marker. Retain across upgrades/failures; delete only after verified restoration. |
| `/var/lib/scr-sdlc/owners` entry | Exact destinations + runtime namespace claim. Preserve registry/other claims; remove own claim only after restoration. |

Preflight uses `lstat`, dpkg ownership, hashes, no-follow checks. Refuse unexpected code/loader/control/guard ownership and exact/parent/child/namespace overlap. Preserve unrelated `/var/log/scr` entries. Snapshot original absence/content/type/symlink target/uid/gid/mode/timestamps/hard links/ACLs/xattrs/capabilities and parent-directory metadata. Unsupported preservation blocks mutation. Existing matching records become baseline and must be restored even after `--reset`. No `Replaces`, conffile seizure, or broad deletion.

#### Module event, guard, file, CLI contract

Module initialization is event boundary. Successful supported initialization accepts one event for current observable boot. Failed initialization before acceptance creates no event. Physical cause irrelevant and never read. Module never accesses i.MX6 registers/MMIO.

Module alone owns event recording, guard state, selected filename, retries, count/filter/reset semantics, serialization, cancellation. Loader and Bash contain no duplicate truth. Guard must survive supported same-boot clean unload/reload but reset between boots. Before implementation, prove target `/run` boot lifecycle or another approved kernel-visible boot identity. If `/run` is not reliably cleared/recreated once per boot and no safe existing-kernel boot identity exists, stop as technical blocker; do not shift truth to loader/Bash.

Guard state records `pending:<filename>`, `complete:<filename>`, or `cancelled` using bounded validated content. Module creates/updates it atomically and synchronizes containing runtime directory as supported. First initialization claims absent guard and selects one filename. Reload reading `pending` resumes same filename/inode state; reload reading `complete` or `cancelled` creates nothing. Corrupt/unsafe/replaced guard fails module initialization without record. Guard is same-boot deduplication, not persistent reset counter.

No-reason format = empty regular file. Old create-before-reason-write sequence no longer applies because no reason write exists. Required durable ordering:

1. ACCEPT current observable-boot event during module initialization.
2. CLAIM module-owned same-boot guard.
3. SELECT one `reset-<epochMs>-<suffix>` name; persist it as `pending` before any record create.
4. QUEUE process-context worker; return without blocking boot.
5. RESOLVE `/var/log/scr` without unexpected symlink/alternate mount.
6. CREATE missing directory `0755 root:root`; synchronize parent before claiming directory persistence.
7. CREATE empty record with exclusive no-follow semantics and `0600 root:root`.
8. ***if*** collision occurs ***then*** choose another suffix, durably update pending guard first, maximum 64 attempts per invocation.
9. RETAIN same record identity across retries; never create second file after successful create.
10. SYNCHRONIZE empty inode, then containing directory.
11. ***if*** both succeed ***then*** atomically mark guard `complete` and synchronize guard directory.
12. ***if*** storage is read-only/full/EIO/unavailable ***then*** retain one pending event/name, log rate-limited error, retry 1 second exponential to 60 seconds, never block boot or reboot.

Crash/reset before empty inode + directory durability can lose event; another boot before module initialization remains uncounted. Device may violate flush guarantees. `RELEASE.md` states limits. No write follows creation except filesystem metadata needed for empty file. Empty file itself counts.

Commands remain `scr-resets-monitor --count [--since <timestamp>]`, `scr-resets-monitor --reset`, help. `--since` exact `yyyy-mm-dd[ hh[:mm[:ss]]]` UTC; omitted components zero; inclusive `eventTime >= sinceTime`; reject `--since last`, timezone suffix, leap second, invalid Gregorian date/range/overflow/trailing text/conflicts. Module parses semantics. Bash validates shape/bounds, transports literal versioned bounded request through `/dev/scr-resets-monitor`, prints response, maps exit. No filesystem enumeration/deletion/date math/retry/fallback/implicit load.

Scope: immediate non-symlink regular empty files whose complete names match grammar and timestamps parse. Non-empty matching files, symlinks, hard links, malformed names unsafe/non-counted and never deleted; report error where operation cannot give complete truthful result. Count success prints integer + newline. Missing directory = zero/no-op. Reset cancels current pending event, writes `cancelled` guard, deletes only generated scoped records, syncs directory, preserves baseline archive/unrelated files. Partial reset reports nonzero; cancelled state prevents recreation. Next boot may count. Module serializes worker/count/reset. Lost response never triggers automatic retry. Endpoint `0600 root:root`; kernel rechecks privilege; active descriptors pin module.

#### Maintainer lifecycle, upgrades, rollback

| Phase | Required behavior |
| --- | --- |
| `preinst install` | Validate architecture, running-kernel contract for live use, dependencies already present, conflicts, metadata support, backup space. Snapshot first baseline + journal before mutation. No APT. |
| `postinst configure` | Atomically publish files/link after backup; verify modes/hashes/targets. Never auto-load module during install/chroot/offline image mutation; first normal boot activation counts. Idempotent. |
| upgrade | Preserve first baseline, records, guard, pending-removal state. Do not unload/reload resident module. Reject control/state ABI incompatibility before replacement. New payload activates next boot; failed upgrade restores prior payload. |
| `prerm remove` | Durably set removal-pending, disable loader link, request module prepare-remove/quiesce, close package control use, attempt ordinary unload. No force unload/reboot/shutdown. Failure returns nonzero with activation disabled, backups/journal retained. |
| `postrm remove/purge` | Only after module/control endpoint absent: remove generated scoped records, restore every baseline path/record/metadata, remove created empty dirs/runtime artifacts/own ownership claim, verify, then remove backup/journal. Remove and purge both restore. |
| abort/retry | Resume/reverse durable journal idempotently. Never reactivate after removal request. Never erase last usable baseline. |

Busy unload remains pending until reboot occurs for unrelated approved operational reason. Package never requests reboot. Disabled loader + pending marker prevent later activation. Ordinary remove retry after natural reboot completes. Resident module, endpoint, pending marker, recreatable worker, restoration mismatch = uninstall not complete. Package restoration engine is generic offline lifecycle logic, not alternate monitor semantics.

#### Tests and acceptance

| Group | Required proof |
| --- | --- |
| Static/scope | Source and binaries contain no i.MX6 register address, `ioremap`, direct MMIO, reset-cause decode, kernel/U-Boot patch, boot artifact replacement, APT mutation, reason payload. `RELEASE.md` states exact scope/limits/notes. |
| OOT/ABI | Reproducible minimal module build from recorded inputs; module metadata/hash. Wrong arch/release/vermagic/symbol compatibility rejects safely. Live load only after exact target compatibility proof. Never `--force`, version bypass, unexported-symbol trick. |
| Guard/exact-once | One empty record after first accepted module initialization. Repeated loader call while loaded changes none. Clean unload/reload same boot changes none. Pending-before-create, created-before-sync, complete-update interruption resumes same name/no duplicate. New boot after verified guard reset adds exactly one. Boot/reset before init adds zero. |
| Storage/names | Equal/backward/invalid clock and forced 4-letter collisions never overwrite. Fault creation/inode sync/directory sync/guard update; one pending identity, bounded retry, boot continues. Empty record only; no reason write. Symlink/hard-link/path replacement attacks fail safe. |
| CLI/control | Count/reset/filter parsing, inclusive boundaries, malformed/partial/NUL/overlength/protocol mismatch, privilege, concurrent requests, process death/lost response. Bash has transport/help only; module absent => explicit nonzero, no filesystem fallback. |
| Package lifecycle | Fresh install/remove, purge, reinstall, v1→v2, failed upgrade, interrupted every journal phase, pre-existing directory/records, busy unload/deferred retry, overlap refusal, disjoint-package coexistence. Restore baseline and preserve unrelated paths. No reboot for uninstall. |
| Image restoration | Lock/journal evidence, before/after fingerprints + timestamps/hard links/ACLs/xattrs/capabilities/parent metadata, no package/runtime/ownership residue, source SHA-256 unchanged. Fault uninstall/restoration/unmount/source verification; quarantine. |
| Live device | After ABI proof and recovery readiness: install DEB without APT; controlled `insmod`/count; unload/reload/count unchanged; one approved ordinary reboot then count +1 after module init; uninstall/load suppression/restoration. Optional further approved boots test repetition only. Never claim physical reset coverage or cause. |

Live-device prerequisites: identify exact device/image/kernel; capture baseline + recovery path; verify adequate free space, SSH plus available console/reflash recovery status, module unload support, boot loader-link order, `/run` per-boot semantics; hash package; define abort. Start load/unload/reload. Reboot only for explicit boot-count acceptance, never uninstall. If connectivity/boot recovery fails, stop disruptive tests and preserve device for recovery. No watchdog/external-reset/brownout/panic tests required by revised semantics.

Acceptance:

- Package installation changes only owned surfaces; target APT state, kernel/U-Boot/boot artifacts, module indexes, monit, cron, watchdog, `/mnt/usb` unchanged.
- Each supported boot that reaches accepted module initialization contributes exactly one durable empty scoped record, subject to stated storage boundary. Same-boot supported unload/reload contributes zero extra. Pre-init boots/resets contribute zero.
- Count/reset/filter truth resides in module; Bash remains transport. No reasons/MMIO.
- `RELEASE.md` fully documents scope, exclusions, boundary, limits, install/remove/upgrade/test and recovery.
- Removing all produced packages (one DEB) restores every managed path/namespace to exact baseline. No success while module active/pending.

#### Lock-bounded image test and restoration proof

1. ACQUIRE SDLC image lock.
2. VERIFY no quarantine/conflicting mount.
3. RECORD source `var/image_8.26.0` SHA-256.
4. CREATE tooling-managed disposable copy.
5. MOUNT copy inside same lock.
6. CAPTURE baseline fingerprint + supplemental metadata/ownership.
7. INSTALL exact hashed DEB without network/APT mutation.
8. RUN package/static/offline tests; never load ARM module into host kernel.
9. UNINSTALL every produced package even after test failure.
10. VERIFY full managed-surface restoration, original records/metadata, no generated records, backup/journal/ownership/runtime residue, active module, endpoint, or pending removal.
11. UNMOUNT copy.
12. VERIFY source SHA-256 unchanged.
13. ***if*** uninstall, restoration, unmount, source verification, or cleanup fails ***then***
   1. QUARANTINE affected image identity.
   2. RETAIN phase journal/evidence.
   3. STOP; OS lock release never clears quarantine or authorizes reuse.
   4. REQUIRE tooling-reported recovery verification before reuse; never remove marker manually.
14. ***else***
   1. RECORD successful restoration evidence.
   2. RELEASE lock.

Preferred entry: `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-resets-monitor/package-test`. Custom flow only through one `./bin/lets sdlc lock-run` spanning mount/install/test/uninstall/restoration/unmount. Missing enforcement blocks mutation; never bypass. Dpkg DB/log changes inside disposable copy are declared verifier bookkeeping, not raw-byte restoration. No managed path may be excluded.

#### Deliverables and approval gate

After approval: minimal OOT source/build evidence; one reversible DEB + SHA-256; ownership/backup manifest; `RELEASE.md`; static, state, CLI, lifecycle, fault, locked-image evidence; controlled live-device procedure/results; exact limitations. Any inability to produce/load exact-compatible module becomes evidence-bearing blocker, not scope expansion.

Policy facts: six payload destinations, custom maintainer scripts, boot activation, kernel privilege/security, persistent storage/runtime namespace. Nontrivial. Commit DRAFT before display. Only deterministic `trivial-policy` may waive approval; otherwise wait for developer approval/amendment. Never self-approve.

### Solution plan — DRAFT revision 4

#### DRAFT revision 4 — bounded approximate-source compatibility probe

Round 1, `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. Supersedes approved DRAFT revision 3 after developer amendment checkpoint sequence 41. Earlier drafts, approvals, tasks, implementation failures stay audit history; none authorizes superseded reset-cause/MMIO/kernel/U-Boot work. Revision 4 adds one narrow live compatibility probe before production-module investigation. No production implementation, package install, boot activation, or reboot authorized by this DRAFT. All load-bearing decisions answered together through coordinator; latest explicit answer authorizes probe below despite unproven exact ABI. No unanswered developer question.

#### Sources, evidence, unchanged production boundary

Reviewed complete durable REQ: customer source, image analysis, planner Q&A, DRAFT revisions 1-3, approvals, task/implementation evidence, latest checkpoint, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/MONIT.md`.

Verified target: `root@192.168.68.56`, hostname `SCR-7CCC91`, ADLINK LEC-iMX6 Quad/Dual SMARC, Debian 8 Jessie ARMv7 SysV, running `3.10.105-imx6`; `/proc/version` build `developer@scr-dev-Eldad`, GCC `4.8.4 (Ubuntu/Linaro 4.8.4-2ubuntu1~14.04.1)`, `#5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018`; `/boot/config-3.10.105-imx6` and `/proc/config.gz` SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; GNU build-id `f7b0840244f238080194bd87ce76c704a67db004`; sample vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `; `CONFIG_MODVERSIONS=n`, `CONFIG_MODULE_SIG=n`, `CONFIG_VMSPLIT_2G_OPT=y`, `CONFIG_PAGE_OFFSET=0x6C000000`. `/run` verified tmpfs `0755 root:root`, 10 MiB. `/` ext4 `rw,noatime,errors=remount-ro,data=ordered`; `/var/log/scr` absent. `/boot/uImage-3.10.105-imx6` MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`; installed dpkg kernel `linux-image-3.10.53-lec-imx6` version `7`, therefore package metadata does not prove running ABI.

Exact inputs remain absent: no `/lib/modules/3.10.105-imx6/{build,source}`, matching complete generated tree, exact `Module.symvers`, source commit producing build-id, or exact compiler recipe. Public ADLINK refs expose no exact old tree. NXP `imx_3.10.53_1.1.0_ga_caf`, stable changes through `v3.10.105`, available ADLINK material, live config, generated-header reconstruction, exported-symbol evidence, and GCC-compatible build form approximate reconstruction only. Local `var/image_8.26.0` = 3,850,371,072 bytes; locked partition probe returned `whole /dev/loop2 3.6GB`; source SHA-256 stayed `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`. `./bin/lets sdlc test` previously: `25 passed in 1.34s`. Restoration fingerprint still must add timestamps, hard links, ACLs, xattrs, capabilities.

Production scope unchanged from revision 3: count exactly one observable boot reaching `scr_reset_monitor` module initialization; same-boot supported unload/reload adds zero; pre-initialization resets/boots uncounted; empty record, no reset cause/reason. No i.MX6 registers, MMIO, reset decoding, retained-counter work, kernel/U-Boot patch/replacement, physical-reset completeness claim, reset-loop detection/mitigation. Production remains minimal OOT LKM + Bash transport + one reversible DEB + `RELEASE.md`. Production live load still needs evidence stronger than probe success; probe success never proves exact ABI or authorizes production load/package completion.

#### Phase 0 — strictly bounded live compatibility probe

Purpose: learn whether reconstruction can load/unload one behavior-free module on exact target. Probe source contains only `module_init`, `module_exit`, fixed identifying `printk`/kernel logging, metadata, and return `0`. No VFS/filesystem access, MMIO, register access, worker/workqueue, thread, timer, delayed work, device/control endpoint, allocation retained past callback, notifier, hook, persistence, boot activation, counter/event semantics, parameter side effects, reboot/shutdown, APT mutation, package install, `depmod`, initramfs, `/lib/modules` write, force load, version bypass, or unexported-symbol trick.

Build probe from recorded reconstruction: NXP `imx_3.10.53_1.1.0_ga_caf` plus applicable stable history through `v3.10.105`, available ADLINK/config reconstruction, matching ARM architecture/config values and documented toolchain choice. Record all source refs/commits/patches/config inputs/tool versions/build commands and probe SHA-256. Label artifact `DIAGNOSTIC APPROXIMATE ABI — NOT PRODUCTION`.

Pre-live static gate:

1. VERIFY ELF class, endianness, machine = ARM, section sanity, relocations, and ARM EABI attributes against target/sample module.
2. VERIFY `modinfo` name/license/description and exact expected vermagic string `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `.
3. VERIFY undefined-symbol set contains only unavoidable module loader/logging primitives expected from minimal callbacks; compare every symbol with live exports. Reject unexpected symbol, CRC/version section, constructor, instrumentation, stack-protector, tracing, sanitizer, floating-point, or runtime-helper dependency.
4. VERIFY disassembly/source proves only fixed init/exit logs and return path. VERIFY absence of VFS, MMIO, worker/timer, persistence, control, boot, counter, force-load, APT, reboot code.
5. STOP before target mutation on any mismatch. Matching metadata permits probe only; never proves ABI.

Live gate and sequence:

1. IDENTIFY exact target/kernel/uptime and hash relevant baseline files.
2. CAPTURE full pre-probe `lsmod`, kernel taint value, bounded dmesg cursor/timestamp, free space, SSH state, probe destination absence/type/ownership, and current recovery readiness.
3. VERIFY console/reflash recovery status is recorded. Because console/reflash is problematic, require usable SSH plus named operator/recovery path; ambiguity stops probe.
4. COPY exact hashed probe transiently to one preflighted root-owned path outside boot/module activation directories. Refuse pre-existing path or ownership conflict. Never copy into `/lib/modules`, `/etc`, init paths, or package namespace.
5. RUN ordinary `insmod <transient-probe-path>` without any force flag.
6. INSPECT exit status, exact new dmesg lines, module presence/refcount, and kernel taint immediately. Success requires only expected fixed init log, module loaded once, refcount permitting ordinary removal, and no new warning/oops/BUG/panic/hung-task/lockdep/error/taint anomaly.
7. ***if*** `insmod` fails cleanly with normal compatibility error and no anomaly ***then*** capture exact error/dmesg, do not retry with altered checks, skip `rmmod`, remove transient file, verify baseline restoration, record probe FAIL evidence.
8. ***if*** module loaded cleanly ***then*** RUN ordinary `rmmod <probe-name>` once.
9. INSPECT exit status, exact new dmesg, module absence, reference state, taint, and expected fixed exit log. Never force removal.
10. REMOVE transient probe file only after confirmed module absence.
11. VERIFY destination restored to original absence, no module/activation/package/APT/file residue, no unexpected dmesg/taint change, and connectivity/recovery readiness unchanged.
12. ***if*** any warning, oops, BUG, panic, hang, unexpected taint, unload failure, lingering module/ref, unexplained log, connectivity loss, cleanup mismatch, or uncertain state occurs ***then*** STOP all device testing, preserve evidence, mark device quarantined for this requirement, and require explicit recovery verification before reuse. Do not reboot as probe cleanup.

Probe success means only: this exact minimal artifact completed init/exit on this exact running kernel once without observed anomaly. It is evidence to continue production-module build investigation. It is not exact source/ABI proof; not evidence that VFS, guard, worker, control, record, retry, count/reset/filter, packaging, boot, upgrade, persistence, or reset semantics are safe; not permission to reuse probe binary as production. Probe failure/anomaly blocks production live work. Clean compatibility rejection informs reconstruction; never triggers force/bypass.

Probe is explicit developer-authorized transient live diagnostic, not golden-image modification or deliverable. No raw image mutation. Capture transient baseline/restoration proof. All lasting image changes remain Debian-package-only.

#### Production deliverable and package ownership

After probe success plus production ABI/integration evidence, produce exactly one architecture-specific package: `scr-req-0001-goal-count-system-resets`, version above abandoned/unpublished artifact version. Determine `armhf`/`armel` from target dpkg evidence. No DKMS, target build, target `apt-get`, dependency upgrade, kernel/U-Boot package, initramfs/DT/boot-selector edit, `/lib/modules` index change, `depmod`, monit/cron/watchdog/USB-counter change.

Dpkg owns private payload `/usr/lib/scr-req-0001-goal-count-system-resets/payload`; maintainer scripts publish only after baseline backup.

| Managed surface | Ownership/restoration contract |
| --- | --- |
| `/usr/lib/scr-resets-monitor/scr_reset_monitor.ko` | Production OOT module, `0644 root:root`; separately verified build/runtime evidence; direct ordinary `insmod`; no force/bypass. |
| `/usr/sbin/scr-resets-monitor` | Bash, `0755 root:root`; validate shape, transport request, display result only; no truth/state/filesystem count/delete. |
| `/etc/init.d/scr-resets-monitor` | One-shot SysV loader, `0755 root:root`; check removal-pending + compatibility; load exact module. No event/guard decision, reboot, install, APT. |
| `/etc/rcS.d/S99scr-resets-monitor` | Exact symlink `../init.d/scr-resets-monitor`; prove root and guard storage ready. No broad `update-rc.d`. |
| `/usr/share/doc/scr-resets-monitor/RELEASE.md` | `0644 root:root`; scope/exclusions, observable-init boundary, pre-init/physical-reset limits, approximate-probe limits, same-boot rule, storage/clock/ABI limits, install/remove/upgrade/test/recovery. |
| `/usr/lib/scr-resets-monitor/package-test` | `0755 root:root`; non-destructive package checks; never load ARM module into unrelated host. |
| `/var/log/scr/reset-<epochMs>-<suffix>` | Module-created empty events; signed decimal UTC kernel-wall-clock milliseconds, suffix `[a-z]{4}`, `0600 root:root`, exclusive/no overwrite. |
| `/run/scr-resets-monitor/boot-guard`, `/dev/scr-resets-monitor` | Module-owned same-boot guard and root-only dynamic endpoint. Scripts touch runtime artifacts only after confirmed module absence during restoration. |
| `/var/lib/scr-req-0001-goal-count-system-resets/` | Root-only first-baseline backup, manifest, durable journal, removal-pending. Retain across upgrade/failure; delete after verified restoration only. |
| `/var/lib/scr-sdlc/owners` entry | Exact destinations/runtime namespace claim. Preserve registry/others; remove own claim after restoration only. |

Preflight: `lstat`, dpkg ownership, hashes, no-follow. Refuse unexpected code/loader/control/guard ownership plus exact/parent/child/namespace overlap. Preserve unrelated `/var/log/scr`. Snapshot original absence/content/type/symlink target/uid/gid/mode/timestamps/hard links/ACLs/xattrs/capabilities and parent metadata. Unsupported preservation blocks mutation. Existing matching records become baseline and restore even after `--reset`. No `Replaces`, conffile seizure, broad delete. One requirement package owns all managed surfaces; conflict with another requirement package stops install. Disjoint ownership may coexist only after registry proof and lifecycle tests.

#### Production module, event, guard, file, CLI contract

Successful supported module initialization accepts one event for current observable boot. Failure before acceptance creates none. Never read physical cause/MMIO. Module alone owns record, guard, selected name, retry, count/filter/reset, serialization, cancellation. Guard survives supported same-boot unload/reload and resets between boots. `/run` tmpfs evidence supports design; implementation must prove boot recreation/order. No safe kernel-visible boot identity = blocker, never shift truth to loader/Bash.

Guard bounded validated states: `pending:<filename>`, `complete:<filename>`, `cancelled`. Module atomically updates and syncs guard directory as supported. First init claims absent guard and selects one filename. Reload with `pending` resumes same identity; `complete`/`cancelled` creates none. Corrupt/unsafe/replaced guard fails init without event. Guard is deduplication, not persistent counter.

Durable event algorithm:

1. ACCEPT current observable-boot event during module initialization.
2. CLAIM module-owned same-boot guard.
3. SELECT `reset-<epochMs>-<suffix>` and persist `pending` before record create.
4. QUEUE process-context worker; never block boot.
5. RESOLVE `/var/log/scr` without unexpected symlink/alternate mount.
6. CREATE absent directory `0755 root:root`; synchronize parent before claiming persistence.
7. CREATE empty record exclusively, no-follow, `0600 root:root`.
8. ***if*** collision occurs ***then*** SELECT another suffix, durably update pending guard first, maximum 64 attempts/invocation.
9. RETAIN same identity across retries; never create second file after successful create.
10. SYNCHRONIZE empty inode, then containing directory.
11. ***if*** both syncs succeed ***then*** ATOMICALLY mark `complete` and synchronize guard directory.
12. ***if*** storage is read-only/full/EIO/unavailable ***then*** RETAIN one pending event/name, LOG rate-limited error, RETRY exponential 1-60 seconds, never block boot/reboot.

Crash/reset before inode + directory durability may lose event; boot ending before module init uncounted; device may violate flush guarantees. `RELEASE.md` states limits. Empty file counts; no reason write/payload.

Commands: `scr-resets-monitor --count [--since <timestamp>]`, `scr-resets-monitor --reset`, help. `--since`: exact `yyyy-mm-dd[ hh[:mm[:ss]]]` UTC; omitted fields zero; inclusive `eventTime >= sinceTime`; reject `--since last`, timezone, leap second, invalid Gregorian/range/overflow/trailing/conflicting input. Module parses semantics. Bash validates shape/bounds, transports literal versioned bounded request via `/dev/scr-resets-monitor`, prints response, maps exit; no enumeration/deletion/date math/retry/fallback/implicit load.

Scope: immediate non-symlink, single-link, regular empty files with complete matching name + parseable timestamp. Non-empty matches, symlinks, hard links, malformed names unsafe/non-counted/never deleted; operation returns error when complete truth impossible. Count success prints integer newline; absent directory = zero/no-op. Reset cancels pending event, writes `cancelled`, deletes only generated scoped records, syncs directory, preserves baseline archive/unrelated paths. Partial reset nonzero; cancelled prevents recreation until next boot. Module serializes worker/count/reset. Lost response never auto-retried. Endpoint `0600 root:root`; kernel rechecks privilege; open descriptors pin module.

#### Maintainer lifecycle, upgrade, rollback

| Phase | Required behavior |
| --- | --- |
| `preinst install` | Validate arch, running-kernel live contract, present dependencies, conflicts, metadata support, backup space. Snapshot first baseline + journal before mutation. No APT. |
| `postinst configure` | Atomically publish after backup; verify modes/hashes/targets. Never auto-load during install/chroot/offline mutation. First normal boot activation counts. Idempotent. |
| upgrade | Preserve first baseline, records, guard, pending-removal. Never unload/reload resident module. Reject control/state ABI incompatibility before replacement. New payload next boot; failed upgrade restores prior payload. |
| `prerm remove` | Durably set removal-pending; disable loader; request fallible `PREPARE_REMOVE`/quiesce before unload; close package control use; ordinary unload. No force/reboot/shutdown. Failure nonzero, activation disabled, backup/journal retained. |
| `postrm remove/purge` | Only after module/endpoint absent: remove generated scoped records; restore every baseline path/record/metadata; remove created empty dirs/runtime artifacts/own claim; verify; then remove backup/journal. Remove and purge both restore. |
| abort/retry | Resume/reverse journal idempotently. Never reactivate after removal request. Never erase last usable baseline. |

Busy unload stays pending until reboot occurs for unrelated approved reason. Package never requests reboot. Disabled loader + pending marker prevent later activation. Removal retry after natural reboot completes. Resident module, endpoint, pending marker, recreatable worker, restoration mismatch = uninstall incomplete. Generic package restoration logic is not alternate monitor semantics.

#### Tests and acceptance

| Group | Required proof |
| --- | --- |
| Probe | Recorded reconstruction; ELF/ARM attributes/vermagic/undefined-symbol/disassembly gate; baseline/recovery; transient copy; ordinary `insmod`; exact dmesg/taint/ref inspection; ordinary `rmmod`; cleanup/restoration. Anomaly quarantines device testing. Success only permits investigation. |
| Static/scope | Production source/binaries contain no i.MX6 address, `ioremap`, MMIO, cause decode, kernel/U-Boot patch, boot artifact replacement, APT mutation, reason payload. Probe contains init/exit/log only. `RELEASE.md` exact scope/limits. |
| OOT/ABI | Reproducible builds with recorded inputs, metadata/hash. Reject wrong arch/release/vermagic/symbol compatibility. Production live load needs production-specific compatibility evidence; approximate probe alone insufficient. Never force/bypass. |
| Guard/exact-once | First accepted init adds one empty record. Repeat loader while loaded and clean unload/reload same boot add none. Interrupt pending-before-create, created-before-sync, complete update: resume same name/no duplicate. Verified new boot adds one. Pre-init boot adds zero. |
| Storage/names | Equal/backward/invalid clock and forced suffix collisions never overwrite. Fault create/inode sync/dir sync/guard update; one pending identity, bounded retry, boot continues. Empty only. Symlink/hard-link/path attacks fail safe. |
| CLI/control | Count/reset/filter parsing; inclusive boundary; malformed/partial/NUL/overlength/protocol mismatch; privilege/concurrency/process death/lost response. Bash transport/help only; absent module explicit nonzero, no fallback. |
| Package lifecycle | Fresh install/remove/purge/reinstall, v1→v2, failed upgrade, every interrupted journal phase, pre-existing dirs/records, busy unload/deferred retry, overlap refusal, disjoint coexistence. Restore baseline; preserve unrelated paths; no uninstall reboot. |
| Image restoration | Lock/journal, before/after hashes + timestamps/hard links/ACLs/xattrs/capabilities/parent metadata; no package/runtime/ownership residue; source SHA-256 unchanged. Fault uninstall/restoration/unmount/source verification; quarantine. |
| Production live device | Only after probe + production evidence/recovery: install DEB without APT; controlled load/count; unload/reload unchanged; one separately approved ordinary reboot then +1 after init; uninstall/load suppression/restoration. Never claim physical reset cause/coverage. |

Acceptance:

- Probe obeys strict no-behavior contract, restores target baseline, causes no anomaly, and is represented only as limited evidence.
- Package changes only owned surfaces; target APT, kernel/U-Boot/boot artifacts, module indexes, monit, cron, watchdog, `/mnt/usb` unchanged.
- Each supported boot reaching accepted production-module init contributes exactly one durable empty scoped record, subject to storage boundary. Same-boot reload contributes zero. Pre-init resets/boots contribute zero.
- Module owns count/reset/filter truth; Bash only transports. No reasons/MMIO.
- `RELEASE.md` documents scope, exclusions, probe limitation, boundary, limits, install/remove/upgrade/test/recovery.
- Removing all produced packages (exactly one DEB) restores every managed path/namespace to exact baseline. No success while module active/pending. Probe transient path separately restores to baseline absence.

#### Lock-bounded image test and restoration proof

1. ACQUIRE SDLC image lock.
2. VERIFY no quarantine/conflicting mount.
3. RECORD `var/image_8.26.0` source SHA-256.
4. CREATE tooling-managed disposable copy.
5. MOUNT copy inside same lock.
6. CAPTURE baseline fingerprint plus timestamps, hard links, ACLs, xattrs, capabilities, ownership, parent metadata.
7. INSTALL exact hashed DEB without network/APT mutation.
8. RUN package/static/offline tests; never load ARM module into host kernel.
9. UNINSTALL every produced package after success or test failure.
10. VERIFY full managed-surface restoration: baseline records/metadata; no generated record, backup, journal, claim, runtime, active module, endpoint, pending removal.
11. UNMOUNT copy.
12. VERIFY source SHA-256 unchanged.
13. ***if*** uninstall, restoration, unmount, source verification, or cleanup fails ***then***
   1. QUARANTINE affected image identity.
   2. RETAIN journal/evidence.
   3. STOP; lock release never clears quarantine/reuse permission.
   4. REQUIRE tooling-reported recovery verification before reuse; never remove marker manually.
14. ***else***
   1. RECORD restoration evidence.
   2. RELEASE lock.

Preferred entry: `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-resets-monitor/package-test`. Custom flow only one `./bin/lets sdlc lock-run` spanning mount/install/test/uninstall/restoration/unmount. Missing enforcement blocks mutation. Dpkg DB/log differences in disposable copy are declared verifier bookkeeping; no managed path excluded.

#### Deliverables and approval gate

After approval: reconstructed-input manifest; minimal probe source/artifact/hash + static/live/restoration evidence; production OOT source/build evidence; one reversible DEB + SHA-256; ownership/backup manifest; `RELEASE.md`; state/CLI/lifecycle/fault/locked-image evidence; controlled production live procedure/results; exact limitations. Probe failure/anomaly or inability to establish safe production module becomes evidence-bearing blocker, never scope expansion.

Policy facts: six persistent payload destinations, custom maintainer scripts, boot activation, kernel privilege/security, persistent storage/runtime namespace, plus live approximate-ABI probe. Nontrivial. Commit DRAFT before display. Only deterministic `trivial-policy` may waive approval; otherwise wait for developer approval/amendment. Never self-approve.

### Solution plan — DRAFT revision 5

### Solution plan — DRAFT revision 5

#### DRAFT revision 5 — LETS-managed compatibility toolchain and one probe retry

Round 1, `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. Supersedes approved DRAFT revision 4 after developer amendment checkpoint sequence 50. Preserves revision 4 probe scope and revision 3 production scope exactly. Earlier drafts, approvals, tasks, failures, artifacts remain audit history; none authorizes removed reset-cause/MMIO/kernel/U-Boot work. Revision 5 adds LETS-native old-toolchain management, rebuilds identical init/exit/log-only probe, then permits one bounded ordinary `insmod`/`rmmod` retry only after all gates pass. No production implementation, package install, boot activation, force load, reboot, or target APT mutation authorized by DRAFT.

Reviewed complete durable REQ, image-analysis evidence, planner answers, revisions 1-4, approvals, implementation checkpoints, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/MONIT.md`. All load-bearing developer choices resolved together. New exact requirement: every compatibility-toolchain operation follows LETS philosophy. No unanswered question: authoritative redistributable Linaro release chosen below; implementation must retain license/notices and cryptographic evidence.

#### Evidence and unchanged boundaries

Target: `root@192.168.68.56`, `SCR-7CCC91`, ADLINK LEC-iMX6 Quad/Dual SMARC, Debian 8 Jessie ARMv7, SysV, live `3.10.105-imx6`. `/proc/version`: `gcc version 4.8.4 (Ubuntu/Linaro 4.8.4-2ubuntu1~14.04.1)`, build `developer@scr-dev-Eldad`, `#5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018`. Live config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; GNU build-id `f7b0840244f238080194bd87ce76c704a67db004`; vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `; `CONFIG_MODVERSIONS=n`, `CONFIG_MODULE_SIG=n`, `CONFIG_VMSPLIT_2G_OPT=y`, `CONFIG_PAGE_OFFSET=0x6C000000`. Exact vendor source/build tree, generated headers, `Module.symvers`, compiler recipe remain absent. NXP `imx_3.10.53_1.1.0_ga_caf` plus stable `v3.10.105`, live config, reconstructed headers remain approximate.

Revision 4 probe artifact SHA-256 `87e10d59c41a47b7af4e48524de728b0d917f223873cbbdfb83c53abbfff7f07`, built by host GCC 12/binutils 2.42, passed ARM attributes/vermagic/exported-symbol/source/disassembly gates, then ordinary `insmod` returned `1`: `insmod: ERROR: could not insert module /root/.scr-req-0001-approx-abi-probe.ko: Invalid module format`; sole dmesg delta: `[27840.175560] scr_approx_abi_probe: unknown relocation: 3`. Module never initialized. Taint stayed `4096`; no anomaly. `rmmod` correctly skipped. Transient file removed; config/uImage/SSH/recovery unchanged; no residue/quarantine/APT/reboot/package/image change. This clean rejection motivates era-compatible toolchain; never proves toolchain alone establishes exact ABI.

Production boundary stays revision 3: exactly one observable boot reaching `scr_reset_monitor` module initialization; supported same-boot unload/reload adds zero; pre-init resets/boots uncounted; empty record only, no reason. No i.MX6 register/MMIO/cause decode/retained counter, VFS use in probe, kernel/U-Boot patch/replacement, physical-reset completeness claim, reset-loop detection/mitigation. Production remains minimal OOT LKM, Bash transport frontend, `RELEASE.md`, one reversible DEB. Probe success permits production investigation only; production live load needs stronger production-specific evidence.

#### LETS compatibility-toolchain contract

All download, installation, verification, environment loading, version inspection, compiler, assembler, linker, archive, object copy/dump, ELF read, strip, and related compatibility-tool execution goes through top-level `./bin/lets`. Implementation/tests must contain no direct `gcc`, `ld`, `as`, `ar`, `nm`, `objcopy`, `objdump`, `readelf`, `strip`, prefixed equivalent, archive download, or hidden subprocess bypass outside wrapper internals. Kernel build receives wrapper-resolved `CROSS_COMPILE` only from managed environment. Mirror existing Python/Node UX, config loading, diagnostics, exit status, stdout/stderr, logging, help, offline behavior, and project-state conventions.

Managed distribution:

- ID: `linaro-arm-linux-gnueabihf-4.8-2014.04`.
- Archive: `gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz`, 51,126,392 bytes.
- Historical authoritative source: `https://releases.linaro.org/archive/14.04/components/toolchain/binaries/gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz`; current redirect is not archive content, so never accept it without hash.
- Availability fallback: `https://mirror-us-stl1.armbian.airframes.io/dl/_toolchain/gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz`, byte-identical required.
- SHA-256: `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`.
- Detached signature companion SHA-256: `659cce39a931a4a311e7913c742676f5cebb1ab23095f8636eeb1c8ec6e4e72c`, size 490, exact `.asc` sibling. SHA-256 is mandatory integrity authority; signature verification is additive only after pinned signer-key provenance exists, never substitute for hash.
- Expected compiler family: `arm-linux-gnueabihf-gcc (crosstool-NG linaro-1.13.1-4.8-2014.04 - Linaro GCC 4.8-2014.04) 4.8.3 20140401 (prerelease)`; binutils versions captured from managed binaries. Difference from live compiler 4.8.4 stays explicit approximate-compatibility limit.
- Licensing: redistributable Linaro binary release under bundled component licenses. Installer preserves complete archive license/copyright/notices; tests prove presence. Missing/ambiguous bundled notices, changed archive, or redistribution restriction blocks install/use; never silently rehost archive in Git/package.

State root: `${LETS_STATE_DIR}` when set by existing LETS config; otherwise project `.lets`. Final versioned tree lives below `${LETS_STATE_DIR}/toolchains/linaro-arm-linux-gnueabihf-4.8-2014.04/`; downloads/staging/locks/manifests live under same state root. Never write system compiler dirs, user home, `/usr/local`, target image, target device, APT state, or Git-tracked tree. One per-toolchain lock serializes init/use/repair.

`./bin/lets devenv init` includes idempotent compatibility-toolchain provisioning like Python/Node:

1. LOAD effective LETS config and `LETS_STATE_DIR`.
2. ACQUIRE toolchain lock.
3. VERIFY existing install manifest, archive SHA-256, required license notices, expected directory boundary, executable allowlist, version banners, and sentinel self-check.
4. ***if*** existing install verifies ***then***
   1. LOG concise skip message matching Python/Node conventions.
   2. RETURN success without network, mtime mutation, re-extraction, or version drift.
5. ***else if*** install is absent or partial ***then***
   1. REMOVE only tool-owned staging path after validating it lies beneath toolchain state root.
   2. RETAIN verified cached archive when present.
6. ***if*** verified archive is absent ***then***
   1. DOWNLOAD into unique same-filesystem partial file with redirects bounded to pinned HTTPS hosts, timeouts, and normal LETS logging.
   2. VERIFY byte length and SHA-256 before extraction.
   3. ***if*** offline or download fails ***then*** RETURN explicit nonzero error naming expected cache path/hash; leave verified current install untouched; leave no install marked ready.
7. EXTRACT into unique staging directory with path-traversal, absolute-path, link-escape, special-file, and ownership checks.
8. VERIFY expected single root, binaries, versions, licenses/notices, and executable self-checks through internal wrapper implementation.
9. WRITE manifest containing ID/version/source URLs/archive size/SHA-256/signature SHA-256/license inventory/file inventory/tool banners/install schema.
10. SYNCHRONIZE staged files and containing directory where supported.
11. RENAME staging atomically to final versioned directory.
12. WRITE ready sentinel atomically only after full verification.
13. RELEASE lock.

Interrupted download remains non-ready partial and is resumed only when downloader proves safe; otherwise replaced. Interrupted extraction never becomes final. Invalid cache quarantined within tool-owned state with evidence or deleted only after exact safe-path validation. Upgrade installs new versioned directory beside old, atomically switches configured selection, then retires only unreferenced tool-owned version after verification. Failure preserves previous verified selection. Offline repeat with verified install succeeds; offline first install or corrupted install+no verified cache fails deterministically with recovery command. Concurrent init/run never sees staging.

Top-level UX:

- `./bin/lets toolchain info [--json]`: load managed environment; print configured ID, root, triplet, archive SHA-256, compiler/binutils versions, verification state; no install mutation.
- `./bin/lets toolchain run <tool> [args...]`: allow exact managed tools `gcc`, `ld`, `as`, `ar`, `nm`, `objcopy`, `objdump`, `readelf`, `strip`, `ranlib`, `size`, `strings`; resolve to pinned triplet binaries; preserve every argument after tool verb exactly, stdout/stderr, signal, exit status, and caller working directory. Reject path separators, unknown tool, empty command, shell evaluation.
- Explicit aliases such as `./bin/lets toolchain gcc -- ...` may exist only when behavior equals `run gcc`; one documented canonical form required.
- `./bin/lets toolchain env -- <command> [args...]`: optional narrowly-scoped environment launcher for kernel `make`; exports absolute managed `PATH` prefix and `CROSS_COMPILE=arm-linux-gnueabihf-`, preserves caller working directory/arguments/exit semantics, never invokes shell string evaluation. Only needed because kernel build orchestrates multiple tools; tests prove all resolved binaries remain inside managed root.

Configuration pins ID, URLs, hashes, archive size, root component, triplet, required tools, expected banners. Invalid override fails closed. Logs redact credentials/proxy secrets and record source host/hash/version, cache/install/skip state, and executed managed tool name without rewriting arguments. Help/error wording and quiet/verbose/color behavior mirror `devenv` Python/Node patterns.

#### Phase 0 — identical probe rebuild and one bounded retry

Probe source and behavior stay revision 4: only `module_init`, `module_exit`, fixed identifying `printk`, metadata, return `0`. No VFS/filesystem, MMIO/register, workqueue/thread/timer, endpoint, allocation retained past callback, notifier/hook, persistence, boot activation, counter, parameters with side effects, reboot/shutdown, APT, package, `depmod`, initramfs, `/lib/modules` write, force/version bypass, or unexported-symbol trick.

Rebuild uses same recorded reconstructed kernel inputs, config/generated-header method, source file, module name, logs, metadata, flags except compiler/binutils paths now originate from managed Linaro toolchain. Record toolchain manifest/hash/banners, source refs/commits/patches/config, complete LETS commands, output hash, and reproducibility result. Label `DIAGNOSTIC APPROXIMATE ABI — NOT PRODUCTION`.

Pre-live gates:

1. RUN all compiler/link/binutils inspection through `./bin/lets toolchain ...`.
2. VERIFY ELF32 little-endian ARM EABI, machine ARM, section sanity, relocations, ARM attributes, exact vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 ` against deployed sample.
3. VERIFY every relocation is supported by target 3.10 ARM module loader; specifically prove prior relocation type `3` is absent or accepted from source-based loader table evidence. Unknown/unsupported relocation stops before copy.
4. VERIFY undefined set contains only unavoidable loader/log primitives and every symbol exists in live exports. Reject CRC/version section, constructor, instrumentation, stack protector, tracing, sanitizer, floating-point, or unexpected runtime helper.
5. VERIFY source/disassembly contains fixed init/exit logs and return only; static scan proves forbidden scope absent.
6. VERIFY two clean managed rebuilds yield identical artifact SHA-256 or record/resolve every nondeterministic field before live use.
7. STOP on mismatch. Metadata match permits one probe retry only.

Live sequence:

1. IDENTIFY exact target/kernel/uptime and verify target equals recorded device.
2. CAPTURE pre-probe `lsmod`, taint, bounded dmesg cursor/timestamp, free space, SSH, recovery readiness, transient destination absence/type/ownership, config/uImage hashes.
3. REQUIRE usable SSH plus named operator/recovery path; ambiguity stops.
4. COPY exact hashed artifact to same preflighted root-owned transient path outside activation/package dirs; mode `0600 root:root`; verify remote hash. Refuse pre-existing conflict.
5. RUN ordinary `insmod <transient-probe-path>` once, no force flag.
6. INSPECT exact exit/error, new dmesg, presence/refcount, taint, warnings/oops/BUG/panic/hang/lockdep/error.
7. ***if*** load fails cleanly with compatibility error and no anomaly ***then***
   1. RECORD exact evidence.
   2. SKIP `rmmod` because module absent.
   3. REMOVE transient file.
   4. VERIFY restoration.
   5. MARK probe FAIL; no third build/load retry under this plan.
8. ***if*** load succeeds cleanly ***then***
   1. RUN ordinary `rmmod <probe-name>` once.
   2. VERIFY expected exit log, module absence, reference state, taint, dmesg, connectivity.
9. REMOVE transient file only after confirmed module absence.
10. VERIFY baseline absence, no activation/package/APT/kernel/U-Boot/image/file residue, unchanged config/uImage, unchanged recovery readiness.
11. ***if*** warning, oops, BUG, panic, hang, unexpected taint, unload failure, lingering module/ref, unexplained log, connectivity loss, cleanup mismatch, or uncertainty occurs ***then***
   1. STOP all device testing.
   2. PRESERVE evidence.
   3. QUARANTINE device for requirement.
   4. REQUIRE explicit recovery verification before reuse.
   5. NEVER reboot as cleanup.

Success means only exact rebuilt diagnostic completed callbacks once on exact running kernel without observed anomaly. Failure/anomaly blocks production live work. No altered retry, force, bypass, reboot, VFS, persistence, or boot activation.

#### Production package: unchanged revision 3 scope

After probe success plus stronger production ABI/integration proof, produce exactly one architecture-specific package `scr-req-0001-goal-count-system-resets`, version above abandoned/unpublished artifacts. Determine `armhf`/`armel` from dpkg evidence. No DKMS, target build, target APT/dependency upgrade, kernel/U-Boot/initramfs/DT/boot-selector/module-index change, `depmod`, monit/cron/watchdog/USB-counter change.

Dpkg owns private payload `/usr/lib/scr-req-0001-goal-count-system-resets/payload`; maintainer scripts publish after first-baseline backup. Managed surfaces:

- `/usr/lib/scr-resets-monitor/scr_reset_monitor.ko`: production OOT module, `0644 root:root`, separately proven; ordinary direct load only.
- `/usr/sbin/scr-resets-monitor`: Bash `0755 root:root`; validates command shape, transports, displays only.
- `/etc/init.d/scr-resets-monitor`: one-shot SysV loader `0755 root:root`; checks removal-pending/compatibility; no truth, reboot, install, APT.
- `/etc/rcS.d/S99scr-resets-monitor`: exact `../init.d/scr-resets-monitor` symlink; no broad `update-rc.d`.
- `/usr/share/doc/scr-resets-monitor/RELEASE.md`: scope/exclusions, probe/toolchain limits, observable-init/pre-init/same-boot/storage/clock/ABI limits, lifecycle/recovery.
- `/usr/lib/scr-resets-monitor/package-test`: non-destructive checks; never loads ARM module into unrelated host.
- `/var/log/scr/reset-<epochMs>-<suffix>`: module-created empty events, signed decimal UTC milliseconds, `[a-z]{4}`, `0600 root:root`, exclusive.
- `/run/scr-resets-monitor/boot-guard`, `/dev/scr-resets-monitor`: module-owned guard/root-only endpoint.
- `/var/lib/scr-req-0001-goal-count-system-resets/`: root-only first-baseline backup, manifest, journal, removal-pending.
- `/var/lib/scr-sdlc/owners` own entry: exact persistent/runtime namespace claim.

Preflight uses `lstat`, dpkg ownership, hashes, no-follow; rejects exact/parent/child/namespace overlap and unexpected ownership. Snapshot absence/content/type/link target/uid/gid/mode/timestamps/hard links/ACLs/xattrs/capabilities/parent metadata. Unsupported preservation blocks mutation. Existing matching records are baseline and restored after `--reset`. No `Replaces`, conffile seizure, broad deletion. One requirement package owns surfaces; another requirement package conflict stops. Disjoint coexistence requires registry and lifecycle proof.

Production behavior unchanged: module alone owns event, guard, selected name, retry, count/filter/reset, serialization, cancellation. Guard states `pending:<filename>`, `complete:<filename>`, `cancelled`; corrupt/unsafe guard fails init. First accepted init persists pending name, worker creates directory safely, exclusively creates empty inode, syncs inode+directory, then atomically completes guard. Collision chooses new suffix only after durable guard update, maximum 64 attempts. Storage failure retains one identity, rate-limited exponential 1-60 second retry, never blocks boot/reboots. Crash before durable inode+directory may lose event; pre-init events uncounted.

CLI: `scr-resets-monitor --count [--since <timestamp>]`, `--reset`, help. Timestamp exact `yyyy-mm-dd[ hh[:mm[:ss]]]` UTC, omitted fields zero, inclusive `eventTime >= sinceTime`; reject `last`, timezone, leap second, invalid/overflow/trailing/conflicting input. Module parses truth. Bash transports bounded versioned request through `/dev/scr-resets-monitor`; no enumeration/delete/date math/retry/fallback/implicit load. Only immediate, non-symlink, single-link, regular empty, complete-name records count/delete. Unsafe matches cause nonzero incomplete-truth result. Reset cancels pending, durably marks `cancelled`, deletes only generated scope, syncs directory, preserves baseline/unrelated files. Lost response never auto-retried. Endpoint `0600 root:root`; kernel rechecks privilege; open descriptors pin module.

#### Maintainer lifecycle and rollback

- `preinst install`: validate arch/live contract/dependencies/conflicts/metadata/space; capture first baseline+journal before mutation; no APT.
- `postinst configure`: atomically publish and verify; never auto-load during install/chroot/offline image change; first normal boot activation counts; idempotent.
- Upgrade: retain first baseline/records/guard/removal state; never unload/reload resident module; reject incompatible control/state ABI; next boot selects new payload; failed upgrade restores prior payload.
- `prerm remove`: durably set removal-pending, disable loader, request fallible `PREPARE_REMOVE`, quiesce/close package control, ordinary unload. No force/reboot/shutdown. Failure nonzero; activation stays disabled; backups/journal stay.
- `postrm remove/purge`: only after module/endpoint absence, delete generated scoped records, restore every baseline path/record/metadata, remove created empty dirs/runtime artifacts/own claim, verify, then remove backup/journal. Remove and purge both restore.
- Abort/retry: resume/reverse durable journal idempotently; never reactivate after removal request; never erase last usable baseline.

Busy unload remains pending until unrelated natural reboot. Package never requests reboot. Disabled loader/pending marker prevent activation. Removal retry then completes. Active module/endpoint/pending marker/recreatable worker/restoration mismatch means uninstall incomplete.

#### Tests and acceptance

Toolchain tests: fresh online init; verified reinstall skip with unchanged mtimes/no network; offline verified repeat; offline absent/corrupt failure; hash/size/banner/license mismatch; HTTP redirect/host rejection; traversal/link/special-file archive; interrupted download/extract/rename/sentinel; partial recovery; concurrent init/run; state-root override/project default; upgrade rollback; cache reuse; invalid config. Test `info --json`, all allowlisted tools, unknown/path tool rejection, exact argv including spaces/leading dash, working directory, stdout/stderr/exit/signal, environment containment, kernel make tool resolution. Static scan rejects direct tool invocations outside wrapper internals and direct archive fetch in implementation/tests.

Probe tests: identical source contract; managed rebuild twice; ELF/ARM/vermagic/relocation/undefined/disassembly gates; baseline/recovery/transient-copy proof; one ordinary load attempt; ordinary unload only after success; exact dmesg/taint/ref inspection; restoration. Anomaly quarantines device testing. Success remains limited evidence.

Production tests: static forbidden-scope scan; reproducible OOT build and production-specific ABI proof; guard exact-once/reload/new-boot/pre-init; crash points pending/create/sync/complete; clock/collision/storage/path attacks; CLI parser/protocol/privilege/concurrency/process death/lost response; package fresh/remove/purge/reinstall/upgrade/failure/interrupted journal/baseline/busy unload/overlap/coexistence; controlled live count/unload/reload and separately approved ordinary reboot only after production gates. No physical reset-cause claim.

Acceptance:

- LETS owns every compatibility-toolchain operation. `devenv init` provides pinned, verified, idempotent, atomic, recoverable, offline-repeatable install under `${LETS_STATE_DIR}`/`.lets`; verified install skips like Python/Node.
- Top-level `./bin/lets toolchain` loads only managed toolchain, mirrors established UX/config/errors/logs, preserves argv/cwd/process results, and prevents direct-tool bypass.
- Rebuilt probe stays init/exit/log only. All relocation/static gates pass before exactly one ordinary retry. Target baseline fully restored; no anomaly/residue.
- Package changes only owned surfaces; target APT, boot/kernel/U-Boot/module indexes, monit, cron, watchdog, `/mnt/usb` unchanged.
- Each supported boot reaching production-module accepted init adds exactly one durable empty record; same-boot reload adds zero; pre-init resets/boots add zero. Module owns truth; Bash transports only.
- `RELEASE.md` records toolchain provenance/hash/version/license, approximate-ABI and probe limits, production scope/lifecycle/recovery.
- Removing all produced requirement packages, exactly one DEB, restores every managed path/namespace to exact baseline. No success while active/pending. Probe transient path separately restores to absence. Host LETS toolchain state is development infrastructure, not target-image mutation or DEB payload.

#### Lock-bounded package test and restoration proof

1. ACQUIRE SDLC image lock.
2. VERIFY no quarantine or conflicting mount.
3. RECORD source SHA-256 for `var/image_8.26.0`.
4. CREATE tooling-managed disposable copy.
5. MOUNT copy while same lock remains held.
6. CAPTURE baseline hashes, timestamps, hard links, ACLs, xattrs, capabilities, ownership, parent metadata.
7. INSTALL exact hashed DEB without network/APT mutation.
8. RUN static/offline/package tests; never load ARM module into host kernel.
9. UNINSTALL every produced package after pass or failure.
10. VERIFY baseline records/metadata and absence of generated records, backup, journal, claim, runtime, module, endpoint, pending removal.
11. UNMOUNT copy.
12. VERIFY source SHA-256 unchanged.
13. ***if*** uninstall, restoration, unmount, source verification, or cleanup fails ***then***
   1. QUARANTINE affected image identity.
   2. RETAIN journal and evidence.
   3. STOP reuse.
   4. REQUIRE tooling-reported recovery verification before unlock/reuse permission; never remove marker manually.
14. ***else***
   1. RECORD restoration proof.
   2. RELEASE lock.

Preferred entry: `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-resets-monitor/package-test`. Custom flow uses one `./bin/lets sdlc lock-run` spanning mount/install/test/uninstall/restoration/unmount. Missing enforcement blocks mutation. Dpkg bookkeeping differences only declared verifier exclusions; no requirement-managed path excluded.

#### Deliverables and approval gate

After approval: LETS toolchain config/installer/wrapper/tests/docs with manifest evidence; reconstructed-input manifest; rebuilt probe source/artifact/hash/static/live/restoration evidence; production OOT source/build evidence; one reversible DEB + SHA-256; ownership/backup manifest; `RELEASE.md`; CLI/lifecycle/fault/locked-image proof; controlled live results; exact limits. Probe/toolchain failure or inability to prove production compatibility becomes evidence-bearing blocker, never scope expansion.

Policy facts: development tooling additions, network download, six persistent target payload destinations, custom maintainer scripts, boot activation, kernel privilege/security, persistent storage/runtime namespace, live approximate-ABI retry. Nontrivial. Commit DRAFT before display. Only deterministic `trivial-policy` may waive approval; otherwise wait for developer approval/amendment. Never self-approve.

### Solution plan — DRAFT revision 6

#### DRAFT revision 6 — hermetic i386 runtime for pinned Linaro toolchain

Round 1, `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. Supersedes approved DRAFT revision 5 after verified runtime blocker at checkpoint sequence 57. Preserves revision 3 production scope, revision 4 diagnostic-probe scope, revision 5 LETS ownership/philosophy, all earlier evidence, exclusions, package lifecycle, tests, restoration rules. Revision 6 changes only host-side compatibility-toolchain runtime design, then permits same one bounded probe rebuild/retry. No production implementation, image/package install, boot activation, force load, reboot, target APT, host APT, `sudo`, container-global install authorized by DRAFT.

Reviewed complete durable REQ through sequence 57: customer source, requirements analysis, image analysis, planner answers, revisions 1-5, approvals, implementation evidence/checkpoints, project guides, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/MONIT.md`. Load-bearing choices already answered. Runtime source/version safely resolved from authoritative Ubuntu archive metadata and exact bytes; no developer question outstanding.

#### Verified blocker and source traceability

- Pinned archive unchanged: `gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz`; size `51126392`; SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`; expected GCC banner remains Linaro GCC `4.8.3 20140401 (prerelease)`.
- Verified archive host executables are ELF32 i386 and request `/lib/ld-linux.so.2`. Current x86_64 host lacks compatible i386 loader/runtime; direct compiler launch fails. Partial staged extraction is non-ready evidence, not healthy install.
- Archive-wide ELF inspection finds runtime names needed by allowed compiler/binutils paths: `libc.so.6`, `libm.so.6`, `libpthread.so.0`, `libdl.so.2`, `libstdc++.so.6`, `libgcc_s.so.1`, `libz.so.1`; `/lib/ld-linux.so.2` interpreter. `gdb` additionally needs `libncurses.so.5`, but `gdb` stays outside revision-5 allowlist and is never provisioned/invoked. Implementation must rescan every allowlisted executable and recursively verify closure; unexpected `DT_NEEDED`, interpreter, ABI, symbol-version failure blocks readiness.
- Choose Ubuntu Trusty Updates i386 runtime because live kernel compiler provenance names Ubuntu/Linaro Trusty-era GCC and packages remain on authoritative `https://archive.ubuntu.com/ubuntu/`. No reliance on host multiarch state.

Pinned package manifest, exact HTTPS URL = `https://archive.ubuntu.com/ubuntu/<Filename>`:

- `libc6` `2.19-0ubuntu6.15`, i386; `pool/main/e/eglibc/libc6_2.19-0ubuntu6.15_i386.deb`; size `3999084`; SHA-256 `8f429c90bb3da42bc34f5a92fc02f808e6097468799a11a12d6ffa771062ecf5`; supplies loader, libc, libm, libpthread, libdl.
- `libgcc1` `1:4.9.3-0ubuntu4`, i386; `pool/main/g/gccgo-4.9/libgcc1_4.9.3-0ubuntu4_i386.deb`; size `48008`; SHA-256 `e8701c791da3fea219f17305ae80838f58d9158706a4858b563004b93131d3ce`; supplies `libgcc_s.so.1`.
- `libstdc++6` `4.8.4-2ubuntu1~14.04.4`, i386; `pool/main/g/gcc-4.8/libstdc++6_4.8.4-2ubuntu1~14.04.4_i386.deb`; size `269602`; SHA-256 `62b417f55b2ef83aa25424338d8d8e4956d712ce22a2b4882441f425459ee500`; supplies `libstdc++.so.6`.
- `zlib1g` `1:1.2.8.dfsg-1ubuntu1.1`, i386; `pool/main/z/zlib/zlib1g_1.2.8.dfsg-1ubuntu1.1_i386.deb`; size `50564`; SHA-256 `5ef3e7a194da9055b5247a1f6e8df60b537e6a0af8e8c4f3081386deb7eb71bc`; supplies `libz.so.1`.
- Metadata-closure packages retained for provenance/license/dependency proof though no maintainer script runs: `gcc-4.8-base` `4.8.4-2ubuntu1~14.04.4`, i386, `pool/main/g/gcc-4.8/gcc-4.8-base_4.8.4-2ubuntu1~14.04.4_i386.deb`, size `16636`, SHA-256 `69ea774b9202940e3bc50158d0743a5a9e9a5cbeb44ab48090b8f01833529c0b`; `gcc-4.9-base` `4.9.3-0ubuntu4`, i386, `pool/main/g/gccgo-4.9/gcc-4.9-base_4.9.3-0ubuntu4_i386.deb`, size `15090`, SHA-256 `0c20ea350db1ed077f2b275bd82d4ba382ff074309ad981aaa6690cba1a25a83`; `multiarch-support` `2.19-0ubuntu6.15`, i386, `pool/main/e/eglibc/multiarch-support_2.19-0ubuntu6.15_i386.deb`, size `4484`, SHA-256 `e123a324ac939c09f764a1a6e9f87ed0e91c3b37002c363b95a21d5ff88f0763`.
- Ubuntu `Packages.gz` declares exact versions/dependencies: `libc6 -> libgcc1`; `libgcc1 -> gcc-4.9-base, libc6`, pre-depends `multiarch-support`; `libstdc++6 -> gcc-4.8-base, libc6, libgcc1`, pre-depends `multiarch-support`; `zlib1g -> libc6`, pre-depends `multiarch-support`; `multiarch-support -> libc6`. Streamed package sizes/SHA-256 matched metadata. Preserve each package control/copyright/license plus Linaro bundled notices in manifest. Missing license, changed metadata/bytes, or redistribution uncertainty blocks use.

#### LETS-managed runtime design

Revision-5 state/config/UX remain. Runtime lives only below `${LETS_STATE_DIR}/toolchains/runtime/ubuntu-trusty-i386-2019/`; default state root project `.lets`. Toolchain tree remains `${LETS_STATE_DIR}/toolchains/linaro-arm-linux-gnueabihf-4.8-2014.04/`. Cache, unique staging, locks, manifests, ready sentinels stay below same root. Never write `/lib`, `/usr`, `/usr/local`, user home, dpkg database, APT database, container image/global filesystem, target image/device, Git tree.

`./bin/lets devenv init` owns runtime + toolchain transaction:

1. LOAD effective LETS config/state root; reject unsafe root/override.
2. ACQUIRE one ordered toolchain/runtime lock covering verify, cache, extract, publish; concurrent `init`/`toolchain` waits or reads only prior verified generation.
3. VERIFY current generation: exact archive/package manifests, sizes/hashes, license inventory, file inventory, no escaped paths/links/special files, ELF class/machine/interpreter/recursive `DT_NEEDED`, expected GNU symbol versions, tool banners, sentinel schema, executable smoke test.
4. ***if*** healthy generation exists ***then*** SKIP network and mutation; preserve mtimes; return success. Offline healthy reuse mandatory.
5. ***if*** partial/corrupt generation exists ***then*** preserve healthy current generation; clean only validated tool-owned staging; never follow links; use verified cache or fail offline with expected paths/hashes.
6. DOWNLOAD missing artifacts to unique same-filesystem partials only from pinned HTTPS hosts/paths with bounded redirects/timeouts; verify size/SHA-256 before acceptance. No host/target APT.
7. INSPECT each `.deb` as ar container; accept expected `debian-binary`, one control archive, one data archive only. Reject duplicate members, absolute/`..` paths, traversal, hard/symlink escape, devices/FIFOs/sockets, unexpected ownership/mode, decompression bombs, unsupported compression. Never call `dpkg`, `dpkg-deb`, package maintainer scripts, triggers, ldconfig.
8. EXTRACT allowlisted runtime files and required license/control evidence into unique runtime staging root. Preserve internal relative symlinks only after canonical containment proof. Package file collisions must be byte-identical and declared; otherwise fail.
9. EXTRACT Linaro archive into separate staging root under same safety rules from revision 5.
10. VERIFY every allowlisted i386 executable against runtime root. Invoke exact managed loader `${runtime}/lib/ld-linux.so.2 --library-path <ordered-runtime-lib-dirs> <absolute-managed-tool> <args...>`; never depend on host `/lib/ld-linux.so.2`, host `LD_LIBRARY_PATH`, host i386 libraries, shell evaluation, or binary patching.
11. WRITE generation manifest: every URL/version/arch/size/hash/license/control dependency, extracted-file hash/mode/link, loader/library paths, ELF/`DT_NEEDED`/symbol-version closure, tool banners, schema.
12. FSYNC staged files/directories where supported; atomically publish immutable versioned runtime and toolchain trees, then atomic ready/current sentinel. Failure keeps previous healthy generation selected; incomplete generation never ready.
13. RELEASE lock.

`./bin/lets toolchain info [--json]`, `run <tool>`, optional exact aliases, and narrowly scoped `env -- <command>` remain revision 5. Wrapper always selects verified generation and invokes managed i386 loader/library path. Preserve exact argv including spaces/leading dash, cwd, stdin/stdout/stderr, exit code, signal. Reject path separators, unknown tool, missing/corrupt generation, unverified runtime, host fallback. Kernel make gets wrapper-controlled tool commands; every compiler/binutils execution remains owned by `./bin/lets toolchain`. Environment removes/overrides loader-influencing vars (`LD_PRELOAD`, `LD_LIBRARY_PATH`, audit/profile/tunables) and compiler search overrides unless explicit validated contract permits them. Never expose runtime as general command shell.

Upgrade installs new immutable generation beside current; validates before atomic switch; failure leaves prior current. Cache may retain only exact verified artifacts. Repair never destroys sole healthy generation. Runtime/toolchain state is development infrastructure, not target-image mutation or DEB payload.

#### Tests and gates added by revision 6

Keep every revision-5 toolchain, probe, production, package, failure, rollback, and acceptance test. Add:

- Architecture: assert host x86_64, all managed host tools ELF32 i386, interpreter exactly `/lib/ld-linux.so.2`, loader itself ELF32 i386, ARM outputs unchanged. Reject mixed/unexpected ELF.
- Closure: enumerate every allowlisted executable plus compiler subprogram reached by smoke/build; recursively resolve all `DT_NEEDED` only inside managed runtime/toolchain; assert no host library resolution using loader diagnostics/map evidence. Test missing/wrong library, incompatible GNU symbol version, stray host i386 install, hostile `LD_*` vars.
- Packages: verify all seven exact URLs/versions/arches/sizes/SHA-256/control dependencies/licenses; corrupt/truncated/redirect/wrong-arch/wrong-version/duplicate member/traversal/link escape/special file/collision/decompression-limit cases fail closed. Assert no dpkg/APT database or host path changes and no maintainer script execution.
- Lifecycle: fresh online init; healthy skip without network/mtime change; healthy offline reuse; offline absent/corrupt explicit failure; interrupted downloads and each extraction/publish/sentinel crash point; atomic repair; previous-generation rollback; concurrent init/init and init/run; alternate `LETS_STATE_DIR`; cache reuse.
- Forwarding: every allowlisted tool, compiler subprogram, `info --json`, unknown/path rejection, exact argv/cwd/stdin/stdout/stderr/exit/signal, make integration. Static scan rejects direct compatibility-tool calls/downloads and host loader/library fallback outside wrapper internals.

Only after all runtime/toolchain gates pass: rebuild identical revision-4 init/exit/fixed-log-only probe twice through managed wrapper. Preserve exact reconstructed source/config contract. Run ELF/ARM attributes/vermagic/undefined-symbol/disassembly and relocation gates. Compare relocations with target 3.10 ARM loader source; prior relocation `3` must be absent or proven supported. Unsupported/unknown relocation stops offline: no copy, load, altered retry, force, VFS, MMIO, persistence, activation, package, boot, reboot.

If gates pass, permit exactly one ordinary live retry from revision 5: target identity/baseline/recovery preflight; copy exact hashed transient probe; remote hash/mode; one ordinary `insmod`; inspect rc/dmesg/module/refcount/taint/connectivity; ordinary `rmmod` only after success; remove transient only after confirmed absence; verify config/uImage/baseline/no residue. Clean compatibility rejection = probe FAIL and no further retry. Warning/oops/BUG/panic/hang/unload failure/lingering module/unexplained log/connectivity or restoration uncertainty = preserve evidence, quarantine device, stop; never reboot for cleanup. Success proves diagnostic callbacks only, not production ABI or reset correctness.

#### Production package, ownership, rollback, acceptance

Revision-3 production scope remains exact. After probe success and stronger production-specific ABI/integration proof, build exactly one reversible architecture-specific Debian package `scr-req-0001-goal-count-system-resets`. Package owns private payload plus published module, Bash transport frontend, SysV loader/link, `RELEASE.md`, package test, exact event/runtime/state/ownership namespaces previously specified. No DKMS, target build/APT, `depmod`, initramfs, kernel/U-Boot/DT/boot-selector, monit/cron/watchdog/USB-counter change. Another requirement package with exact/parent/child namespace overlap conflicts and blocks install; disjoint package coexistence requires registry/lifecycle proof. No `Replaces` or conffile seizure.

`preinst` validates architecture/kernel contract, conflicts, metadata, space; captures first baseline and durable journal before mutation. `postinst` atomically publishes/verifies; never loads during install/chroot/offline image mutation. Upgrade retains first baseline, records/guard/removal state; never reloads resident module; rejects incompatible ABI; failed upgrade restores prior payload. `prerm` durably marks removal pending, disables loader, requests fallible `PREPARE_REMOVE`, quiesces control, ordinary unload only; no force/reboot/shutdown. Busy unload returns nonzero, keeps backup/journal, prevents reactivation until unrelated natural reboot and later retry. `postrm remove/purge` proceeds only after module/endpoint absence; deletes generated scoped records, restores every baseline path/content/type/link/uid/gid/mode/timestamps/hard links/ACLs/xattrs/capabilities/parent metadata, removes created empty dirs/runtime/state/claim, verifies, then removes backup/journal. Abort/retry is durable/idempotent; never erase last baseline. Active/pending/residue/mismatch means uninstall incomplete.

Production behavior/acceptance stays revision 3/5: module alone owns accepted-init event, guard, name, exclusive empty-file create, inode+directory sync, retry, count/filter/reset, serialization/cancel. Bash validates/transports/displays only. Exactly one supported boot reaching accepted module init creates one durable empty `/var/log/scr/reset-<epochMs>-<four-lowercase-letters>`; same-boot reload zero; pre-init resets/boots uncounted. No reset reason/MMIO claim. Storage failure retries without blocking/reboot. CLI grammar/filter/deletion safety unchanged. `RELEASE.md` records runtime/toolchain provenance and hashes, approximate-ABI/probe limits, production limits/lifecycle/recovery.

#### Lock-bounded package proof

1. ACQUIRE SDLC image lock.
2. VERIFY no quarantine/conflicting mount; RECORD source `var/image_8.26.0` SHA-256.
3. CREATE tooling-managed disposable copy; MOUNT while same lock stays held.
4. CAPTURE full baseline: hashes, contents/types/links, ownership/modes/timestamps, hard links, ACLs, xattrs, capabilities, parent metadata, package bookkeeping.
5. INSTALL exact hashed DEB without network/host or target APT mutation.
6. TEST static/offline/package lifecycle; never load ARM module into host kernel.
7. UNINSTALL every produced package after pass or failure.
8. VERIFY exact baseline restoration and absence of generated records, backup, journal, claim, runtime, module, endpoint, pending removal.
9. UNMOUNT copy; VERIFY source SHA-256 unchanged.
10. ***if*** uninstall, restoration, unmount, source verification, or cleanup fails ***then*** QUARANTINE affected image identity; RETAIN journal/evidence; STOP reuse; REQUIRE tooling-reported recovery before unlock/reuse; never remove marker manually.
11. ***else*** RECORD restoration proof; RELEASE lock.

Preferred command remains `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-resets-monitor/package-test`. Custom flow uses one `./bin/lets sdlc lock-run` spanning mount, install, test, uninstall, restoration verification, unmount. Missing enforcement blocks mutation. Removing all produced requirement packages—exactly one DEB—must restore original image managed surfaces exactly. Host `.lets` runtime/toolchain state excluded only because development infrastructure never enters image/package.

#### Deliverables and approval gate

After approval: LETS runtime/toolchain config, safe `.deb` extractor, installer/wrapper/tests/docs/manifests/licenses; reconstructed-kernel input manifest; reproducible rebuilt probe/source/artifact/hash/static/live/restoration evidence; production OOT source/build proof; one reversible DEB + SHA-256; ownership/baseline manifest; `RELEASE.md`; CLI/lifecycle/fault/locked-image proof; controlled live results; exact limits. Runtime/toolchain/probe/production compatibility failure becomes evidence-bearing blocker, never scope expansion.

Nontrivial: seven network artifacts, executable legacy runtime, LETS code/config/tests, live approximate-ABI retry, six persistent target payload destinations, maintainer scripts, boot activation, kernel privilege, persistent storage/runtime namespace. Commit DRAFT before display. Never self-approve. Only deterministic `trivial-policy` may waive; otherwise await developer approval/amendment.

### Solution plan — DRAFT revision 7

#### DRAFT revision 7 — developer-waived approximate production ABI

Round 1, `REQ-0001-GOAL-COUNT-SYSTEM-RESETS`. Supersedes approved DRAFT revision 6 after checkpoint sequence 66. Preserves revision 3 production semantics/package, revision 4 probe safety, revisions 5-6 LETS toolchain/runtime, all evidence, exclusions, rollback, image locking, quarantine. Change: developer confirms legacy vendor artifacts unavailable and explicitly accepts validated approximate NXP source + LETS-managed GCC for production implementation and real-HW testing. This waiver removes exact-vendor-artifact gate only. It never waives static checks, ordinary-load-only rule, restoration, package reversibility, device safety, or truthful limits.

#### Sources, decisions, evidence

Reviewed complete durable REQ through sequence 66: customer source, requirements/image analysis, planner answers, revisions 1-6, approvals, implementation attempts/checkpoints, probe evidence, event log, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, `docs/MONIT.md`.

Load-bearing decisions resolved:

- Counter means exactly one observable boot reaching accepted `scr_reset_monitor` module initialization. Same-boot supported unload/reload adds zero. Reset/boot ending before module init adds zero. No physical-reset completeness claim.
- Event = durable empty `/var/log/scr/reset-<epochMs>-<four-lowercase-letters>`. File count = counter. No reset reason/payload.
- No i.MX6 register/SRC access, direct MMIO, reset decoding, retained-counter work, kernel/U-Boot source patching/replacement, boot-selector/DT/initramfs change. `RELEASE.md` states kernel/U-Boot patching out of scope because EOL/lack of supported artifacts.
- Module owns event, same-boot guard, filename, retry, count/filter/reset, serialization/cancellation. Bash frontend validates/transports/displays only. No monit/daemon/cron/USB counter truth.
- Developer states exact vendor source/generated headers/`Module.symvers`/recipe unavailable and authorizes production with approximate artifacts plus real-HW tests. No further provenance question remains.
- Developer request to avoid repeated approvals is recorded. Pipeline approval policy still applies: DRAFT must commit; tooling alone may auto-approve. Otherwise one approval of exact revision/hash remains mandatory; implementation then auto-progresses until hardware gate, safety failure, or tooling blocker.

Verified target `192.168.68.55`: hostname `SCR-7CCC91`; ADLINK LEC-iMX6; Debian 8 Jessie ARMv7 SysV; root; kernel `3.10.105-imx6 #5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018`; live compiler provenance GCC `4.8.4 (Ubuntu/Linaro 4.8.4-2ubuntu1~14.04.1)`; config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; build-id `f7b0840244f238080194bd87ce76c704a67db004`; vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `; `CONFIG_MODVERSIONS=n`; `CONFIG_MODULE_SIG=n`; `CONFIG_VMSPLIT_2G_OPT=y`; `PAGE_OFFSET=0x6C000000`; uImage MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`; `/run` tmpfs verified. Credentials remain ignored `admin/hw.credentials`, mode `0600`; never log secret.

Approximate inputs: NXP source commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`, reconstructed release `3.10.105-imx6`, exact live config above, managed Linaro GCC `4.8.3 20140401 (prerelease)` and binutils `2.24.0.20140311 Linaro 2014.03`. Toolchain archive SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`. Seven pinned Trusty i386 runtime packages remain revision-6 exact manifest. All compiler/binutils operations use `./bin/lets devenv init` and `./bin/lets toolchain`; direct tools, host/target APT, `sudo`, global install forbidden.

Diagnostic probe evidence: two byte-identical builds SHA-256 `1377d6cae2339aedf00647a8e78b7aefed54c206a40927fb241cae0e12245334`; ELF/ARM attributes/vermagic/symbol/disassembly/relocation gates passed; relocation `3` absent; ordinary `insmod` rc `0`; ordinary `rmmod` rc `0`; exact expected init/exit logs; taint unchanged `4096`; config/uImage/module-table baselines restored; no residue/anomaly. This proves minimal callbacks load/unload on exact running kernel. It does not prove arbitrary structures/prototypes/VFS behavior. Developer waiver accepts that residual production ABI risk only after production-specific static and bounded live gates below.

#### Implementation scope and production gates

Implement minimal OOT module against existing kernel; never patch kernel tree. Prefer smallest 3.10-compatible exported interface set. No unexported-symbol tricks, KALLSYMS address lookup, `--force`, vermagic editing, version bypass, binary patch, target build, target APT, kernel/U-Boot modification.

Before package/live production use:

1. INITIALIZE pinned runtime/toolchain with `./bin/lets devenv init`.
2. VERIFY healthy generation, manifests, license evidence, recursive ELF closure, managed loader, banners, offline/idempotent reuse.
3. RECONSTRUCT kernel tree from pinned NXP commit, exact live config, recorded stable/config adjustments.
4. BUILD production module twice using only `./bin/lets toolchain` routes.
5. REQUIRE byte-identical production artifacts or resolve every nondeterministic field.
6. VERIFY ELF32 little-endian ARM EABI, ARMv7 attributes, exact vermagic, section sanity, no CRC/signature assumption, supported relocations, expected undefined exports, no instrumentation/stack-protector/sanitizer/floating-point/unexpected helper.
7. COMPARE every used kernel type/prototype/layout with chosen source and isolate code from broad internal structures.
8. SCAN source/binary for forbidden MMIO/reset-reason/kernel/U-Boot/force/APT behavior.
9. RUN host-side model/fault/protocol tests for all logic that can be separated from kernel glue.
10. ***if*** unresolved symbol, unsupported relocation, unexplained layout dependency, static anomaly, nondeterminism, or forbidden behavior exists ***then***
    1. STOP before target copy/load/package activation.
    2. RECORD exact blocker.

Production module contract:

1. ACCEPT one current-boot event only after supported module init reaches stable initialized state.
2. CLAIM `/run/scr-resets-monitor/boot-guard` using no-follow bounded state `pending:<filename>`, `complete:<filename>`, or `cancelled`.
3. ***if*** guard is `complete` ***or*** `cancelled` ***then***
   1. CREATE no event.
4. ***else if*** guard is valid `pending` ***then***
   1. RESUME same filename/event identity.
5. ***else if*** guard is absent ***then***
   1. SELECT `reset-<epochMs>-<suffix>`.
   2. PERSIST `pending:<filename>` atomically.
   3. SYNCHRONIZE guard directory.
6. ***else***
   1. FAIL initialization safely without event.
7. QUEUE process-context worker without blocking boot.
8. RESOLVE `/var/log/scr` without symlink/alternate-object acceptance.
9. CREATE absent directory `0755 root:root` and synchronize parent.
10. CREATE empty record exclusively/no-follow as `0600 root:root`.
11. ***if*** name collides ***then***
    1. SELECT new four-letter suffix, maximum 64 attempts per invocation.
    2. PERSIST new pending name before create.
12. RETAIN same inode/name after successful create across retries.
13. SYNCHRONIZE empty inode.
14. SYNCHRONIZE containing directory.
15. MARK guard `complete` atomically.
16. SYNCHRONIZE guard directory.
17. ***if*** storage returns read-only/full/EIO/unavailable ***then***
    1. RETAIN one pending identity.
    2. LOG rate-limited error.
    3. RETRY exponentially from 1 to 60 seconds.
    4. NEVER block boot or reboot.

Crash before inode + directory durability may lose event. Storage may violate flush guarantees. Invalid/backward wall clock remains filename time; suffix prevents overwrite. No reason write exists.

CLI remains `/usr/sbin/scr-resets-monitor --count [--since <timestamp>]`, `--reset`, help. `--since` exact `yyyy-mm-dd[ hh[:mm[:ss]]]` UTC; missing time components zero; inclusive filename-time comparison. Reject `last`, timezone suffix, leap second, invalid Gregorian/range/overflow/trailing/conflicting input. Module parses/owns truth over root-only `/dev/scr-resets-monitor`; Bash sends bounded versioned literal request and displays result only. Count/delete scope: immediate, non-symlink, single-link, regular empty files with complete valid name. Unsafe matching entries make truthful operation fail nonzero and remain untouched. Reset cancels pending, durably marks guard `cancelled`, deletes generated scoped records, synchronizes directory, preserves baseline/unrelated data. No auto-retry after lost response.

#### Reversible Debian package

Produce exactly one architecture-specific package `scr-req-0001-goal-count-system-resets`, version above every unpublished artifact. Confirm dpkg architecture from image/target. Dpkg owns private `/usr/lib/scr-req-0001-goal-count-system-resets/payload`; scripts publish after baseline capture. No DKMS, `depmod`, `/lib/modules` index update, target dependency upgrade, or hidden helper package.

Managed ownership:

| Surface | Contract |
| --- | --- |
| `/usr/lib/scr-resets-monitor/scr_reset_monitor.ko` | Production OOT module, `0644 root:root`; exact artifact hash/vermagic/provenance. |
| `/usr/sbin/scr-resets-monitor` | Bash transport/help only, `0755 root:root`. |
| `/etc/init.d/scr-resets-monitor` | One-shot SysV loader, `0755 root:root`; checks pending removal/compatibility; ordinary `insmod` only; no truth/reboot/APT. |
| `/etc/rcS.d/S99scr-resets-monitor` | Exact symlink `../init.d/scr-resets-monitor`; no broad `update-rc.d`. |
| `/usr/share/doc/scr-resets-monitor/RELEASE.md` | `0644 root:root`; scope, exclusions, EOL/artifact waiver, approximate ABI/probe limits, observable-init/pre-init/same-boot/storage/clock limits, lifecycle/test/recovery. |
| `/usr/lib/scr-resets-monitor/package-test` | `0755 root:root`; non-destructive; never loads ARM module into host kernel. |
| `/var/log/scr/reset-<epochMs>-<suffix>` | Module-created empty events; baseline matching records preserved/restored. |
| `/run/scr-resets-monitor/boot-guard`, `/dev/scr-resets-monitor` | Module runtime namespace; removal only after confirmed module absence. |
| `/var/lib/scr-req-0001-goal-count-system-resets/` | Root-only first baseline, manifest, journal, removal-pending; retained until verified restoration. |
| `/var/lib/scr-sdlc/owners` entry | Exact destinations + dynamic namespace claim; preserve registry/other claims. |

Preflight uses `lstat`, no-follow, hashes, dpkg ownership, metadata support, capacity. Refuse unexpected code/loader/control/guard ownership and exact/parent/child/namespace conflict with another requirement package. Disjoint coexistence requires registry + lifecycle proof. No `Replaces` or conffile seizure. Snapshot original absence/content/type/link target/uid/gid/mode/timestamps/hard links/ACLs/xattrs/capabilities/parent metadata. Unsupported restoration capability blocks mutation. Preserve unrelated `/var/log/scr` entries and all original matching records.

Maintainer lifecycle:

| Phase | Required behavior |
| --- | --- |
| `preinst install` | Validate architecture/kernel contract/dependencies/conflicts/metadata/space; durably capture first baseline + journal before mutation. No network/APT. |
| `postinst configure` | Atomically publish/verify payload and loader link. Never load in install/chroot/offline image mutation. Idempotent. |
| upgrade | Retain first baseline, records, guard, removal state. Never reload resident module. Reject incompatible control/state ABI before replacement. Failed upgrade restores prior payload. New payload activates next boot. |
| `prerm remove` | Durably mark removal pending; disable loader; issue fallible `PREPARE_REMOVE`; quiesce worker/control; ordinary unload only. No force/reboot/shutdown. Failure returns nonzero; keep backup/journal and activation disabled. |
| `postrm remove/purge` | Proceed only after module/endpoint absence. Delete generated scoped records; restore all baseline paths/records/metadata; remove created empty dirs/runtime/own claim; verify; then remove backup/journal. Both remove/purge restore. |
| abort/retry | Resume or reverse journal idempotently. Never reactivate after removal request. Never erase last baseline. |

Busy unload stays pending until unrelated natural reboot; package never triggers reboot. Pending marker + disabled loader suppress activation. Ordinary removal retry completes after natural reboot. Active module/endpoint/pending worker/residue/mismatch means uninstall incomplete.

#### Automated, image, and real-HW tests

Automated gates:

- LETS runtime/toolchain revision-6 suites: package/hash/license/extractor safety, ELF closure, hostile environment, fresh/skip/offline/repair/concurrency/alternate state root, forwarding, make integration, direct-tool bypass scan.
- Production build reproducibility/static ABI gates above.
- Guard exact-once model: first init one, repeated loader zero, unload/reload same boot zero, new boot one, pre-init boot zero; interruption at every guard/create/inode-sync/dir-sync/complete boundary resumes one identity.
- Storage/name/path faults: collisions, equal/backward clock, read-only/full/EIO, symlink/hard-link/replacement, bounded retry and rate limit.
- Protocol/CLI: parsing/bounds/NUL/fragment/unsupported version/privilege/concurrency/process death/lost response; absent module explicit failure/no fallback.
- Package lifecycle: install/remove/purge/reinstall, upgrade/failed upgrade, interruption every journal phase, pre-existing directory/records, busy unload/deferred retry, overlap refusal/disjoint coexistence, preserved unrelated paths.

Lock-bounded disposable-image proof:

1. ACQUIRE SDLC image lock.
2. VERIFY no quarantine or conflicting mount.
3. RECORD source `var/image_8.26.0` SHA-256.
4. CREATE tooling-managed disposable copy.
5. MOUNT copy while same lock remains held.
6. CAPTURE full baseline: hashes, types, links, ownership, modes, timestamps, hard links, ACLs, xattrs, capabilities, parent metadata, package bookkeeping.
7. INSTALL exact hashed DEB without network/host/target APT mutation.
8. RUN static/offline/package lifecycle tests; never load ARM module into host kernel.
9. UNINSTALL every produced package after pass or failure.
10. VERIFY exact managed-surface restoration and absence of generated records, backup, journal, claim, runtime, module, endpoint, pending removal.
11. UNMOUNT disposable copy.
12. VERIFY source SHA-256 unchanged.
13. ***if*** uninstall, restoration, unmount, source verification, or cleanup fails ***then***
    1. QUARANTINE affected image identity.
    2. RETAIN journal/evidence.
    3. STOP reuse.
    4. REQUIRE tooling-reported recovery before unlock/reuse.
    5. NEVER remove quarantine marker manually.
14. ***else***
    1. RECORD restoration proof.
    2. RELEASE lock.

Preferred command: `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <artifact> --test-command /usr/lib/scr-resets-monitor/package-test`. Custom flow must use one `./bin/lets sdlc lock-run` spanning mount/install/test/uninstall/restoration/unmount. Missing enforcement blocks mutation. Dpkg bookkeeping exclusions may not hide any managed path.

Controlled target sequence uses `192.168.68.55` only after automated/image PASS and exact DEB hash:

1. VERIFY endpoint identity, kernel/config/uImage hashes, architecture, free space, uptime, connectivity, console/reflash/operator recovery, no quarantine, no namespace conflict.
2. CAPTURE baseline package/APT state, protected-path hashes, `/proc/modules`, taint, bounded dmesg cursor, `/var/log/scr`, runtime/state paths, loader paths.
3. COPY exact hashed DEB transiently; verify remote hash/mode.
4. INSTALL DEB using existing package manager without network or dependency upgrade; confirm install does not load module/create event.
5. RUN ordinary one-time loader/`insmod`; inspect rc, exact dmesg delta, module/refcount, endpoint/guard, taint, connectivity.
6. VERIFY first accepted init produces exactly one durable empty event and `--count` returns baseline plus one.
7. RUN repeated loader; verify zero new events.
8. RUN ordinary remove/load same boot; verify zero new events, expected logs, unchanged taint.
9. EXERCISE count/filter/reset semantics and bounded safe faults without corrupting baseline records; preserve evidence.
10. RESTORE test-generated records/state before reboot acceptance.
11. VERIFY safe recovery remains available.
12. PERFORM one controlled ordinary reboot because boot-count acceptance requires it and developer authorized real-HW completion.
13. RECONNECT with bounded timeout.
14. VERIFY exact identity/kernel/config/uImage, loader activation, expected single new event, count delta `+1`, no duplicate, no warning/oops/BUG/panic/hang/new unexplained taint.
15. DISABLE loader and mark removal pending through package removal path.
16. UNLOAD ordinarily without reboot.
17. UNINSTALL package.
18. VERIFY all managed paths/records/metadata restore to target baseline; transient DEB removed; no module/endpoint/worker/runtime/state/claim/loader residue; package/APT/protected paths restored; connectivity healthy.
19. ***if*** ordinary unload is busy ***then***
    1. KEEP removal pending and loader disabled.
    2. RETAIN backups/evidence.
    3. DO NOT reboot for cleanup.
    4. STOP with explicit incomplete-uninstall state.
20. ***if*** warning, oops, BUG, panic, hang, unexpected taint, connectivity loss, boot failure, unload failure, cleanup mismatch, or restoration uncertainty occurs ***then***
    1. STOP further tests.
    2. PRESERVE evidence.
    3. QUARANTINE device for requirement.
    4. REQUIRE explicit recovery verification before reuse.
    5. NEVER force module operations or patch kernel/U-Boot.

Credentials stay secret: use ignored credential file/askpass, redact commands/logs, never persist password in REQ/evidence/package/Git.

#### Acceptance and deliverables

Acceptance requires:

- One reproducible production `.ko` built solely through LETS-managed toolchain from recorded approximate inputs; static production gates PASS.
- One reversible DEB + SHA-256, ownership/baseline manifest, source/license/toolchain provenance, `RELEASE.md`, package tests.
- Package/image lock proof shows install/test/uninstall/restoration and unchanged source image; cleanup failure quarantines.
- On exact HW, ordinary production load/unload/reload and one controlled reboot pass with no new anomaly/taint; exactly one event first accepted init, zero same-boot reload, exactly one next boot init.
- CLI/module authority, storage retry, filename safety, lifecycle, overlap, upgrade, rollback tests pass.
- Target cleanup restores baseline exactly; no target APT changes, force, kernel/U-Boot/boot artifact/module-index/monit/cron/watchdog/USB-counter changes.
- `RELEASE.md` clearly says counter counts observable module initializations, not physical reset reasons; pre-init events uncounted; no MMIO; kernel/U-Boot patching out of scope due EOL/lack support; approximate source/toolchain accepted by developer; probe/production evidence cannot guarantee unknown vendor ABI internals; storage/clock limits remain.

Deliver exact commits/artifact hashes/test commands/results/dmesg deltas/taint/baseline-restoration evidence. Independent validation verifies complete requirement, approved plan, DEB reversibility, image restoration, and HW evidence before merge. Hardware success still needs developer follow-up to close requirement.

#### Approval gate

Nontrivial: kernel-privileged production module, boot activation, persistent storage/runtime namespace, custom maintainer scripts, approximate ABI waiver, controlled target reboot. DRAFT must commit before display. Run deterministic `trivial-policy`. Only explicit tooling PASS may waive approval; otherwise await one developer approval of revision 7/hash. Never self-approve. After approval, auto-progress through implementation, validation, integration, and hardware procedure until explicit hardware gate, safety failure, or tooling blocker.

### Solution plan — DRAFT revision 8

#### DRAFT revision 8 — activation and exact-once repair after independent validation

Supersedes approved DRAFT revision 7 after independent validation FAIL sequence 76 and replan checkpoint sequence 77. Preserves revision 7 scope, developer acceptance of approximate NXP source/LETS-managed toolchain, real-HW authorization, observable-module-init semantics, package safety, exclusions, evidence, and truthful limits. Changes only defects required by validation. No load-bearing developer question remains: required behavior, risk acceptance, package removal semantics, one additional bounded reboot, and target `192.168.68.55` already authorized.

#### Binding sources and failure evidence

Reviewed complete REQ through sequence 77, customer source, requirements/image analysis, planner answers, revisions 1–7, approvals, implementation evidence, revision 7 independent validation, event log, `AGENTS.md`, `docs/SDLC-DEVELOPER-GUIDE.md`, `docs/DEVELOPER-GUIDE.md`, and `docs/MONIT.md`.

Revision 7 binding: plan SHA-256 `3b397ef90c63e6037302d7ca4eab7dd47773017ba26c538e24be60e811300ad6`; rejected implementation commit `7610f9249db5640e7db82fbed20d23ff1f3b6c6d`; module SHA-256 `091a20b51f95b1f56110aa89ce1830b0cfb59bec8a9bfa1e17065732e26ce15d`; rejected DEB SHA-256 `119b0c760bf76e8e765f92877f232f99170648c0562fc75d7092edb351be1f50`. Never merge/release those rejected artifacts.

Preserved PASS evidence: two reproducible production builds; ELF32 ARM EABI5; exact vermagic `3.10.105-imx6 SMP preempt mod_unload ARMv7 p2v8 `; relocation type `3` absent; target-exported undefined symbols; manual ordinary load/unload/reload; one first-init event; zero repeated-loader/same-boot reload events; CLI count/filter/reset; taint unchanged `4096`; locked disposable-image restoration; source image SHA-256 `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`; target cleanup; RELEASE limits; `26 passed in 1.44s`.

Mandatory FAIL set:

1. Automatic boot created zero module, guard, device, or event although `/etc/rcS.d/S10scr-resets-monitor` existed. PID 1/runlevel evidence says SysV runlevel `2`; exact Debian 8 target sequencing/cause remains unproved.
2. Record parent-directory sync failure can leave created inode, then retry new random name and duplicate one boot event.
3. Guard file/directory sync errors are logged but returned as success, permitting false durable-claim success and later duplicate count.
4. Remove/purge can retain generated records when module is absent because `prerm` skips `--reset` and `postrm` silently fails to remove nonempty `/var/log/scr`.
5. ARM `.ko` package incorrectly declares `Architecture: all`; required architecture is `armhf`.
6. `./bin/lets sdlc acceptance REQ-0001-GOAL-COUNT-SYSTEM-RESETS` fails `task manifest approved-plan hash does not match current approval`.

#### Scope and immutable exclusions

Counter remains exactly one durable empty record per observable boot whose `scr_reset_monitor` module initialization reaches accepted state. Same-boot repeated loader or unload/reload creates zero. Reset/boot ending before module init creates zero. No reset reason, physical-reset completeness claim, i.MX6 SRC/register/MMIO access, retained-counter work, kernel/U-Boot patch/replacement, boot-selector/DT/initramfs change, force load, vermagic editing, target build/APT/network dependency, monit/cron/watchdog/USB-counter truth, or reboot-loop behavior.

Legacy vendor source/generated headers/`Module.symvers`/recipe remain unavailable. Developer accepts approximate NXP commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`, exact live config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`, managed Linaro GCC `4.8.3 20140401 (prerelease)`, binutils `2.24.0.20140311 Linaro 2014.03`, and residual ABI risk. All compiler/binutils operations use `./bin/lets devenv init` and `./bin/lets toolchain`; direct compatibility tools forbidden. Pinned runtime/toolchain stays under `.lets`; healthy install skipped.

#### Implementation defect repairs

Record identity becomes immutable before any record create. Guard `pending:<filename>` is sole pending identity. Worker retries same validated pathname and same extant inode after successful exclusive creation; never generates another suffix unless exclusive create proves selected name collided before ownership. Persist in-memory state distinguishing `name-selected`, `inode-created`, `inode-synced`, `parent-synced`, `guard-complete`. Parent sync retry reopens/verifies exact owned record and syncs same directory; it never calls random-name selection. Unexpected type, link count, owner, size, name, replacement, disappearance after owned creation, or identity mismatch fails closed, logs rate-limited error, preserves evidence, and never creates second record.

Guard claim must propagate every write, inode sync, rename, and parent-directory sync error. Module initialization/worker may continue boot and retry storage, but count/complete status never reports success until exact guard state and directory durability succeed. Retry retains immutable pending filename/state. Existing valid same-boot `pending` resumes same event. Existing `complete` or `cancelled` creates none. Malformed/unsafe guard fails initialization safely. A file-sync or parent-sync failure never becomes success, never discards pending state, and never selects another event.

Required exact-once algorithm:

1. READ validated boot guard into `guardState`
2. ***if*** `guardState` is `complete` ***or*** `cancelled` ***then***
   1. RETURN without event creation
3. ***else if*** `guardState` is valid `pending:<filename>` ***then***
   1. SET `eventName` to persisted filename
4. ***else if*** guard is absent ***then***
   1. SELECT one collision-free candidate into `eventName`
   2. WRITE `pending:<eventName>` atomically
   3. SYNCHRONIZE guard inode
   4. SYNCHRONIZE guard parent directory
   5. ***if*** any operation fails ***then***
      1. RETURN nonzero pending result
      2. RETRY same guard/event identity later
5. ***else***
   1. RETURN nonzero unsafe-state result
6. CREATE `eventName` exclusively only when absent
7. ***if*** exclusive create reports collision before ownership ***then***
   1. SELECT another candidate
   2. PERSIST new pending identity durably before create
8. ***else if*** record exists from earlier owned attempt ***then***
   1. VERIFY exact pathname, regular empty file, uid/gid/mode/link count, and owned pending identity
   2. REUSE same record
9. SYNCHRONIZE exact record inode
10. SYNCHRONIZE record parent directory
11. WRITE `complete:<eventName>` atomically
12. SYNCHRONIZE guard inode
13. SYNCHRONIZE guard parent directory
14. REPORT one completed event only after all prior steps pass

Add deterministic injected failures at each guard-write/inode-sync/parent-sync, record-create/inode-sync/parent-sync, and completion boundary. Every retry sequence must yield zero or one valid event, never two; success requires exactly one. Include replacement, symlink, hard-link, truncation, deletion, collision, read-only, ENOSPC, EIO, interruption, worker cancellation, and unload races.

#### Boot activation investigation and repair

Do not guess link/runlevel. Before package redesign or reboot, inspect target `192.168.68.55` read-only: `runlevel`; `/etc/inittab`; `/etc/init.d/rc`, `/etc/init.d/rcS`; `/etc/rcS.d`, `/etc/rc2.d`, all existing `scr-resets-monitor` links; init-script headers; `update-rc.d` behavior/version/config; boot logs, syslog/dmesg timestamps, and prior package evidence; presence/behavior of systemd compatibility tools without assuming systemd PID 1; dependency order for root rw, `/var`, `/run`, `/dev`, and local filesystems. Record exact cause why rcS link did not run or did not load. Credentials use ignored `admin/hw.credentials`/askpass; secret never enters commands, evidence, REQ, package, or Git.

Select activation only from evidence. Expected candidate is SysV runlevel 2 link because target runs runlevel `2`, but result is not predetermined. Use dependency-correct init headers and deterministic package-owned registration. `update-rc.d` may be used only if exact target behavior, created links, policy, offline-image behavior, baseline capture, and full reversal are proven. Otherwise publish exact required link set through package lifecycle. Support Debian 8 SysV target; systemd compatibility must neither mask failure nor add separate service truth. Loader checks kernel/config/vermagic, pending removal, existing module, and ordinary `insmod`; returns nonzero and logs exact failure. No load during package install, chroot, or disposable-host test.

Activation tests: exact init action manually with captured rc/log; simulated runlevel invocation; offline root/chroot-safe no-load behavior; start twice; stop/remove; failed load; pending removal; missing/wrong kernel; link registration/upgrade/removal restoration; boot log proof. Automatic acceptance requires module, `/run/scr-resets-monitor/boot-guard`, `/dev/scr-resets-monitor`, and exactly one new record after one newly authorized bounded ordinary reboot. Manual load never substitutes.

#### Single reversible Debian package

Produce exactly one canonical package `scr-req-0001-goal-count-system-resets`, new version above rejected `1.0.1`, Debian `Architecture: armhf`, canonical `_armhf.deb` filename. Remove/ignore stale `_all.deb` and alternate artifacts from candidate selection; validation binds one DEB path/SHA-256 only. Package remains architecture-specific even when scripts are shell.

Dpkg owns private payload below `/usr/lib/scr-req-0001-goal-count-system-resets/payload`; maintainer scripts publish managed destinations only after durable baseline capture. No DKMS, `depmod`, module-index edit, `Replaces`, conffile seizure, helper package, target dependency upgrade, or network.

Managed surfaces:

| Surface | Ownership/restoration contract |
| --- | --- |
| `/usr/lib/scr-resets-monitor/scr_reset_monitor.ko` | ARM production module, `0644 root:root`; exact hash/vermagic/provenance. |
| `/usr/sbin/scr-resets-monitor` | Bash argument/transport/display only, `0755 root:root`; no filesystem count/delete fallback. |
| `/etc/init.d/scr-resets-monitor` | SysV one-shot loader, `0755 root:root`; exact evidence-derived headers/actions. |
| Evidence-derived `/etc/rc*.d/*scr-resets-monitor` links | Package-managed exact link names/targets; capture and restore every baseline link. Never retain failed rcS design by default. |
| `/usr/share/doc/scr-resets-monitor/RELEASE.md` | Scope, exclusions, EOL, approximate ABI, observable-init, activation, storage/clock limits, recovery. |
| `/usr/lib/scr-resets-monitor/package-test` | Non-destructive lifecycle/static test; never loads ARM module into host kernel. |
| `/var/log/scr/reset-<epochMs>-<four-lowercase-letters>` | Generated empty events; package removal deletes package-generated scoped records and restores every baseline matching record exactly. |
| `/run/scr-resets-monitor/boot-guard`, `/dev/scr-resets-monitor` | Runtime namespace; absent after unload/removal. |
| `/var/lib/scr-req-0001-goal-count-system-resets/` | Root-only immutable first baseline, record inventory/copies, journal, ownership manifest, removal-pending; retained until verified restoration. |
| `/var/lib/scr-sdlc/owners` entry | Exact destinations plus dynamic namespace claim; preserve other owners/claims. |

Preflight uses `lstat`, no-follow, hashes, dpkg ownership, types, link targets, uid/gid/mode/timestamps, hard links, ACLs, xattrs, capabilities, parent metadata, capacity, and exact record inventory. Refuse unsupported metadata restoration, unsafe objects, code/runtime/namespace ownership, and exact/parent/child overlap with another requirement package. Permit disjoint coexistence only with registry and lifecycle proof.

Maintainer lifecycle:

1. `preinst install`: VERIFY `armhf`, kernel contract, dependencies, namespace, metadata support, free space; SAVE first baseline and journal durably before mutation; perform no network/APT/load.
2. `postinst configure`: PUBLISH payload and evidence-derived activation atomically; VERIFY exact destinations/links; NEVER load module; RETAIN first baseline across reinstall/upgrade.
3. `upgrade`: PRESERVE first baseline, baseline records, guard, removal state; NEVER reload resident module; REJECT incompatible state/control ABI; RESTORE prior payload on failed upgrade; activate new payload only next boot.
4. `prerm remove`: MARK removal pending durably; DISABLE every activation path; ***if*** module loaded ***then*** issue fallible `PREPARE_REMOVE`, quiesce, reset scoped generated records under module authority, ordinary unload; NEVER force/reboot.
5. `prerm remove`: ***if*** module absent ***then*** run package-lifecycle cleanup, not frontend fallback: compare exact baseline inventory/manifest, delete only non-baseline immediate regular empty single-link valid-name records owned by package contract, reject unsafe/mutated candidates, and propagate any failure nonzero.
6. `postrm remove/purge`: REQUIRE module/endpoint/worker absence; RESTORE baseline records and all managed paths/links/metadata; REMOVE only package-created empty dirs/runtime/claim; VERIFY exact baseline; REMOVE backup/journal only after verification. `remove` and `purge` share full restoration semantics.
7. `abort/retry`: RESUME or reverse journal idempotently; NEVER reactivate after removal request; NEVER erase last baseline.

Absent-module cleanup is deterministic package lifecycle, not a second counter authority. Module remains sole live count/filter/reset authority. Baseline matching records are never deleted permanently. Unsafe record or restoration error stops removal; never silently `rmdir`. Busy unload retains pending marker, disabled activation, backups, and journal until unrelated natural reboot; package never initiates cleanup reboot.

#### Regression, build, package, and acceptance gates

Regression tests required for all six validation findings:

- Activation: target sequence evidence; chosen registration; manual init action; simulated boot/runlevel; exactly one real boot activation; no rcS/rc2/systemd duplicate activation.
- Record retry: injected parent-sync failure after inode durability, repeated retries, immutable name/inode, exactly one record.
- Guard sync: injected file-sync and parent-sync errors return nonzero, retain pending state, retry same identity, no false completed count.
- Uninstall: loaded and absent module; failed activation; records present; pre-existing matching/unrelated/unsafe entries; install/remove/purge/reinstall/upgrade/failed-upgrade/abort; exact restoration or hard failure.
- Architecture: control field `armhf`, filename `_armhf.deb`, ARM `.ko`, target dpkg architecture match, one canonical artifact.
- Task binding: regenerate task manifest only through `./bin/lets sdlc task-plan ...` after revision 8 approval; bind exact revision-8 SHA; run bounded tasks/coverage; require `./bin/lets sdlc acceptance REQ-0001-GOAL-COUNT-SYSTEM-RESETS` PASS before implementation commit/validation. Never edit ledger/artifacts by hand.

Build module twice from clean state with `./bin/lets devenv init` and only `./bin/lets toolchain` compiler/binutils routes. Require byte-identical `.ko`; ELF32 little-endian ARM EABI5; ARMv7 attributes; exact vermagic; relocation type `3` absent; supported relocations; expected target-exported undefined symbols; no CRC/signature assumption, sanitizer, stack protector, FP, MMIO/reset code, force behavior, or unexplained layout dependency. Rebuild canonical DEB twice; require identical package hashes or explain/resolve nondeterminism before use.

Run unit/model/fault/protocol tests plus `./bin/lets sdlc test`. Test CLI parsing, privilege, fragments, NUL/length/version, concurrency, lost response, absent module, no userspace truth fallback. Test collision/backward clock/storage/path faults, cancellation, rate limits, overlap refusal, disjoint coexistence, journals, upgrades, and every maintainer interruption.

#### Continuous-lock disposable-image proof

1. ACQUIRE SDLC image lock for `var/image_8.26.0`
2. VERIFY no quarantine or conflicting mount
3. RECORD source SHA-256
4. CREATE tooling-managed disposable copy
5. MOUNT copy while same lock remains held
6. CAPTURE full filesystem/package/managed-surface baseline
7. INSTALL exact canonical `armhf` DEB without network/APT mutation
8. TEST install, offline activation registration, upgrade, failed upgrade, module-absent records, remove, purge, abort, reinstall, overlap, and package test without loading ARM module into host kernel
9. UNINSTALL every produced package after pass or failure
10. VERIFY exact path, link, record, metadata, package bookkeeping, runtime, claim, backup, journal, pending-removal restoration
11. UNMOUNT disposable copy
12. VERIFY source SHA-256 unchanged
13. ***if*** cleanup, restoration, unmount, or source verification fails ***then***
    1. QUARANTINE image through tooling
    2. RETAIN journal/evidence
    3. STOP reuse
    4. REQUIRE tooling-reported recovery before unlock/reuse
14. ***else***
    1. RECORD restoration proof
    2. RELEASE lock

Preferred command: `./bin/lets sdlc test-package REQ-0001-GOAL-COUNT-SYSTEM-RESETS --image var/image_8.26.0 --deb <canonical-armhf-deb> --test-command /usr/lib/scr-resets-monitor/package-test`. Custom path must use one `./bin/lets sdlc lock-run` spanning mount/install/test/uninstall/restoration/unmount. Requirement-managed paths cannot be verification exclusions.

#### Real-HW sequence and bounded reboot

Use `192.168.68.55` only after automated/static/reproducible/image/task acceptance PASS. One new bounded ordinary reboot is authorized solely to retest corrected activation.

1. VERIFY exact hostname/board/Debian/kernel/config/uImage/architecture, uptime, free space, connectivity, recovery availability, no quarantine, no namespace conflict
2. INSPECT and RECORD exact SysV/default-runlevel/rcS/rc2/systemd-compat activation facts before selecting registration
3. CAPTURE package/APT state, protected hashes, activation links, records, `/proc/modules`, taint, bounded dmesg/log cursor, runtime/state/loader baseline
4. COPY exact canonical DEB transiently
5. VERIFY remote SHA-256 and mode
6. INSTALL without network/dependency upgrade
7. VERIFY install creates no event and loads no module
8. RUN chosen init action manually once
9. VERIFY ordinary load, expected logs, module/device/guard, taint unchanged, exactly one event, count baseline plus one
10. RUN repeated start
11. VERIFY zero new events
12. RUN ordinary unload/reload same boot
13. VERIFY zero new events and unchanged taint
14. EXERCISE CLI and bounded sync-fault hooks without corrupting baseline
15. RESTORE test-generated state/records to defined pre-reboot installed baseline
16. VERIFY activation enabled exactly once and safe recovery available
17. PERFORM one ordinary controlled reboot
18. RECONNECT within bounded timeout
19. VERIFY exact identity/kernel/config/uImage and connectivity
20. VERIFY automatic activation produced loaded module, guard, device, expected logs, and count delta exactly `+1`
21. VERIFY no duplicate event, warning, oops, BUG, panic, hang, new unexplained taint, or competing activation
22. MARK removal pending and disable all activation through package removal
23. UNLOAD ordinarily without reboot
24. UNINSTALL and purge package
25. VERIFY generated records removed even with module absent
26. VERIFY every baseline record/path/link/metadata/package/APT/protected hash restored; transient DEB, module, endpoint, guard, worker, runtime, state, claim, backup, journal, activation residue absent; connectivity healthy
27. ***if*** unload is busy ***then***
    1. RETAIN removal-pending state
    2. KEEP activation disabled
    3. RETAIN backups/evidence
    4. DO NOT reboot for cleanup
    5. STOP with incomplete uninstall
28. ***if*** boot, module, taint, warning, cleanup, restoration, or connectivity safety fails ***then***
    1. STOP further tests
    2. PRESERVE evidence
    3. QUARANTINE device for requirement
    4. REQUIRE explicit recovery verification before reuse
    5. NEVER force module operation or patch kernel/U-Boot

#### Deliverables and approval gate

Deliver revision-8-bound task manifest, fixed source/tests, two reproducible `.ko` builds, two reproducible canonical `armhf` DEB builds, exact commit/artifact hashes, activation investigation, unit/fault/package/image/HW evidence, dmesg/log/taint/count deltas, full ownership/baseline manifest, `RELEASE.md`, and exact cleanup/restoration proof. Independent validation must PASS full customer requirement, approved revision 8, package reversibility, image restoration, task acceptance, automatic activation, and HW cleanup before merge. No merge on any validation failure.

Nontrivial: kernel-privileged module, boot activation, persistent records/runtime namespace, custom maintainer scripts, approximate ABI waiver, controlled reboot. Commit DRAFT revision 8 before display. Run deterministic `trivial-policy`; only tooling PASS may waive approval. Otherwise wait for explicit approval of exact revision/hash. After approval, auto-progress until hardware gate, safety failure, or tooling blocker.

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

- `2026-09-17T13:41:58+00:00` [implementing] Implementation started from the approved plan

- `2026-09-17T13:42:04+00:00` [implementing] Activated task T01 attempt 1

- `2026-09-17T14:01:01+00:00` [implementing] Recorded task T01 attempt 1 result

- `2026-09-17T14:05:21+00:00` [implementing] Task T01 attempt 1 validation fail

- `2026-09-17T14:40:39+00:00` [implementing] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-17T14:45:32+00:00` [implementing] Updated round 1 implementation section

- `2026-09-17T14:45:37+00:00` [implementing] Updated round 1 implementation section

- `2026-09-17T14:48:27+00:00` [implementing] Updated round 1 implementation section

- `2026-09-17T14:49:17+00:00` [implementing] Updated round 1 implementation section

- `2026-09-17T16:10:28+00:00` [implementing] Activated task T01 attempt 2

- `2026-09-17T16:11:31+00:00` [drafting-plan] Replan approved scope around module-initialization boot counting; exclude kernel/U-Boot patching and reset reasons

- `2026-09-17T16:14:19+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-17T16:14:29+00:00` [draft-ready] Committed DRAFT revision 3 after developer amendment: count exactly one observable boot reaching module initialization; same-boot unload/reload deduplicated by module-owned guard; pre-init resets/boots uncounted. Removed reset-cause collection, all i.MX6 register/MMIO access, retained-counter research, kernel-source and U-Boot/bootloader patching/replacement. Plan keeps minimal OOT module, Bash transport frontend, RELEASE.md, reversible single DEB, controlled live load/unload/reload/boot checks, no target APT mutation, and continuous-lock install/test/uninstall/restoration/quarantine proof. No new load-bearing question; no implementation.

- `2026-09-17T16:14:37+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-17T16:16:41+00:00` [approved] Developer approved DRAFT revision 3 SHA-256 42a33ec51bfd585df1d382afc984fb5ee1eddc418eae51dea0e99368ca0e8d7c

- `2026-09-17T16:16:49+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-17T16:16:54+00:00` [implementing] Implementation started from the approved plan

- `2026-09-17T16:21:10+00:00` [implementing] Updated round 1 implementation section

- `2026-09-17T16:22:49+00:00` [drafting-plan] Amend revision 3 to permit minimal approximate-source insmod/rmmod compatibility probe only

- `2026-09-17T16:26:01+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-17T16:26:06+00:00` [draft-ready] Committed DRAFT revision 4: preserve revision 3 production counter/package/RELEASE.md/EOL exclusions; add developer-authorized approximate-source init/exit/log-only live probe with static ELF/ARM/vermagic/symbol gate, baseline/recovery, ordinary insmod/rmmod, exact dmesg/taint inspection, cleanup proof, anomaly quarantine, and probe-success limitation. No unanswered developer question; no implementation.

- `2026-09-17T16:26:16+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-17T16:27:15+00:00` [approved] Developer approved DRAFT revision 4 SHA-256 2be0f002e9bf51b6d622007bd0643626dc77de6e9841fb46ed7496eac5b7d49a

- `2026-09-17T16:27:21+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-17T16:27:25+00:00` [implementing] Implementation started from the approved plan

- `2026-09-17T16:41:02+00:00` [implementing] Updated round 1 implementation section

- `2026-09-17T16:48:10+00:00` [implementing] Updated round 1 implementation section

- `2026-09-18T11:27:26+00:00` [drafting-plan] Amend revision 4 to permit old-toolchain rebuild and one bounded live probe retry

- `2026-09-18T11:34:46+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-18T11:34:55+00:00` [draft-ready] Committed DRAFT revision 5: preserved revision 4 init/exit/log-only probe and revision 3 production scope; added pinned LETS-managed Linaro GCC 4.8-2014.04 toolchain install under LETS state, idempotent devenv init, top-level toolchain wrapper, atomic verification/recovery/offline tests, and one gated ordinary probe retry. No direct compatibility tools, target APT, force load, VFS/MMIO probe behavior, persistence, boot activation, or reboot. Nontrivial; approval policy next.

- `2026-09-18T11:35:06+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-18T11:36:39+00:00` [approved] Developer approved DRAFT revision 5 SHA-256 6d2f45c30c3a4eaf77070ac64c5fe5549c18016f9889655566d2ddb86c887600

- `2026-09-18T11:36:46+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-18T11:36:52+00:00` [implementing] Implementation started from the approved plan

- `2026-09-18T11:46:47+00:00` [drafting-plan] Replan toolchain runtime after verified i386-host archive incompatibility

- `2026-09-18T11:51:20+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-18T11:51:25+00:00` [draft-ready] Committed DRAFT revision 6 after verified revision-5 blocker: pinned Linaro archive is i386-host and requires /lib/ld-linux.so.2. Added hermetic Ubuntu Trusty i386 runtime entirely under LETS state using seven exact authoritative archive packages with pinned sizes/SHA-256, safe no-script .deb extraction, recursive ELF dependency proof, managed loader/library invocation, atomic idempotent repair/offline/concurrency tests. Preserved revision 3 production, revision 4 probe, revision 5 LETS scope; one gated ordinary retry only. No host/target APT, sudo, global install, force, VFS/MMIO probe, persistence, boot, or reboot. No unanswered developer question; nontrivial approval required unless deterministic policy says otherwise.

- `2026-09-18T11:51:41+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-18T12:09:29+00:00` [approved] Developer approved DRAFT revision 6 SHA-256 eaa5b1ea6f36bf64e3c18d9301ffbb90f6581fdbea3c0198907ae814315e4242 via proceed instruction.

- `2026-09-18T12:09:39+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-18T12:09:43+00:00` [implementing] Implementation started from the approved plan

- `2026-09-18T12:29:02+00:00` [implementing] Updated round 1 implementation section

- `2026-09-18T12:41:34+00:00` [implementing] Updated round 1 implementation section

- `2026-09-18T13:08:15+00:00` [drafting-plan] Developer confirms legacy vendor artifacts are unavailable and explicitly authorizes completing requirement implementation and real-hardware testing with the validated approximate NXP source and LETS-managed toolchain; retain reversible package, locking, cleanup, restoration, and quarantine safety controls.

- `2026-09-18T13:11:12+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-18T13:11:16+00:00` [draft-ready] Committed DRAFT revision 7 after developer confirms legacy vendor artifacts unavailable and explicitly accepts approximate NXP source plus LETS-managed GCC for production and real-HW tests. Preserves observable-init semantics, no MMIO/reason/kernel/U-Boot patching, reversible single-DEB lifecycle, continuous image lock/restoration/quarantine, ordinary module operations, production static gates, one controlled reboot, exact target cleanup. No unanswered load-bearing question.

- `2026-09-18T13:11:20+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-18T13:12:51+00:00` [approved] Developer approved DRAFT revision 7 SHA-256 3b397ef90c63e6037302d7ca4eab7dd47773017ba26c538e24be60e811300ad6.

- `2026-09-18T13:12:57+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-18T13:13:01+00:00` [implementing] Implementation started from the approved plan

- `2026-09-18T16:11:18+00:00` [implementation-ready] Recorded implementation commit 7610f9249db5640e7db82fbed20d23ff1f3b6c6d

- `2026-09-18T16:11:40+00:00` [validating] Independent validation started

- `2026-09-18T16:12:20+00:00` [validating] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-18T16:14:28+00:00` [implementing] Independent validation fail

- `2026-09-18T16:14:55+00:00` [drafting-plan] Revision 7 independent validation failed: automatic boot activation produced no module/guard/device/record; record parent-sync retry can duplicate random record; guard sync error returns success; uninstall may retain records when module absent; ARM .ko DEB incorrectly Architecture all; task manifest approved-plan hash stale. Replan all defects, inspect exact SysV runlevel sequencing, repeat locked lifecycle tests, and require one bounded reboot retest.

- `2026-09-18T16:17:30+00:00` [drafting-plan] Updated round 1 solution-plan section

- `2026-09-18T16:17:50+00:00` [draft-ready] Committed DRAFT revision 8 after revision 7 validation FAIL: preserve developer-approved approximate ABI and production scope; require evidence-derived Debian 8 SysV activation, immutable record identity, propagated guard sync failure, deterministic loaded/absent-module uninstall cleanup, one canonical armhf DEB, revision-8-bound task manifest, regression tests for all six defects, two reproducible builds, continuous-lock restoration/quarantine, and one bounded HW reboot retest. No unanswered load-bearing question.

- `2026-09-18T16:17:54+00:00` [awaiting-approval] Trivial policy failed; developer approval is required

- `2026-09-18T16:22:57+00:00` [approved] Developer approved DRAFT revision 8 SHA-256 15c49323b5434881e27f357bd675d3d7dedd02911392e1d0a43904316f15bbd5.

- `2026-09-18T16:23:01+00:00` [approved] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-18T16:23:04+00:00` [implementing] Implementation started from the approved plan

- `2026-09-18T16:37:40+00:00` [implementing] Split approved-plan candidate into 4 bounded tasks

- `2026-09-18T16:38:00+00:00` [implementing] Activated task T01 attempt 1

- `2026-09-18T16:38:05+00:00` [implementing] Recorded task T01 attempt 1 result

- `2026-09-18T16:38:42+00:00` [implementing] Prepared implementation worktree sdlc-req/req-0001-goal-count-system-resets

- `2026-09-18T16:40:55+00:00` [implementing] Task T01 attempt 1 validation fail
