---
schema: 1
id: REQ-0001-GOAL-COUNT-SYSTEM-RESETS
title: Count system resets reliably
state: planner-questions
round: 1
sequence: 8
approval: none
implementation_branch: 
implementation_commit: 
updated: 2026-09-17T12:51:55+00:00
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

### Solution plan — DRAFT

Pending.

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
