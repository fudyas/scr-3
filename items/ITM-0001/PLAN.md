# ITM-0001-BMC-RESET-MONITOR-UTILITY — Plan

## Goal

Deliver RAOM steps 1 and 2: validated BMC reset tracking and user-space decision API. Package `/usr/sbin/scr-resets-monitor`, durable history, SysV observation hook, and system rotation integration. Require explicit threshold/window arguments. Return decision only. Preserve exact-package hardware acceptance as separate gate.

## Context

1. Customer: "Update the item's brief to mention it is step 1+2 of the ROAM. Then run $sdlc-plan on this item". Email calls mode RAOM.
2. Latest decisions: "Decision only, no boot or entering RAOM in the scope of this item". "Require explicit values as CLI arguments, no defaults". "Startup: use existing SysV - agreed".
3. Agreed observation hook remains. "No boot" excludes mode/startup gating. All 21 responsibilities in `brief-consolidated.md` remain acceptance anchors.
4. Canonical inputs: `.codex/sdlc/artifacts/items/ITM-0001/planning/raom-step12-20261112/`: emails, rulings, `brief-consolidated.md`, `image-facts.md`, and `target-runtime-storage.log`.
5. Latest request: "Rerun the planning". INPUT `9484028def2a287194e3c26706fb2fa9f9ca0a685b517eb7616c74577261cb54` preserves r2 FAIL, partial source, and gate correction. Approved r2 stays immutable.
6. Observed SCR-7CCC91: `armhf`, Linux `3.10.105-imx6 #5`, glibc `2.19`, SEMA `2.5 R4`, SysV, logrotate `3.8.7`. `/var/log` resides on writable ext4 root. Power-loss persistence remains unqualified.
7. `ITM-0006` is DONE. Keep dependency and original plan/task history. Fresh read-only transcripts reside under managed `planning/replan-20261112/`.
8. Resume existing block `/home/fudya/devel/scr/.codex/worktrees/ITM-0001/BLK-0001`, commit `5e922e57766d27dc439d6f5c1449b7e7ab561a5b`. Only documentation/constants exist. Preserve other workers' edits.

## Design

1. **Fit:** Native C99/POSIX utility uses existing SEMA through fixed read-only commands. Qualified managed ARM toolchain targets installed libc. No Python installation.
2. **Patterns:** Separate pure parsing/window rules, observation use cases, SEMA/storage adapters, and CLI. Reuse SysV, monit program checks, system logrotate, LETS package scaffold, and restoration gates.
3. **Context:** `docs/MONIT.md` supplies service relationships. Current SDLC contract governs evidence/safety. Monit state remains diagnostic only. BMC totals remain authoritative.
4. **Decision:** `check --max-resets N --window SECONDS` returns 0 at/below limit, 1 above limit, 2 unavailable. Interval evidence prevents invented reset timestamps.
5. **Revised bounds:** Strict `uint64_t` parser capacity replaces unavailable vendor maximum as implementation prerequisite. Every decrease is discontinuity. No rollover or physical-retention guarantee follows.

## Out of scope

1. Entering/leaving RAOM, normal-boot gating, service suppression, monit recovery actions, latches, healthy-reset budgets, and caller action on unavailable.
2. Kernel modules/rebuilds, init migration, watchdog changes, BMC writes, counter clearing, firmware/flash changes, and agent-operated reboots.
3. Private rotation scheduler, production threshold defaults, unrelated monit fixes, other-item edits, and quarantine recovery.

## Proposed revision changes

1. Amend responsibility 3's unavailable documented-firmware-range requirement: accept decimal counters representable in `uint64_t`. Reject negatives, syntax errors, and overflow.
2. Preserve responsibility 15: every decrease invalidates continuity. Firmware width, maximum, rollover, and complete reset retention remain unknown, never inferred from parser capacity.
3. Replace broad r2 qualification gate with recorded command/runtime facts and concrete clock/startup rules below. Physical persistence/reset-mode acceptance remains later hardware gate.
4. Permit offline tasks 1–7 and 9 before source-image recovery. TSK-0008 requires cleared quarantine, qualified source image, complete ownership evidence, and full restoration.
5. Execute documentation TSK-0009 before final image task TSK-0008. Stable task IDs remain. No end-to-end delivery or installation is unblocked by this revision alone.
6. These changes require new explicit approval. Historical r2 FAIL and corrected header-probe evidence remain valid records of their original criteria.

## Safety

1. Item already has `hardware.required=true`. Device operations require separate authority and exact device/image/package identity. Plan approval grants no device action.
2. Existing quarantine remains. Approved recovery with restoration proof must precede blocked image reuse. Missing source-image identity blocks package image acceptance.
3. PRESERVE original `var/image_8.26.0`, kernel archive, README, metadata, previous packages, historical ledgers, and unrelated edits.
4. DELIVER one reversible `scr-resets-monitor` Debian package, architecture `armhf`. Declare qualified libc/helper dependencies. Preserve installed SEMA bytes and ownership.
5. DECLARE payload paths: `/usr/sbin/scr-resets-monitor`, `/etc/init.d/scr-resets-monitor`, `/etc/logrotate.d/scr-resets-monitor`, and `/usr/share/doc/scr-resets-monitor/`.
6. DECLARE generated paths: qualified SysV links, `/run/lock/scr-resets-monitor.lock`, `/var/log/scr/`, logs/state/journal, and utility rotation generations.
7. DECLARE utility-owned `.resets-rotation.json` barrier and stanza hooks. Preserve global `/etc/cron.daily/logrotate` unchanged. Introduce no diversion.
8. DECLARE private package payload/backups, `/var/lib/scr-sdlc/owners` records, affected parents, and shared logrotate-state changes. Inventory every touched path.
9. BACK UP pre-existing managed paths before mutation. Preserve bytes, type, uid/gid, mode, links, hardlink relationships, timestamps, and xattrs. Record originally absent paths.
10. REJECT unexpected dpkg owners, overlaps, symlinks, and path types. Missing package file lists make ownership inventory incomplete, not unowned. Preserve unrelated files/SEMA.
11. RETAIN initial restoration baseline across upgrades. Preserve committed utility data. Cover failed install, interrupted configure, upgrade, abort-upgrade, remove, purge, and rollback.
12. REQUIRE uninstall of all delivered packages to restore original payload/metadata. Remove package-created files, rotation generations, barriers, links, directories, and ownership markers.
13. EXPORT new logs as managed evidence before uninstall. Export grants no exception to whole-image restoration.
14. HOLD shared image lock through source checks, disposable copy, mount, install, tests, upgrades, rollback, uninstall, restoration, unmount, and cleanup.
15. RETAIN source hashes, architecture, root-scoped dpkg, overlap, whole-tree fingerprints, xattrs, mount/loop, and cleanup checks. Ordinary leases never replace image lock.
16. QUARANTINE after restoration/cleanup failure. Preserve evidence and logical quarantine. Stop image work until separately approved recovery succeeds.
17. PUBLISH explicit INPUT manifests from `.codex/sdlc/artifacts/items/ITM-0001/` through `./bin/lets sdlc artifacts publish`. Preserve bytes, modes, paths, and hashes.
18. REQUIRE independent validation and detached QA against exact source tree/INPUT pair. QA publishes separate RESULT. Historical exploration is INPUT, never delivered-package acceptance.
19. REQUIRE `--expected-artifacts DIGEST` on bound verified/approve/settle/prepare-promotion/promote commands. Missing index cannot imply source-only acceptance.
20. STOP after three same-stage failures, safety failure, unavailable required evidence, or material contract change. Retain exact error and resume prerequisite.
21. CAPTURE separate exact before/after manifest for `/var/log/scr/` and affected `/var/log` parent metadata under same full image lock. Existing `SDLC_VERIFY_EXCLUDES` excludes `/var/log`.
22. INCLUDE bytes, path absence/type, uid/gid, modes, timestamps, symlink/hardlink topology, and xattrs in supplementary manifest. Ordinary `test-package` fingerprint alone proves no log restoration.
23. REQUIRE complete ownership inventory before actual installation on image or hardware. Current target's missing dpkg `.list` files block installation until separately authorized repair/proof.
24. KEEP image and device package gates independent from offline source/build/tests. Never access quarantined image to qualify offline code, and never mark final delivery complete without those gates.

### Post-task item acceptance

1. VALIDATE completed task/block criteria independently before final item ceremonies.
2. ASSEMBLE integration and capture exact source tree plus immutable INPUT. Run independent detached QA and publish separate bound RESULT.
3. PRESENT exact source/INPUT/RESULT pair, package hashes, tests, rollback, and hardware obligations for explicit SHOW approval.
4. PROMOTE only exact approved verified revision through bound LETS commands. Preserve integration ownership across fixes and repeat affected verification.
5. KEEP hardware-required item in REVIEW until separately authorized exact-package developer acceptance passes. Final QA/RESULT/SHOW/promotion are not task prerequisites.

### Hardware acceptance after exact-revision SHOW

1. IDENTIFY SCR-7CCC91 or approved replacement, actual image/version/hash, BMC identity/firmware, exact package version/SHA-256, and rollback artifact.
2. OBTAIN explicit installation/test authority. Separate developer-operated resets/power loss from read-only agent observations.
3. RECORD pre-install counters, boot identity, time quality, package inventory, and original managed-path metadata.
4. INSTALL exact reviewed package under approved procedure. Verify actual runtime, boot observation, CLI exits, logs, and system rotation.
5. REQUEST agreed developer resets. Record before/after values, boot IDs, intervals, expected/observed decisions, logs, and verbatim developer report.
6. QUALIFY repeated resets, full power-loss retention, and Linux-fails-before-utility coverage through separately authorized procedures. Record unsupported modes explicitly.
7. KEEP software/watchdog reset tests separately authorized. Historical manual reset reporting `Watchdog` does not prove watchdog-trigger coverage.
8. VERIFY upgrade preservation and approved rollback/uninstall. Export logs before restoration. Retain working remote/recovery path.
9. RECORD exact-package result through `./bin/lets sdlc hardware pass|fail`. Missing authority/evidence leaves item REVIEW, never DONE.
10. REQUIRE fresh SHOW and hardware acceptance after package bytes change. Automated tests never establish hardware success.

## BLK-0001 — DELIVER BMC TRACKING AND DECISION UTILITY

Single block owns utility, package, tests, and product documentation. Dependencies reference earlier tasks in this block only.

### TSK-0001 — RECONCILE OBSERVED PROFILE AND BUILD CONTRACT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. UPDATE existing `docs/RESET-MONITOR.md` and `src/scr_resets_monitor/platform.h` in preserved block commit, not a new empty worktree.
2. RECONCILE historical BLOCKED text against this approved revision. Preserve original reports, source hashes, commit, and correction in immutable evidence.
3. PIN fixed argv `/usr/bin/sema cap all` from `target-elf.log`, with exact help/output/exit evidence from `target-readonly.log`.
4. DEFINE capability and observation parsing sections separately. Capability `Restart event: 1` and observation `Restart event: Watchdog` are different fields.
5. RETAIN SEMA `2.5 R4`, capability `0x38ebf`, firmware `BMC LEC-iMX6 0v13 Jun 25 2015`, and raw bootloader `bl_LiMX6 3v2 Aug  5 2014`.
6. RETAIN binary SHA-256 `b9fbc6b88c3a2e382d9566dcd7573c2abd6bd38f194d5be2d7466bd910c3e383` and library SHA-256 `09cf935188b2ca31792ff99ec7ecaf95855b4824572b4a3945eb898022a9b159`.
7. DEFINE decimal parser capacity `0..UINT64_MAX`, including overflow-safe conversion/arithmetic. Label firmware maximum/width unknown. Map no wrap modulus.
8. RECORD observed restart-cause text verbatim. Required field must be nonempty, bounded, and structurally valid. Unrecognized cause stays unknown diagnostic text, never zero resets.
9. REUSE retained managed GCC `4.8.3` compile/equivalent link through actual assigned-checkout LETS wrapper. Preserve original `collect2: error: ld returned 255 exit status` evidence.
9.1. KEEP existing block's working `./bin/lets toolchain` route. Requalify routing after integration with later committed changes. Copy no concurrent uncommitted route edits.
10. COMPARE build contract with `target-elf.log` and `target-librt-scheduler.log`: ELF32 ARM EABI5 hard-float, VFP register arguments, `/lib/ld-linux-armhf.so.3`, supported GLIBC versions.
11. RECORD live target storage/init/clock/helper facts from `target-readonly.log` and `target-time-helpers.log`. These are implementation inputs, not source-image equivalence.
12. KEEP `SCR_RESETS_PROFILE_QUALIFIED=0` until TSK-0002 implements/tests observed-profile validation. Replacement support flag must not claim image or hardware qualification.
13. DOCUMENT exact task-specific readiness: code/build contract now, real ARM execution/rotation before TSK-0008 completion, physical retention at hardware acceptance.
14. RETAIN source-image quarantine and incomplete target dpkg inventory as installation/restoration prerequisites, not offline code prerequisites.

**Done when**

1. Existing files describe fixed command, parser capacity, observed profile, build contract, concrete clock/startup rules, and stage-specific limits without broad prerequisite ambiguity.
2. Independent audit can trace each fact to captured command/output/status. Current NTP sync never claims historical/next-boot trust or power-loss persistence.
3. Header compiles through nonempty include probe with checked exit status. Historical failed standalone-header probe and correction both remain intact.
4. No source-image/device access or runtime installation occurs. Counter-range policy change is explicit and approved before task execution.

### TSK-0002 — IMPLEMENT BOUNDED READ-ONLY BMC ADAPTER

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | high |

**To do**

1. ADD `src/scr_resets_monitor/{types.h,sema.c,sema.h,clock.c,clock.h,Makefile}` and `tests/reset_monitor/test_reader.py`.
2. IMPLEMENT `read_bmc_observation`, `parse_sema_output`, and `read_clock_context` with explicit success/unavailable results.
3. EXECUTE only `/usr/bin/sema cap all` directly under stable locale. Reject arbitrary command injection and production test-backend overrides.
4. REQUIRE successful exit, complete/unique fields per section, strict decimal `uint64_t` counters, supported profile/identity, and nonempty bounded cause text.
5. BOUND each SEMA attempt to two seconds. Permit one retry. Bound total acquisition to five seconds including termination handling.
6. LIMIT output/field lengths. Reject truncation, overflow, conflicting fields, timeout, missing device, unsupported profile, and malformed output.
7. RECORD UTC observation time, monotonic/boot uptime, Linux boot ID, clock quality, board identity, firmware, counters, and latest cause.
8. BRACKET complete SEMA acquisition with realtime, `CLOCK_BOOTTIME`, and read-only `adjtimex(modes=0)` samples. Never set clock or wait for synchronization.
9. ACCEPT clock quality only with successful `TIME_OK`, `STA_UNSYNC` clear, and valid nonnegative uncertainty fields. Otherwise persist counters with invalid-time reason.
10. SET timestamp uncertainty from maximum endpoint error plus complete acquisition-bracket duration and clock resolution. Reject overflow or inconsistent samples. Claim no atomic multi-field snapshot.
11. COMPARE same-boot realtime elapsed against boot-clock elapsed using combined uncertainty intervals. Nonoverlap marks clock discontinuity and breaks time coverage.
12. REQUIRE independently valid UTC anchors on both sides of cross-boot intervals. Current sync never retroactively validates boot-time timestamps.
13. BRACKET intermediate invalid-time observations only through trustworthy outer anchors and unchanged controller epoch. Otherwise window decision remains unavailable.
14. LABEL uncertainty as clock-health evidence, not a threshold/window default. Missing kernel time status fails closed. Infer no synchronization from ntpd process presence.
15. PROVIDE injected reader/clock seams in test binaries only. Keep production hardware commands read-only and allowlisted.
16. REPLACE disabled profile flag only after supported schema/identity/binary checks pass their tests. Name support as observed-profile compatibility, never full hardware qualification.

**Done when**

1. Retained SEMA fixtures produce exact totals/identity. Zero means returned valid value, never substituted error.
2. Tests cover section-specific duplicate labels, missing fields, negative/UINT64 overflow, unknown diagnostic cause, oversized output, failed exit, timeout, and device errors.
3. Host-native compiled test binary exercises actual parser/process/time adapters with fixture commands. Deadline/retry tests include child cleanup failure as explicit unavailable.
4. ARM build passes static ELF/ABI/symbol audit against captured target runtime. Real ARM execution remains mandatory TSK-0008 criterion, not claimed from host tests.
5. Clock tests cover unsynced startup, unavailable status, leap/error states, uncertainty overflow, steps/regressions, reboot, and conservative interval widening.
6. Hardware argv contains no writes, counter clearing, watchdog, reboot, or firmware commands. Responsibilities 2–4, 7, and 21 have direct evidence.

### TSK-0003 — IMPLEMENT DURABLE OBSERVATION STORE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | high |

**To do**

1. ADD `src/scr_resets_monitor/{store.c,store.h,json.c,json.h}` and `tests/reset_monitor/test_store.py`.
2. IMPLEMENT `commit_observation`, `recover_transaction`, `read_committed_state`, and strict versioned JSON codec.
3. MANAGE `/var/log/scr/resets.jsonl`, `/var/log/scr/resets-state.json`, and `/var/log/scr/resets-monitor.log`, root-owned mode `0600`.
4. CREATE owned `/var/log/scr/` mode `0700` when absent. Preserve unrelated files and original metadata through package lifecycle.
5. USE hidden `.resets-transaction.json` journal for interrupted commits. Exclude state/journal/rotation barrier from rotation.
6. SERIALIZE history/state access with `/run/lock/scr-resets-monitor.lock`. Bound utility lock acquisition to one second. Contention returns unavailable.
7. DEFINE schema version, baseline epoch, sequence/event identity, context, separate counter deltas, validity/discontinuity, and coverage metadata.
8. ENCODE counters/deltas as decimal strings for lossless JSON interchange. Reject corrupt, conflicting, or unsupported records.
9. ESTABLISH initial baseline without reporting lifetime totals as new resets. Preserve original totals and first-observation boundary.
10. RECORD positive deltas once, including aggregate delta greater than one. Attribute cause only to latest observed event.
11. DEDUPLICATE transaction retries. Repeated unchanged probes create no duplicate reset event. Distinguish durable coverage checkpoints from reset events.
12. WRITE/synchronize journal before history mutation. Synchronize complete history record before atomic state replacement and parent-directory synchronization.
13. RETAIN previous committed state during uncertain transaction. Recovery reconciles journal/history/state idempotently before new observations.
14. DEFINE durable commit point. Cleanup failure cannot erase committed record. Unresolved commit never appears as valid state.
15. KEEP last proven committed baseline on read/write/sync errors. Preserve uncertain bytes for recovery instead of destructive truncation or silent rebaseline.
16. REPORT failures through stderr/existing syslog when own log is unavailable. Persistence failure never returns healthy.
17. PRESERVE counter decrease, firmware/controller change, and unexpected boot/counter relationships as discontinuity evidence.
18. START invalid coverage epoch only after durable discontinuity record. Treat every decrease as discontinuity, including apparent wrap. Never infer rollover increments or clear BMC totals.
19. REQUIRE full trustworthy new window after discontinuity before healthy decision. Introduce no RAOM latch or reset-budget policy.

**Done when**

1. Fault tests cover short writes, ENOSPC, read-only storage, permissions, fsync/rename errors, torn files, and crash at every commit boundary.
2. Failed history write with baseline 146 and BMC 147 leaves committed baseline 146. Later success records accumulated delta exactly once.
3. Concurrent calls, boot retries, restarts, and recovery produce no duplicate reset delta or missing committed observation.
4. Status distinguishes last committed observation from incomplete transaction and failed attempt. Discontinuities never appear as normal increments.
5. Actual filesystem recovery tests cover synchronization failures. Responsibilities 5–15 and 20 have direct evidence.

### TSK-0004 — IMPLEMENT DECISION CLI AND WINDOW CONTRACT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0003 |
| 2 | model | high |

**To do**

1. ADD `src/scr_resets_monitor/{window.c,window.h,cli.c}` and `tests/reset_monitor/test_decision.py`.
2. IMPLEMENT `evaluate_window`, `run_record`, `run_status`, and `run_check` using qualified reader/store interfaces.
3. PROVIDE `record`, `status --json`, and `check --max-resets N --window SECONDS`. Support `check --json` for machine-readable decision.
4. REQUIRE both check arguments each call. Accept decimal integer N ≥ 0 and SECONDS > 0 within checked arithmetic range.
5. REJECT missing, duplicate, negative, fractional, malformed, overflow, and unknown arguments with exit 2 and explicit usage error.
6. READ no threshold/window from environment, configuration, or built-in fallback. `record` needs neither value.
7. DEFINE window `(observationTime - SECONDS, observationTime]`. Count boot-count increments. Report power-cycle changes separately without double counting.
8. ASSIGN delta to interval between valid observations, never invented reset timestamp. Wholly contained interval contributes entire delta.
9. EXCLUDE wholly outside intervals. Expand observation/window boundaries by recorded clock uncertainty. Retain lower/upper count bounds for overlaps.
10. REQUIRE trustworthy current clock, valid controller epoch, committed refresh, and trustworthy anchor covering earliest possible window start.
10.1. BRACKET intervening invalid-time observations as aggregate between valid outer anchors. Never assign individual reset times or infer historical sync.
10.2. RETURN 2 until adequate trustworthy coverage exists after initial/unsynchronized boot, clock discontinuity, or controller discontinuity.
11. ***if*** coverage is absent, clock invalid, acquisition/persistence fails, or outcome ambiguous ***then*** RETURN unavailable with exit 2.
12. ***if*** supported lower bound exceeds N ***then*** RETURN `raom_required` with exit 1.
13. ***else if*** supported upper bound is at most N ***then*** RETURN `normal` with exit 0.
14. ***else*** RETURN `unavailable` with exit 2. No branch starts/stops services or enters mode.
15. DEFINE JSON fields: `schema_version`, `decision`, `reason`, `max_resets`, `window_seconds`, `window_start`, `window_end`, `reset_count_min`, `reset_count_max`, `coverage`, `observation`.
16. DEFINE status fields: latest committed observation, age, clock/store validity, pending transaction, and last persisted failure when available.
17. KEEP status read-only toward BMC. Report freshness explicitly. Cached values never imply successful current reading or persistence.
18. RETURN `record` 0 after durable valid observation, otherwise 2. Return `status` 0 for valid committed store, otherwise 2. JSON exposes time/decision limits.
19. DOCUMENT initial baseline, insufficient retention, clock jumps, sparse observations, and discontinuity behavior beside CLI contract.

**Done when**

1. Missing values fail. Environment/configuration never substitute. `N=5`, `SECONDS=900` appear only as tests/examples.
2. N proven increments return 0. N+1 return 1. Exact window boundaries have tests.
3. Aggregate intervals remain aggregate. Ambiguous boundary, missing anchor, invalid time, and incomplete/corrupt history return 2.
4. Current read/storage failure returns 2 despite earlier good history. No failed read becomes zero or cached result becomes current success.
5. CLI/JSON tests cover decisions, reasons, numeric limits, age, cache validity, and incomplete commits. Responsibilities 16–18 and step 2 are covered.
6. Tests intercept service-control, reboot, watchdog, and BMC-write attempts and prove none occur.

### TSK-0005 — INTEGRATE SYSV OBSERVATION AND MONIT EXAMPLES

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0004 |
| 2 | model | default |

**To do**

1. ADD `packaging/scr-resets-monitor/init/scr-resets-monitor`, `packaging/scr-resets-monitor/examples/monit-check.conf.in`, and `tests/reset_monitor/test_integration.py`.
2. IMPLEMENT idempotent asynchronous SysV hook after `mountall-bootclean` and `mountnfs-bootclean`, with `$local_fs` ready. Invoke `record` only.
3. USE observed `/etc/rcS.d/S17scr-resets-monitor` hook after existing `S16bootmisc.sh` as target layout. Verify exact source layout before installation.
3.1. LAUNCH detached bounded record worker and return immediately. No synchronous SEMA read, lock wait, fsync, or NTP wait in init parent.
3.2. PRESERVE all existing watchdog/monit links and start ordering. Do not run global dependency reordering that changes unrelated service links.
4. ROUTE bootstrap errors to stderr/syslog when log storage cannot persist. Later successful `record`/`check` captures accumulated delta.
5. INSTALL disabled monit example under package documentation. Require operator-supplied literal N/window before deployment.
6. SHOW separate status conditions for exits 1 and 2, reporting only. Include no recovery action or automatic enabled symlink.
7. COVER substituted example in offline integration tests. Exact target monit syntax validation remains required in TSK-0008. Preserve active configuration/recovery policy.
8. DOCUMENT manual record, hook retry, status inspection, and unavailable outcomes in `docs/RESET-MONITOR.md`.

**Done when**

1. Init tests prove writable-storage ordering and unchanged monit/watchdog startup. Failed observation cannot block boot.
2. Hook invokes `record` without parameters. Later successful call captures missed delta exactly once.
3. Package enables no threshold check and supplies no production values. Example needs explicit substitution.
4. Example and consumer tests distinguish 1 from 2 with reporting only. Exact target syntax/runtime acceptance remains TSK-0008. Responsibilities 1, 12, 16, 17, and 21 are traced.

### TSK-0006 — INTEGRATE SYSTEM ROTATION AND COVERAGE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0005 |
| 2 | model | high |

**To do**

1. ADD `packaging/scr-resets-monitor/logrotate/scr-resets-monitor`, `src/scr_resets_monitor/rotation.c`, and `tests/reset_monitor/test_rotation.py`.
2. EXTEND `store.c` with `read_retained_history` and integrity/coverage checks for active, numbered, and system-compressed history.
3. INTEGRATE utility logs with existing logrotate schedule/retention/size/compression policy. Exclude state/journal. Use rename/create, never copytruncate.
4. OPEN current log path each invocation. Set created log ownership/mode correctly.
5. IMPLEMENT `begin_rotation` and `end_rotation` maintenance commands through utility stanza `firstaction`/`lastaction`, with shared scripts.
6. UNDER history flock, persist `.resets-rotation.json` with actual logrotate owner PID/starttime/boot ID and pre-rotation history inventory. Reject hook-shell identity.
7. REQUIRE normal reader/writer calls to inspect barrier under flock. Active or uncertain barrier returns 2 without changing committed data. Diagnostics use stderr/syslog.
8. CLEAR barrier under flock only after qualified final hook confirms rename/compression completion and validates current history/state coverage.
9. ON owner death/reboot, require proof that every rotation/compression participant is quiescent before inventory reconciliation. Parent death alone proves nothing about surviving children.
10. READ compressed records through qualified bounded decompressor argv. Reject corrupt archives, sequence gaps, conflicting duplicates, incomplete records, and unsafe paths.
11. RETAIN cumulative counters and coverage watermark in nonrotated state. Old-history deletion reduces coverage, never resets totals or silently starts healthy window.
12. RETURN 2 when retained history cannot support supplied CLI window. Add no utility cron job, timer, daemon, or private scheduler.
13. PREPARE offline scenarios for hook ordering, failure propagation, manual calls, simultaneous rotators, and removal with barrier active. Actual logrotate 3.8.7 execution belongs to TSK-0008.
14. PRESERVE global cron script, unrelated stanzas, and existing schedule unchanged. Reject begin-hook failure before utility rotation. Uncertain recovery stays unavailable.
15. TREAT direct file mutation outside system rotation as invalid history. Retain evidence and explicit unavailable. Never invent continuity.
16. KEEP barrier active with exit 2 when participant quiescence cannot be proven. Require explicit recovery. Never clear by timeout or parent death alone.
17. VALIDATE complete committed history under flock only after quiescence proof. Clear barrier only after validation and durable state synchronization.

**Done when**

1. Offline stanza/barrier tests cover rename/create, compression, deletion, corrupt archives, concurrent calls, and manual rotation through actual compiled maintenance interface.
2. Rotation loses no committed delta and duplicates no event. State/journal never rotate. Cumulative baseline survives history deletion.
3. Complete windows return correct decisions. Missing coverage returns 2, including windows beyond system retention.
4. Original system rules/schedule remain unchanged. Manual logrotate calls execute same hooks. No global wrapper or private scheduler exists.
5. Tests cover owner death with surviving compression child, wrong owner, PID reuse, hook failure, partial compression, barrier failure, reboot, and concurrent rotators.
6. Offline failure tests exercise hook ordering and ownership assumptions. Actual logrotate 3.8.7 proof remains mandatory TSK-0008 gate. Responsibility 19 is traced.

### TSK-0007 — BUILD REVERSIBLE DEBIAN DELIVERY

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0006 |
| 2 | model | high |

**To do**

1. GENERATE scaffold with `./bin/lets sdlc package-init ITM-0001` only after approved running state and hardware-required checks.
2. KEEP generated sources at command-reported item-worktree path. Add `packaging/scr-resets-monitor/build.sh` as deterministic consumer.
3. COMPLETE generated `debian/control`, `rules`, `preinst`, `postinst`, `prerm`, `postrm`, and operation manifest.
4. REUSE `SdlcPackageHelper.cmd_package_init` private payload/backup pattern. Extend scripts for runtime paths, parents, rotated files, and rotation barrier lifecycle.
5. DECLARE exact version, architecture, dependencies/conflicts, payload ownership, permissions, and maintainer-script behavior.
6. CHECK complete dpkg file-list inventory and all owners/overlaps before managed payload/backup/marker mutation. Missing lists refuse installation. Capture original baseline once.
7. INSTALL utility/init/rotation without BMC reads or active monit reload during image package tests. Enable observation hook for subsequent boot only.
8. REJECT incompatible data schema without replacing working state/binary. Verify failed upgrade, reinstall, downgrade, and rollback behavior.
9. RESTORE original managed paths/metadata on remove/purge, including runtime files, rotated logs, init links, rotation barrier, and parent directories.
10. ACCOUNT for package bookkeeping and shared logrotate-state changes. Preserve unrelated files and other package ownership.
11. RETAIN exact `.deb`, source/build manifest, architecture output, version, and SHA-256 under managed implementation INPUT paths.
12. TEST absent/corrupt package file-list rejection in controlled synthetic roots. Current live-target database repair remains outside item authority.

**Done when**

1. Script tests cover clean/pre-existing installs, expected/unexpected ownership, overlap, interrupted install, upgrades, active rotation, rollback, remove, and purge.
2. Upgrade preserves committed counters/history. Uninstall restores pre-install payload/metadata, including initially absent paths.
3. SEMA hashes remain unchanged. No undeclared runtime install, watchdog/service action, or counter write occurs.
4. Build source/toolchain are pinned. Version/hash and ownership match manifest. Synthetic-root lifecycle tests pass without image access or live installation.
5. Package refuses incomplete ownership inventory before managed payload/backup/marker writes. Dpkg bookkeeping remains separately accounted and restored. Real-image/hardware installation stays pending.

### TSK-0009 — COMPLETE OPERATOR CONTRACT AND HARDWARE HANDOFF

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0007 |
| 2 | model | default |

**To do**

1. COMPLETE `docs/RESET-MONITOR.md`: platform, architecture, CLI/JSON, window rules, durability/recovery, rotation, package lifecycle, and limits.
2. UPDATE relevant `docs/MONIT.md` consumers with decision API and disabled explicit-argument example. Preserve historical findings and unrelated proposals.
3. LINK package docs/examples. Update affected architecture/index records only where present.
3.1. REBUILD package after delivered documentation/example changes. Re-run affected packaging checks and record final version/hash before hardware handoff.
3.2. USE these final package bytes for TSK-0008 and later SHOW/hardware acceptance. Superseded builds retain history but provide no final acceptance.
4. ADD responsibility matrix numbered 1–21 linking original anchors, symbols, tests, and retained evidence.
5. DISTINGUISH observation hook from future boot/mode control. Exit 1 changes no service. Exit 2 defines no caller action.
6. DOCUMENT counter/reset-mode/clock qualification, initial window, sparse observations, retention, discontinuities, and rebaseline limits.
7. PREPARE exact-package hardware procedure with identities, source hashes, expected/observed table, logs, developer reset ownership, rollback, and verbatim report field.
8. INCLUDE installation/error-path checks, developer resets, separately authorized power-loss/early-Linux-failure tests, upgrade, and approved uninstall/restoration.
9. RECORD pending authority/hardware evidence separately from automated passes. Preserve historical reset observation and its limits.
10. PREPARE evidence index with explicit pending TSK-0008/image/hardware entries. Add no invented future result. Coordinator publishes later completed evidence for final ceremonies.

**Done when**

1. Docs/help/schema/example/package/tests agree on mandatory values, exits 0/1/2, and decision-only behavior.
2. Matrix covers all 21 anchors without claiming RAOM activation or unperformed hardware success.
3. Hardware procedure names exact built package and intended device. Image identity, operation authority, and later acceptance fields remain explicitly pending.
3.1. Required image/authority fields must be complete before any hardware action. TSK-0008 and post-SHOW handoff supply later evidence without blocking offline documentation.
4. Handoff identifies tested package/source/evidence and pending hardware obligations without claiming future QA/RESULT/SHOW/promotion completion.

### TSK-0008 — VERIFY RUNTIME AND LOCKED IMAGE RESTORATION

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0009 |
| 2 | model | high |

**To do**

1. ADD `tests/system/test_reset_monitor.py` and `tests/reset_monitor/package_scenario.sh` for installed CLI, init, rotation, and lifecycle.
2. RUN `./bin/lets sdlc gate unit tests/reset_monitor`. Default gate paths alone do not select new utility tests.
3. RUN `./bin/lets sdlc gate style` on changed Python tests. Run C warnings and shell syntax checks through applicable LETS wrappers.
4. RUN `./bin/lets sdlc gate system --holder ITM-0001` under owned stack lease. Include installed binary and meaningful fault tests.
5. REQUIRE qualified ARM execution environment. Successful x86 tests never prove target ABI/runtime compatibility.
6. ***if*** quarantine or source identity remains unresolved ***then*** STOP this image stage with NOT RUN. Offline tasks remain valid but final delivery stays blocked.
6.1. REQUIRE separately approved recovery/restoration proof before any blocked image access. Inspect exact source identity under shared lock afterward.
6.2. VERIFY source-specific filesystem, rc links, helpers, logrotate/cron, complete dpkg inventory, all managed paths, parent metadata, and ownership before installation.
6.3. REJECT incompatible source topology or incomplete inventory before mutation. Do not assume observed live target equals source image.
7. RUN `./bin/lets sdlc test-package ITM-0001` against qualified source image and exact package under full shared image lock.
8. EXECUTE explicit version-A install, data creation, version-B upgrade, injected failed upgrade, rollback/downgrade, and removal of all delivered packages inside locked scenario.
9. INJECT fixtures through test-only harness. Test persistence/sync errors, crashes, locks, clock changes, and missing history with production override disabled.
9.1. EXECUTE exact target-compatible ARM utility, actual logrotate 3.8.7 hook/compression scenarios, and substituted monit syntax test.
9.2. REQUIRE barrier spans all rotation/compression participants. No host-only substitute qualifies target runtime or hook ordering.
10. COMPARE whole-tree fingerprints plus separate exact `/var/log/scr/` and affected-parent manifest. Cover excluded logs, journal, barrier, rotations, and initially absent paths.
11. VERIFY source hashes/metadata, clean unmount, released loops, and complete scratch cleanup before unlock.
12. PUBLISH commands, exits, runtime identities, package hashes, fingerprints, and limitations as implementation INPUT.
13. VERIFY supplementary log manifest before first install and after final uninstall while same image lock remains held. Include bytes/types/owners/modes/timestamps/links/xattrs.
14. RETAIN explicit package-scenario transcript. Base helper alone does not exercise upgrades. Preserve existing fingerprint exclusions without adding bypasses.

**Done when**

1. Every responsibility has functional evidence, including actual filesystem/rotation behavior and installed ARM-compatible execution.
2. Full lifecycle restores original tree/metadata and preserves source image. Upgrade/rollback evidence identifies exact versions.
3. Restoration/cleanup failure quarantines and fails acceptance. Missing runtime/image gate never becomes simulated success.
4. Retained commands, scenarios, packages, and manifests let independent validator reproduce every task check.
