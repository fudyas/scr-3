# ITM-0001-BASH-RESET-MONITOR-DEBIAN-PACKAGE — Plan

## Goal

Deliver RAOM steps 1 and 2: Bash BMC reader, durable history, decision API, reversible Debian package. Explicit threshold/window arguments; exits 0/1/2.

## Context

1. Developer: "Retain API, the scope of the item is the same - 1+2 of RAOM". All 21 responsibilities remain.
2. D-04 replaces rejected implementation. D-01 removes rotation-specific tests. D-03 excludes global OS inventory work.

## Deliverables

| # | Deliverable | Source requirement | Observable result, owned changes, and supported conditions |
| --- | --- | --- | --- |
| 1 | D1 — Observation/history | Brief responsibilities 2–15, 20–21 | Bash `/usr/sbin/scr-resets-monitor record` reads `/usr/bin/sema cap all`, validates observations, commits JSONL history and latest state, reports failures without false resets. |
| 2 | D2 — Decision API | Brief responsibilities 16–18 | `status --json` reports committed observation, age, validity. `check --max-resets N --window SECONDS` refreshes and returns 0/1/2 with explicit arguments and conservative history evidence. |
| 3 | D3 — Native integration | Brief responsibilities 1, 5–6, 19, 21 | SysV observation after writable log storage, owned restricted logs, disabled monit example, system rotation stanza, concise operator contract. No service-control policy. |
| 4 | D4 — Debian delivery | D-04 and brief Delivery 1–6 | Small LETS build command plus `src/resets-monitor/{scripts,etc,src}` sources. Ignored `build/resets-monitor/` staging and `.deb` output. Reversible install, upgrade, rollback, removal. |

## Dependencies

1. ITM-0006 supplies completed workflow prerequisite. Consume public SDLC package/image/artifact commands. Do not redesign their internals.
2. Existing SEMA supplies fixed read-only `/usr/bin/sema cap all` output. Retained `planning/replan-20261112/target-*.log` supplies command/profile facts. Actual delivered execution remains later acceptance.
3. Existing Bash, GNU coreutils, util-linux `flock`, gzip, and `/usr/bin/ntpq` supply runtime interfaces. No target LETS, Python, compiler, toolchain, jq, or new compiled helper.
4. Existing `ntpq -c 'rv 0'` supplies clock-health fields. Retained successful output proves interface existed. Missing or unreliable current health invalidates time decisions.
5. GNU `dd conv=fsync` supplies checked file synchronization. Directory-descriptor synchronization requires actual target-compatible execution before package acceptance. Host-only probe proves no target result.
6. Native SysV and system logrotate own startup ordering and rotation policy. Consume observed `S16bootmisc.sh` boundary and existing rotation configuration. Do not qualify unrelated services or scheduler internals.
7. Build host consumes LETS command discovery, rsync, and `dpkg-deb`. Target package consumes existing dpkg. Missing required interface blocks affected delivery, never authorizes dependency repair.
8. Exact source-image identity, available safe disposable execution, and operation-specific hardware authority remain later acceptance prerequisites. No image/device work occurs during planning.

### Planning facts

1. Developer: "The userspace utility is a bash script that parses the BMC output, no C code needed, no toolchain".
2. Canonical source: `.codex/sdlc/artifacts/items/ITM-0001/planning/bash-restart-20261112/{customer-source.txt,brief.md}`. Customer source stays verbatim. Brief's 21 responsibilities remain acceptance anchors.
3. Effective REVIEW D-04 discards previous implementation and approval. D-01 removes rotation-specific tests. D-03 excludes global OS inventory repair/qualification.
4. Retained target evidence identifies Bash 4.3, SEMA 2.5 R4, SysV, `flock`, `timeout`, `ntpq`, gzip, and logrotate 3.8.7. Evidence describes SCR-7CCC91, not new-package acceptance.
5. Base checkout: `/home/fudya/devel/scr`, `feature/monit-stability`, `f66ffbda7e0f14618e044ddde2047dfc36980302`. Source tree: `fc33411eafea319e4dbeda49bd7ea2a02137875c`. ITM-0006 remains DONE dependency.
6. Existing source has no reset-monitor implementation or `tools/deb/build.sh`. Rejected plans/packages/tests remain historical evidence only. Current modified SDLC guide supplies contract.
7. Build command: `./bin/lets deb build src/resets-monitor/etc/deb.conf`. Separate hardware acceptance remains required.
8. Developer: "Since you have a full ssh access, you can automate the test and don't wait for me. I'll give the machine IP when you're ready". Agent owns authorized target execution once IP arrives.

## Design

1. **Fit:** One Bash utility; SysV calls `record`, disabled monit example calls `check`.
2. **Patterns:** Reuse LETS shell style, native SysV, system rotation, `flock`, and reversible-package principles.
3. **Context:** Brief/REVIEW define behavior; `docs/MONIT.md` supplies service context; SDLC guide governs acceptance.
4. **Necessity:** Journal, state cache, lock, and checked synchronization protect committed observations. Interval decisions avoid invented reset times. Small rotation marker prevents races; backups restore originals.

## Out of scope

1. C/kernel/toolchain work, compiled helpers, target development runtime, and separate transaction framework.
2. RAOM activation, boot/service/watchdog control, BMC writes, firmware changes, and agent-operated reboots.
3. Private rotation scheduler, production defaults, global OS qualification, unrelated monit changes, and retired SDLC recovery.
4. Source-image mutation, implicit hardware authority, and acceptance of rejected implementation.

## Runtime contract

1. Source utility: `src/resets-monitor/src/scr-resets-monitor`. Use LETS shell conventions: clear functions, `main`, explicit failures, quoted arguments. Runtime never sources development LETS.
2. Commands remain exactly `record`, `status --json`, and `check --max-resets N --window SECONDS`. Reject duplicate, missing, unknown, or malformed arguments before device access.
3. Counter capacity: decimal `0..4294967295`. This is parser capacity, not claimed firmware width. Reject larger values, signs, fractions, and arithmetic overflow.
4. CLI capacity: `N` is decimal `0..2147483647`; `SECONDS` is decimal `1..2147483647`. Normalize decimal safely. Guard arithmetic; saturate decision sums above N.
5. Query only `/usr/bin/sema cap all` under `LC_ALL=C`. Two attempts maximum, two seconds each, bounded termination handling. Limit captured output to 64 KiB and text fields to 256 bytes.
6. Require success and complete unique observation fields. Distinguish capability `Boot counter`/`Restart event` from observation `Boot count`/`Restart event`. Unknown cause text remains diagnostic data.
7. Record schema version, sequence, observation time, time validity/reason, uncertainty, Linux boot ID, uptime, BMC serial/identity, firmware, both counters, both deltas, and latest cause.
8. JSON uses explicit escaping and fixed versioned schema. Parse own records as data, never `source` or `eval`. Reject malformed/truncated records and unsupported schema.
9. Initial record establishes baseline with zero new resets. Changed boot count and power cycles produce separate deltas. Decision count uses boot-count delta only; never double-count power cycles.
10. Delta greater than one remains one aggregate interval. Latest cause describes latest event only. Unchanged counters create no reset event; repeated identical observation creates no duplicate record.
11. Counter decrease, changed BMC identity, or changed firmware commits explicit discontinuity and fresh baseline epoch. Preserve previous history. Infer no rollover. Windows crossing discontinuity return 2.
12. Root-owned `/var/log/scr/` uses mode 0700; owned history/state/diagnostic files use 0600. Preserve unrelated files. Reject unsafe path types and symlink traversal.
13. `/var/log/scr/resets.jsonl` is authoritative history. `/var/log/scr/resets-state.json` caches latest committed observation. `/var/log/scr/resets-monitor.log` records failures and recovery.
14. Stable `/run/lock/scr-resets-monitor.lock` serializes reads, commits, and recovery. Bound lock wait to two seconds. Open current paths each invocation.
    14.1. Shipped stanza uses small Bash `rotation_begin`/`rotation_end` hooks under same lock. Begin durably creates `/var/log/scr/.rotation-pending` before any rename/compression.
    14.2. Marker records rotating logrotate process identity (boot ID, PID, start time) and last committed sequence. Existing marker or failed marker synchronization aborts rotation.
    14.3. Every utility invocation checks marker under lock before journal access. Marker present means exit 2 and stderr diagnostic. No journal replacement during rotation.
    14.4. End clears marker only for matching invocation after rotation/compression completes, retained history preserves committed sequence, and changed history/directory synchronization succeeds.
    14.5. Interrupted or uncertain completion leaves marker intact. Never clear by elapsed time, PID absence, or automatic reboot recovery. Document explicit operator recovery under lock after proving quiescence and valid durable history.
15. Hold lock from marker check and history read through complete journal publication and cache update. Publish via same-directory temporary file, checked file synchronization, rename, then checked directory synchronization. Update state cache only after journal commit.
16. Rebuild missing/stale state from validated durable journal. Interrupted pre-rename files never advance baseline. Uncertain post-rename state requires successful synchronization before adoption.
17. Cache failure after durable journal commit returns 2. Journal remains last committed truth; retry rebuilds cache without repeating delta. Failure before durable history leaves earlier baseline authoritative.
18. Torn/corrupt/conflicting history fails closed with evidence preserved. Never overwrite unexplained corruption or advance baseline past missing durable records.
19. Full/read-only storage, permission errors, failed writes/renames/synchronization, and lock timeout return 2. Use stderr and existing system logger when diagnostic log cannot accept writes.
20. `record` returns 0 after successful commit/cache recovery, otherwise 2. `status --json` does not query BMC. Return valid JSON, latest committed data, age or null, validity/reason, and 0 or 2.
21. Read wall time, `/proc/uptime`, boot ID, and bounded local `ntpq -c 'rv 0'` around acquisition. Missing/malformed/unsynchronized clock health marks time invalid but does not discard valid counters.
22. Require `leap_none`, `sync_ntp`, finite valid uncertainty fields, and current reference age within four reported poll intervals. No clock setting, NTP wait, or daemon-presence inference.
23. Round uncertainty upward from root dispersion, half absolute root delay, absolute offset, acquisition duration, and clock resolution. Same-boot wall/uptime disagreement invalidates continuity.
24. Cross-boot intervals require trustworthy time anchors on both sides. Invalid-time intermediate records can use valid outer anchors within same BMC epoch. Current synchronization never validates old timestamps retroactively.
25. Window is `(now - SECONDS, now]`. Compute lower/upper reset counts from complete observation intervals and uncertainty. Partial intervals contribute only to upper count; never assign individual event times.
26. `check` returns 1 only when reliable lower count exceeds N; returns 0 only when complete valid coverage proves upper count at most N. Otherwise return 2.
27. Read/persistence failure always returns 2, even with earlier threshold evidence. Missing history, retention gaps, corruption, discontinuity, and unusable time cannot produce healthy result.
28. Consume retained plain/gzip history when needed. Collapse identical sequence records across files; reject missing/conflicting sequence evidence. System rotation owns retention; state cache and rotation marker are never rotated.
29. Production runtime accepts no arbitrary command/backend override. Focused checks source named functions or use isolated installed roots with controlled dependency fixtures.

## Safety

1. Hardware-required marker remains mandatory before approval. Developer separately authorized agent SSH package testing once IP arrives. No repeated permission for listed target checks. Historical SCR-7CCC91 identity does not select target. Reboots, physical resets/power cuts, firmware, and watchdog actions remain outside this authority.
2. Package owns utility, `/etc/init.d/scr-resets-monitor`, `/etc/rcS.d/S17scr-resets-monitor`, `/etc/logrotate.d/scr-resets-monitor`, disabled example, and `/usr/share/doc/scr-resets-monitor/`.
3. Disabled example source remains `src/resets-monitor/etc/monit-example.conf`; install under `/usr/share/doc/scr-resets-monitor/`. No `/etc/monit` changes, enabled link, reload, service start/stop, watchdog change, or reboot command.
4. Inventory every touched path: private payload, backups, owner markers, runtime files, rotation marker/helper, temporary files, SysV link, created directories, and affected parents. Preserve SEMA and unrelated files.
5. Reuse compatible backup/restoration principles and helpers from `SdlcPackageHelper.cmd_package_init`. Author required `src/resets-monitor/scripts/` layout directly. Do not generate legacy central package tree or parallel packaging sources.
6. `scripts/{control,preinst,postinst,prerm,postrm}` provide package metadata and lifecycle. Keep runtime payload under private package path until originals are preserved.
7. `preinst` rejects known dpkg conflicts, other SDLC owners, unsafe types/ancestors, and unresolved ownership of affected existing paths. Missing unrelated package lists do not require global inventory repair.
8. Preserve first-install originals and absence markers before mutation. Retain bytes, type, uid/gid, permissions, symlinks, hardlinks, timestamps, and xattrs. Preserve parent metadata.
9. `postinst` installs only declared payload and hook. Create owned runtime paths with saved original metadata. Never start observation during package configuration.
10. Upgrade preserves committed history, baseline, original backups, and idempotent startup. Failed/interrupted configuration and abort-upgrade must leave recoverable old or new package state.
11. `prerm` prevents new item invocations during removal. `postrm` restores original managed paths and removes package-created paths/markers on remove/purge/abort-install. Upgrade callbacks must not restore originals prematurely.
12. Uninstall all delivered packages restores original image payload and metadata. Export new logs as managed evidence before removal. Runtime data preservation applies across upgrades, not an exception to uninstall restoration.
13. Hold shared SDLC image lock across source checks, disposable copy, mount, install, functional checks, upgrade, rollback, uninstall, restoration, unmount, cleanup, and unlock.
14. Preserve original `var/` image, kernel archive, README, bytes, and metadata. Ordinary leases never replace image lock. No source-image mutation or protected sibling scans.
15. Retain architecture, root-scoped dpkg, ownership overlap, source hashes, whole-tree fingerprints, xattrs, active-mount, and cleanup checks. Package `Architecture: all` contains scripts only; target helper compatibility still requires proof.
16. Existing fingerprint excludes `/var/log`; capture separate exact before/after manifest for owned logs and affected parents under same lock. Do not broaden exclusions.
17. Cleanup/restoration failure quarantines image and halts reuse until approved recovery proves restoration. Three failures at same stage, tooling blocker, or safety failure halt affected work.

## Verification

D-01 excludes rotation-specific tests and old harnesses. Review shipped stanza, shared-lock/marker protocol, interruption refusal, ownership, state exclusion, current-path opening, and retained-history code directly. Do not claim removed tests passed.

| # | Deliverable criterion | Test and expected result | Defect detected or affected regression | Acceptance stage |
| --- | --- | --- | --- | --- |
| 1 | D1 valid read, R2–4/R7/R21 | Captured SEMA fixture parses correct fields; missing/duplicate/negative/overflow/oversized/nonzero/timeout inputs return 2, previous baseline intact. | Capability/observation confusion, false zero, command injection, unbounded boot work. | TSK-0001 |
| 2 | D1 durable history, R5–15/R20 | Initial totals produce zero delta; 146→147 produces one; aggregate 146→150 produces four; unchanged/repeated/concurrent calls do not duplicate reset delta. | Lifetime-count inflation, lost/duplicate reset events, mistaken rollover. | TSK-0001 |
| 3 | D1 persistence, R12–14 | Inject failure before journal publication, during synchronization, and after journal commit before cache. Retry preserves committed record exactly once. | Cache ahead of durable history, ignored I/O failure, crash duplication. | TSK-0001 |
| 4 | D1 failures, R14–15 | ENOSPC/read-only/permission errors return 2 with stderr fallback. Identity/firmware/decrease records break continuity and preserve evidence. | False healthy status, silent rebaseline, lost diagnostic evidence. | TSK-0001 |
| 5 | D2 CLI, R16–17 | Missing/duplicate/invalid flags rejected; JSON parses; explicit N/window required; exact N yields 0, N+1 yields 1 with complete evidence. | Argument defaults, off-by-one threshold, invalid JSON, status/device side effects. | TSK-0002 |
| 6 | D2 evidence, R11/R18 | Complete intervals prove 0/1; boundary-straddling delta, insufficient coverage, failed refresh, clock jump/unsync, or discontinuity yields 2 when decision unprovable. | Invented event times, stale read accepted, history gap treated as zero. | TSK-0002 |
| 7 | D3 startup, R1/R21 | Isolated SysV invocation launches bounded observation after declared storage boundary and returns without waiting. No service/reboot/watchdog commands. | Boot gating, delayed watchdog servicing, accidental recovery policy. | TSK-0003 |
| 8 | D3 integration, R5–6/R12–13/R19 | Source/config review confirms shared-lock/marker protocol, refusal on interrupted rotation, restricted logs, state/marker exclusion, documentation-only monit example, and history consumer. No rotation test. | Journal/rotation race, lost or duplicate committed delta, active monit policy change, private scheduler, retention promise without coverage. | TSK-0003 |
| 9 | D4 build | Actual LETS build with rsync fixtures preserves file/directory trailing-slash mapping, exclusion, modes; outputs valid script-only `.deb` under build/. | Wrong package layout, stale staging, glob expansion, unintended source copy. | TSK-0003 |
| 10 | D4 lifecycle | Controlled disposable-root install/reconfigure/upgrade/failed-upgrade/rollback/remove/purge checks preserve history during upgrade and exact original payload on removal. | Backup replacement, ownership collision, unsafe path traversal, upgrade callback deletion, metadata loss. | TSK-0004 |
| 11 | D1–D4 consumed target interfaces | Execute delivered Bash with target-compatible timeout/flock/dd file+directory synchronization and retained SEMA profile. Device values remain fixture-driven outside authorized hardware. | Host-only assumptions, unsupported shell/helper options, false durability claim. | Final independent QA, locked disposable image |
| 12 | D4 whole-image safety | Locked exact-package install/use/upgrade/rollback/uninstall produces matching original fingerprints plus log manifest and unchanged source hashes. | Undeclared path writes, restoration gaps, xattr loss, unsafe cleanup. | Final independent QA, locked disposable image |
| 13 | D1–D4 actual target behavior | Agent runs exact-package SSH stage on supplied IP: real BMC reads, API/log checks, upgrade, rollback, removal, and original-path restoration. Report actual exits and pending physical cases separately. | Target-only incompatibility, lost upgrade history, failed rollback/restoration. | Automated target test after SHOW |
| 14 | D4 target runner | Focused simulated SSH outcomes prove hash/identity mismatch refusal, timeout/connection-loss stop, evidence capture, and no blind mutation retry. | Wrong package/device, duplicate install after uncertain result, unsupported success claim. | TSK-0004 |

### Mandatory gates

1. Current SDLC guide requires independent task validation, final `./bin/lets sdlc gate unit`, and `./bin/lets sdlc gate system --holder ID`. Run changed Python style gate only if Python changes exist.
2. Item checks stay under `src/resets-monitor/scripts/`; expose via small `tools/deb/test.sh` LETS wrapper. Use fixtures and shell checks, not new test framework or compiled helper.
3. Final QA retains `./bin/lets sdlc test-package` and applicable `verify-package` checks, including source preservation, architecture, ownership, restoration, and cleanup.
4. Lifecycle tests supplement existing package helper; base install/remove check does not prove upgrades. Full image-lock window and supplementary log manifest remain mandatory.
5. Task checks prove assigned criteria only. No task Done-when depends on final QA, RESULT, SHOW, promotion, hardware authority, or physical success.

### Post-task item acceptance

1. Independently validate block, assemble integration, and retain exact final `.deb` version/hash. Rebuild and repeat affected checks after payload/documentation changes.
2. Stage evidence belongs under `.codex/sdlc/artifacts/items/ITM-0001/`, with explicit purpose/stage. Coordinator publishes selected INPUT manifests through public artifacts commands.
3. Restore/verify immutable bundles with exact bytes/modes/paths/historical hashes. Old QA can be INPUT; it never accepts replacement Bash implementation.
4. Independent detached QA verifies exact source tree and INPUT digest, including mandatory repository and locked image gates. QA publishes separate bound RESULT without self-reference.
5. SHOW presents source tree, INPUT/RESULT digests, full diff, final package hash, evidence, rollback, and pending hardware acceptance. Explicit approval binds exact pair.
6. Verified/approve/settle/prepare-promotion/promote use explicit `--expected-artifacts DIGEST`. Missing index cannot downgrade existing bundles to source-only.
7. Agent prepares target execution with supplied IP, verified device/image identity, BMC/firmware, exact package version/hash, expected results, logs, and rollback package/path.
8. Agent executes automated target stage below under existing SSH test authorization. Do not wait for developer to run installation, BMC/API/log checks, upgrade, rollback, or removal.
9. Developer-operated resets/power loss require explicit procedure and authority. Record before/after counters, boot IDs, expected/observed output, persistence, and supported reset modes.
10. Actual SSH evidence proves only observed device behavior; injected fixtures prove software cases only. Missing boot/reset/power-loss evidence stays pending. Final hardware acceptance requires developer confirmation, retained verbatim through `hardware pass|fail` with exact package.
11. Item remains REVIEW until required developer confirmation. Changed package requires fresh affected QA, SHOW, and hardware acceptance.

### Automated target test — agent execution

1. **Owner:** Agent. Execute after exact-package local/image checks and SHOW, once developer supplies machine IP. Existing authorization covers listed SSH checks without another permission request.
2. VERIFY SSH host identity, device/image identity, exact package hashes, privileges, and retained rollback package/backups. Scope inspection to delivered paths and consumed interfaces.
3. CAPTURE original managed-path bytes/metadata, package state, BMC identity/counters, boot ID, clock validity, and logs. Preserve unrelated target files and local `var/` originals.
4. TRANSFER checked packages and small Bash runner payload through SSH. Compare remote hashes before installation. Identify every upgrade/rollback version; use no rejected C package.
5. INSTALL package and execute actual `/usr/bin/sema cap all`, `record`, `status --json`, repeated/concurrent reads, and `check` with explicit N/window. Compare logs and observed counters; expect no duplicate reset delta.
6. EXECUTE observation hook directly and inspect installed startup ordering without reboot. This proves hook execution, not boot-time or reset persistence.
7. EXERCISE upgrade, rollback, removal, and cleanup with previously checked package versions. Expect preserved committed history across upgrades and restored original owned payload/metadata after removal.
8. RECORD commands, stdout/stderr, exits, times, source/package hashes, expected/observed results, and before/after manifests. Export evidence under `.codex/sdlc/artifacts/items/ITM-0001/` before cleanup.
9. KEEP fixture failures/threshold scenarios separate from real BMC observations. Never inject invented counters into live history or claim exits 0/1/2 physically exercised without observations.
10. BOUND SSH connection and command waits. Retain remote operation identity/status and backups across disconnect. ***if*** timeout or SSH loss occurs ***then*** stop dependent mutations and inspect operation/package state after reconnect. Never blindly retry install or kill package manager.
11. RESTORE through recorded item rollback/removal once operation state is known. Verify original managed paths, metadata, package state, and cleanup. ***if*** connection or restoration remains unavailable ***then*** retain evidence/backups and report blocked recovery; never claim restoration.
12. KEEP D-01 rotation-test exclusion. Physical reset/power-cut cases require separate procedure/authority and developer action. No firmware/watchdog change or reboot. Final developer confirmation remains after automated results.

## BLK-0001 — DELIVER BASH RESET MONITOR PACKAGE

One block owns runtime, small checks, package, and operator documentation. No cross-block dependencies. Paths below are relative to assigned implementation worktree.

### TSK-0001 — IMPLEMENT BMC OBSERVATION AND DURABLE HISTORY

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | default |

**To do**

1. ADD `src/resets-monitor/src/scr-resets-monitor` functions `main`, `read_bmc`, `parse_bmc`, `read_clock`, `load_history`, `commit_observation`, and `write_diagnostic` for D1.
2. IMPLEMENT Runtime contract 3, 5–19, 21–24 and responsibility 20 upgrade-readable schema. Use fixed versioned JSON records and one authoritative journal.
3. ADD `src/resets-monitor/scripts/check-runtime.sh` and small captured-output fixtures under `scripts/fixtures/`. Map cases to Verification 1–4.
4. DOCUMENT schema, numeric capacity, commit/recovery rules, and clock limits in `src/resets-monitor/README.md`. Mark unverified target synchronization explicitly.

**Done when**

1. Verification 1–4 pass with real Bash/shell file operations and focused injected failures. Source review confirms fixed read-only SEMA command and bounded access.
2. Failure at baseline 146 with reading 147 leaves no lost increment. Successful retry records one delta and repairs cache without duplicate committed record.
3. Host file/directory synchronization behavior is exercised through delivered code. Report distinguishes host evidence from pending target-compatible acceptance.
4. Source/check scripts pass `bash -n`; README matches actual schema/recovery behavior. No compiler, target Python, or new runtime framework.

### TSK-0002 — IMPLEMENT STATUS AND WINDOW DECISIONS

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | default |

**To do**

1. EXTEND `src/resets-monitor/src/scr-resets-monitor` with `parse_args`, `show_status`, and `check_window` for D2 and Runtime contract 2, 4, 20, 25–29.
2. ADD focused API/history fixtures to `src/resets-monitor/scripts/check-runtime.sh`. Map cases to Verification 5–6, including boot-count-only thresholds and separate power-cycle diagnostics.
3. UPDATE `src/resets-monitor/README.md` with exact arguments, JSON fields, 0/1/2 meanings, age/validity, uncertainty, and unavailable examples.

**Done when**

1. Verification 5–6 pass; prior Verification 1–4 still pass for shared runtime functions.
2. No explicit threshold/window means rejection. Complete exact-boundary fixtures distinguish N from N+1. Partial evidence never invents event timestamps.
3. `status --json` uses committed data without BMC read; failed `check` refresh cannot return 0 or 1. CLI/help and README agree.

### TSK-0003 — BUILD DEBIAN PACKAGE AND NATIVE INTEGRATION

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | default |

**To do**

1. ADD `tools/deb/build.sh` functions `lets_info`, `lets_usage`, `main`, and small mapping validation. Reuse `tools/codex/build.sh` style for D4.
2. SOURCE trusted `src/resets-monitor/etc/deb.conf` containing `INCLUDE_FILES` and `EXCLUDE_FILES`. Accept local `source:destination` entries with whitespace-separated mappings; reject malformed/remote mappings.
3. PRESERVE rsync trailing-slash semantics and literal exclusion patterns. Restrict destinations/cleanup to dedicated staging below build/. Reject unsafe destination ancestry and source/staging overlap.
4. STAGE fresh package under `build/resets-monitor/`; emit `.deb` under ignored build/. Preserve unrelated build outputs. No generated sources enter Git.
5. ADD `src/resets-monitor/scripts/{control,preinst,postinst,prerm,postrm,scr-resets-monitor.init}` and `etc/{deb.conf,logrotate.conf,monit-example.conf}` for D3/D4. Add small `src/rotation-hooks` Bash helper installed under `/usr/lib/scr-resets-monitor/`.
6. IMPLEMENT Safety 2–12 through declared path inventory, private payload, durable original backups, conflict checks, upgrade branches, and exact restoration.
7. INSTALL asynchronous SysV record hook after observed `S16bootmisc.sh`, preserving existing watchdog/monit ordering. Install disabled monit example under `/usr/share/doc/scr-resets-monitor/`, with explicit threshold placeholders.
8. IMPLEMENT Runtime 14.1–14.5 through `rotation_begin`/`rotation_end` and stanza firstaction/lastaction hooks. Use rename/create with `nocopytruncate`; inherit system schedule/size/retention policy. Keep marker outside rotation and document bounded refusal/recovery. No global wrapper, private scheduler, or rotation-specific tests.
9. ADD `src/resets-monitor/scripts/check-build.sh` for Verification 7–9 and `tools/deb/test.sh` as thin LETS entry to item checks.
10. UPDATE `src/resets-monitor/README.md` with build/config mapping, installation paths, startup, dependencies, rotation boundary, and operator commands.

**Done when**

1. Verification 7–9 pass. Exact command `./bin/lets deb build src/resets-monitor/etc/deb.conf` emits inspectable script-only Debian package under build/.
2. Package inventory contains declared payload, correct modes/ownership, scripts, disabled example, and documentation. No C/compiler/toolchain/LETS/Python runtime payload.
3. Source review confirms D-01/D-03 boundaries, no enabled monit policy or recovery actions, and no undeclared outside-staging build writes.
4. Package scripts pass shell syntax checks. Focused runtime/API checks still pass for packaged runtime bytes.

### TSK-0004 — VERIFY PACKAGE LIFECYCLE AND COMPLETE HANDOFF

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0003 |
| 2 | model | default |

**To do**

1. ADD `src/resets-monitor/scripts/check-package.sh` with controlled disposable-root lifecycle cases for D4, Verification 10, and Safety 4–12.
2. EXERCISE install/reconfigure, history-preserving upgrade, failed/aborted upgrade, rollback, remove/purge, known conflicts, unsafe types, and pre-existing/unrelated files.
3. COMPARE original owned payload, path absence, parent metadata, links, hardlinks, xattrs, and ownership after removal. Preserve lifecycle transcripts outside product tree.
4. UPDATE `src/resets-monitor/README.md` with installation/rollback procedure, limitations, exact-package hardware handoff fields, and separately authorized expected/observed cases.
5. REBUILD final package through LETS. Record version, architecture, SHA-256, source revision, focused-check results, and pending final image/hardware obligations.
6. PREPARE implementation INPUT evidence under `.codex/sdlc/artifacts/items/ITM-0001/implementation/`. Coordinator owns explicit manifest publication and later bound acceptance.
7. ADD simple `src/resets-monitor/scripts/check-target.sh` with `main`, `run_remote`, `capture_evidence`, and `restore_target` for automated target stage. No framework or target LETS/Python dependency.
8. COVER Verification 14 through focused SSH command fixtures. Document runner arguments, timeouts, recovery, and actual-versus-injected evidence in `src/resets-monitor/README.md`.

**Done when**

1. Verification 10 passes on controlled disposable root; all item checks pass through LETS test entry. No host or original-image installation occurs.
2. Upgrade preserves committed history and first-install backups. Removal restores originals exactly, removes package-created paths, and preserves unrelated data.
3. Final package version/hash matches inspected payload and current documentation. Transcript names actual checks, failures, and pending target/image/hardware acceptance separately.
4. Agent target/rollback procedure is actionable with pending IP/device/image fields and recorded SSH authority. Verification 14 passes; runner awaits actual target stage. No task criterion requires target availability, final QA/RESULT/SHOW/promotion, or hardware confirmation.
