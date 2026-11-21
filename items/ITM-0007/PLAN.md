# ITM-0007-RAOM-SYSV-STARTUP-SERVICE — Plan

## Goal

Deliver configurable SysV boot gating through existing reset API. Start one MONIT instance with selected safe or normal profile. Ship reversible Debian package.

## Context

1. CHN-0002 position 2 follows DONE ITM-0001. Planning base: `80ddbaf4f0ecc0f3c83b96a0335599ab2ea0dc9f`, branch `feature/monit-stability`, checkout `/home/fudya/devel/scr`.
2. REVIEW D-01–D-03 control scope. Developer: "Built-in true if fails to read its own configuration. CloudFlare is out of this item scope, the client will define what goes into the safe mode monit config".
3. Published planning INPUT: `6a87a78345015cc513a83196da18ee51ea5ea1f53700670efb39234342eaf916`. Ledger locator: `artifacts/bundles/6a87a78345015cc513a83196da18ee51ea5ea1f53700670efb39234342eaf916.json`. Contains `current-decisions.md` and four `target-*.txt` logs.
4. Live evidence: SCR-7CCC91, Linux `3.10.105-imx6`, armv7l, MONIT 5.22.0, reset package 1.0.6. NTP starts through MONIT; watchdog and fallback scripts couple boot to normal MONIT. Inspection proves configuration, not new boot behavior.

## Deliverables

| # | Deliverable | Source requirement | Observable result, owned changes, and supported conditions |
| --- | --- | --- | --- |
| 1 | D1 — Boot decision | Source idea; REVIEW D-01–D-03 | Configurable N/M/K and error policy select one mode per boot through existing API. Missing/invalid configuration uses complete built-in defaults. Errors remain visible. |
| 2 | D2 — MONIT integration | Source idea; D-01/D-03; live boot evidence | Native NTP bootstrap precedes decision. Existing keepalive covers wait. One MONIT uses selected profile across supported start/restart/reload/fallback paths. Minimal safe test profile supervises keepalive only. |
| 3 | D3 — Reversible delivery | Source idea; SDLC image/package rules | Same-package upgrade preserves reset API/history, client configuration, original backups, ownership checks, and exact removal restoration. Operator documentation defines scope and rollback. |

### Behavior for approval

| # | Condition or setting | Required behavior |
| --- | --- | --- |
| 1 | Defaults | `N=5`, `M=900`, `K=60`, `SAFE_MODE_ON_ERROR=true`. N counts resets; M/K use seconds. Client changes production values. |
| 2 | Configuration | `/etc/default/scr-raom` holds numeric settings, boolean flag, `SAFE_PROFILE`, and `NORMAL_PROFILE`. Parse validated data, never execute configuration as shell code. |
| 3 | Configuration unavailable or invalid | Discard partial values. Use complete built-in defaults, including true flag and known safe profile `/etc/monit/raom/safe.monitrc`. Log configuration error. |
| 4 | NTP readiness | Bootstrap native logging/NTP after filesystem/network prerequisites and runlevel stop actions. Start monotonic K at decision entry after bounded native NTP start attempt. Failed bootstrap is error. |
| 5 | Waiting | Poll bounded local NTP readiness until synchronization or K expires. Wall-clock jumps cannot extend deadline. Keep existing `wd_keepalive` active. No normal MONIT starts during wait. |
| 6 | Ready NTP | Call `/usr/bin/scr-resets-monitor check --max-resets N --window M`. Utility alone calculates threshold and refreshes history. No separate counter/window algorithm. |
| 7 | API exit 0 / 1 | Select normal / safe respectively. Threshold strictly greater than N always selects safe, regardless of error-policy flag. |
| 8 | API exit 2, unexpected failure, NTP timeout, filesystem error | True selects safe; false permits normal. Retain error reason; never relabel unavailable evidence as below threshold. |
| 9 | Mode lifetime | Fix mode and selected profile path for current boot. Repeated service starts reuse selection. Reboot reevaluates unchanged reset history. No automatic same-boot return to normal. |
| 10 | Launch | Validate selected MONIT configuration before launch. Missing binary/profile, invalid syntax, or unusable runtime filesystem means explicit failed startup. Never substitute normal after failed safe launch. |
| 11 | Profiles | Default normal path remains `/etc/monit/monitrc`. Safe sample contains only `wd_keepalive` supervision and required MONIT settings; no shared normal includes or reboot handlers. |
| 12 | Client responsibility | Client owns safe-profile contents. Sample is test default, not remote-access service inventory or production RAOM access promise. Existing OS boot services continue without duplicate supervision. |

## Dependencies

1. Consume ITM-0001 CLI at `/usr/bin/scr-resets-monitor`, linked to `/usr/local/scr/bin/src-resets-monitor`. Preserve parser, history, clock, and threshold internals. Test actual CLI integration in disposable fixtures; no live `check` during planning.
2. Consume native `/etc/init.d/ntp`, `rsyslog`, `wd_keepalive`, and MONIT 5.22.0 interfaces. Reuse existing daemons and init operations. Functional watchdog feeding requires later exact-package hardware evidence.
3. Consume existing normal MONIT configuration unchanged. Client profile validity and executable prerequisites constrain launch; client service provisioning and qualification remain outside scope.
4. Evidence lives under `/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0007/planning/`. `docs/MONIT.md` describes historical image 8.26.0 only. Missing dpkg lists do not prove paths unowned.
5. Apply `docs/SDLC-DEVELOPER-GUIDE.md#scope-and-verification`. ITM-0001 D-09 explains current package ownership. Its D-10 image-check waiver does not apply here.

## Design

1. **Fit:** Add small Bash RAOM tool and SysV service. Upgrade existing `scr-resets-monitor` package; retain delivered reset API unchanged.
2. **Patterns:** Reuse central entry point, sourced `tool.sh`, cohesive helpers, native init commands, MONIT `CONFIG` override, and existing Debian build/restoration code.
3. **Context:** Bootstrap NTP outside gated MONIT. Preserve keepalive until selected profile takes over. Route existing MONIT fallback and CLI defaults through selected profile.
4. **Necessity:** Boot selection prevents reset-loop continuation. One boot record prevents mode changes on restart. Scoped compatibility edits close observed bypasses; backup extensions restore newly owned paths.

## Out of scope

1. Cloudflare; client safe-service inventory, provisioning, or qualification; production remote-access guarantees.
2. Reset-monitor algorithm changes, kernel/C work, parallel service supervision, broad MONIT redesign, A/B upgrade framework, or global OS/package-inventory repair.
3. Target installation, restart, reboot, watchdog changes, or hardware acceptance through this planning approval.

## Safety

1. Item hardware-required marker already set. Current planner edits only `/home/fudya/devel/scr/.lets/sdlc/drafts/ITM-0007/PLAN.md`. Preserve coordinator `AGENTS.md` edits and all unrelated work.
2. Delivery: `scr-resets-monitor` 1.1.0, architecture `all`. Same owner avoids second package competing for existing full `src/` payload. ARM target prerequisites still require evidence.
3. Managed additions: RAOM source payload, command link, configuration, sample profile, SysV script and links. Managed compatibility changes: `/etc/init.d/monit`, `/etc/default/monit`, `/etc/monitrc`, `/sbin/monitstate.sh`, and narrow `/etc/rc.local` state-wipe removal. Remove obsolete `S17scr-resets-monitor` hook and competing `S03monit` starts; preserve original bytes and links for restoration.
4. Keep `/etc/monit/monitrc`, MONIT binaries, watchdog binaries/configuration, and client service payload unchanged. Safe sample monitors existing keepalive; normal watchdog retains native takeover.
5. Maintainer scripts preflight managed-path ownership, expected original content, path types, and architecture before mutation. Known foreign owners, version mismatches, unsafe paths, and unresolved managed ownership fail closed. No global inventory repair.
6. Preserve immutable first-install backup. Capture newly managed paths before first modification during upgrade, with separate retained baseline evidence. Do not overwrite historical backups. Preserve history and client edits across supported upgrades.
7. Cover preinst/postinst/prerm/postrm success, aborted install/upgrade, reconfiguration, downgrade to retained 1.0.6/1.0.7, remove, and purge. Remove RAOM additions on downgrade; retain reset history. Maintainer scripts never start services or reboot.
8. Uninstall all delivered packages restores original bytes, types, ownership, permissions, symlinks, hardlinks, timestamps, xattrs, and added/moved/deleted paths. Failed restoration retains recovery evidence.
9. Image acceptance uses identified disposable copies only. Hold shared SDLC image lock across source hashing, copy, mount, install, functional tests, upgrade/rollback, uninstall, whole-tree restoration, unmount, and cleanup. Preserve original `var/` image, kernel archive, and README. Failure quarantines image; no retry bypass.
10. Hardware work needs separate explicit authority, exact device/image/package identities, source/package hashes, commands, expected observations, logs, rollback, and verbatim developer confirmation. No current device actions authorized.

## Verification

| # | Criterion | Test and expected result | Defect detected or affected regression | Acceptance stage |
| --- | --- | --- | --- | --- |
| 1 | D1 defaults/error policy | Config fixtures: valid true/false, missing/unreadable/malformed/partial data. Complete defaults on invalid input; errors visible; no shell execution. | Partial fallback, unsafe configuration execution, unavailable evidence labeled healthy. | TSK-0001 |
| 2 | D1 API decisions | API fixtures 0/1/2/unexpected failure with both flag values. Exact N/M arguments; exit 1 always safe. | Inverted threshold, duplicate algorithm, error-policy bypass. | TSK-0001; actual dependency integration TSK-0004 |
| 3 | D1 bounded boot | Controlled monotonic clock, NTP success/timeout/start failure, clock jumps, repeated start and reboot identity. Fixed deadline and mode; new boot reevaluates. | Indefinite wait, wall-clock dependence, same-boot mode changes. | TSK-0001 |
| 4 | D2 bootstrap/order | Captured SysV fixtures exercise runlevel 2–5 stop/start ordering, native NTP bootstrap, and keepalive continuity. No normal MONIT before decision. | Circular dependency, K02ntp undoing bootstrap, competing watchdog ownership. | TSK-0002; real boot later hardware |
| 5 | D2 profile isolation | Safe selection excludes normal includes/reboot helpers; normal selection retains normal path. Native start/restart/reload, fallback, and default CLI resolve same selection. | Default-profile bypass, second daemon, fallback reboot, rc.local state deletion. | TSK-0002; assembled QA |
| 6 | D2 launch failure | Missing MONIT/profile, invalid syntax, unusable boot-state path, and interrupted selection publication. Explicit failure, no normal fallback or fabricated success. | Mode choice confused with successful launch; incomplete boot record accepted. | TSK-0002 |
| 7 | D3 package lifecycle | Actual disposable dpkg install/reconfigure/upgrade/abort/downgrade/remove/purge; new-path baseline and client edits retained; exact restoration. | Lost original paths, overwritten baseline, obsolete RAOM residue, history loss. | TSK-0003 native lifecycle; locked image acceptance later |
| 8 | D3 conflicts/regressions | Managed foreign owner/version/type and unknown owner fixtures fail before mutation. Build retains full source subtree and existing CLI/logrotate consumers. | Overlap bypass, expanded payload missing from manifest, stale command paths. | TSK-0003 |
| 9 | D1/D2 consumed interfaces | Execute shipped reset CLI with controlled SEMA/NTP/history in disposable root; invoke installed selector and real MONIT syntax validation. | Fixtures hiding CLI or MONIT integration mismatch. No dependency-internal requalification. | TSK-0004; assembled QA |
| 10 | D3 documentation | Examples match shipped settings/profile paths, error reasons, mode lifetime, sample limits, upgrade and rollback. | Client mistaking test sample for production RAOM service delivery. | TSK-0004 |

### Mandatory gates

1. All Bash worker handoffs include full `.agents/skills/bash-style/SKILL.md`; sourced modules never execute automatically. Run `bash -n`, applicable POSIX syntax checks, and focused behavior checks. Use ShellCheck when available.
2. Final independent QA runs `./bin/lets sdlc gate unit` and `./bin/lets sdlc gate system --holder ITM-0007` with required lease. Apply style gate to changed Python paths only, if any. Task fixtures cannot replace final gates.
3. SDLC image/package rules require source hashes, architecture/ownership checks, shared lock, whole-tree restoration including xattrs, and cleanup proof. Execute through `./bin/lets sdlc test-package` and related authorized safety commands. Missing executable image/prerequisite evidence remains pending acceptance.
4. New stage evidence belongs under `.codex/sdlc/artifacts/items/ITM-0007/`. Publish explicit INPUT/RESULT manifests through `./bin/lets sdlc artifacts publish`. Restore/verify through artifact commands; preserve exact bytes, modes, original paths, and historical hashes. No forced Git addition or protected runtime scans.

### Post-task item acceptance

1. Independent validator/QA assesses assembled source and immutable INPUT, including relevant V1–V10 results and mandatory gates. QA publishes separate RESULT for exact `(source_tree, input_digest)`, without self-reference. Historical INPUT is evidence, not current test success.
2. Exact-pair SHOW, verification, approval, settlement, prepare-promotion, and promotion retain explicit `--expected-artifacts DIGEST` for bound contexts. Plan approval never substitutes for SHOW approval.
3. Hardware procedure requires separately authorized install and reboot on identified target/image with exact package hash. Capture normal boot, threshold-safe boot, NTP-timeout/error-policy behavior, repeated service actions, MONIT selection, keepalive continuity, and rollback observations. Use controlled history/test inputs only within explicit authority; never induce physical reset loops without separate approval.
4. Developer confirms exact package result before DONE. Sample acceptance proves selector/keepalive integration only; no client service inventory or Cloudflare acceptance. Retain failed logs and rollback path; automated tests never establish hardware success.

## BLK-0001 — Deliver reversible RAOM boot selection

All file paths below resolve under assigned checkout `/home/fudya/devel/scr`. Subsequent workers receive absolute assigned worktree paths. One block; dependencies stay inside block.

### TSK-0001 — IMPLEMENT CONFIGURABLE BOOT DECISION

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | default |

**To do**

1. ADD `src/bin/src-raom`, `src/tools/raom/tool.sh`, `src/tools/raom/src/decision.sh`, and `src/tools/raom/etc/raom.conf`. Implement `load_config`, `wait_for_ntp`, `select_mode`, and command `main` for D1.
2. REUSE SCR entry-point/loading conventions and shared helpers. Validate N/M against existing API bounds, positive bounded K, boolean flag, and absolute profile paths.
3. IMPLEMENT complete fallback, bounded clock/command waits, exact reset-API call, error reasons, and root-owned boot selection under `/run/scr-raom/`. Publish complete state safely under one invocation lock; reject invalid state without default-normal launch.
4. ADD `src/tools/raom/test/check-decision.sh` for V1–V3. Apply Bash skill; preserve reset-monitor runtime internals.

**Done when**

1. V1–V3 pass with fake clock/API inputs; no host SEMA, history, services, or watchdog access.
2. Defaults, true/false errors, threshold precedence, timer boundary, and boot lifetime match behavior table.
3. Changed scripts pass applicable syntax checks. No repeated threshold algorithm or parallel service supervision.

### TSK-0002 — INTEGRATE SYSV AND SELECTED MONIT PROFILE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | default |

**To do**

1. ADD `src/tools/raom/src/scr-raom.init`, `src/tools/raom/src/monit.sh`, and `src/tools/raom/etc/safe.monitrc`. Implement `bootstrap_ntp`, `start_selected_monit`, and `selected_profile` for D2.
2. DEFINE runlevel 2–5 ordering after native stop actions, mounted storage, network, logging, and `wd_keepalive`, before unrestricted MONIT. Reuse native init starts. Bound bootstrap separately; K begins decision phase after native NTP start attempt.
3. ADD narrow compatibility templates/patches under `src/tools/raom/etc/` for native MONIT init/defaults, CLI default configuration, `monitstate.sh`, and rc.local. Use existing `CONFIG` support; retain native stop/status behavior and selected profile on restart/reload.
4. ROUTE `/etc/monitrc` default CLI configuration to selected runtime profile. Preserve existing `/etc/monit/monitrc` as normal profile. Remove fallback alternate-normal launch/reboot and rc.local state wipe; no general cron rewrite.
5. SHIP keepalive-only safe test profile with explicit MONIT pid/state/log paths and no normal includes or reboot recovery. Leave native OS services alone. Normal profile retains native watchdog takeover.
6. ADD `src/tools/raom/test/check-boot.sh` for V4–V6 using captured init fixtures and harmless command substitutes. Update obsolete observation-hook fixture expectations in `src/tools/resets-monitor/test/check-build.sh`.

**Done when**

1. V4–V6 pass: one selected daemon path, bounded bootstrap, repeated starts reuse mode, and failure cannot launch normal or reboot.
2. Runlevel fixtures cover existing K02ntp/S01wd_keepalive/S03monit/S03rc.local interactions. Safe sample never starts normal watchdog or application checks.
3. Template patches reject unsupported original content. Changed shell files pass syntax checks; POSIX native scripts remain POSIX.

### TSK-0003 — PACKAGE REVERSIBLE STARTUP UPGRADE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | high |

**To do**

1. UPDATE `src/tools/resets-monitor/etc/deb.conf`, `src/tools/resets-monitor/pkg/{control,preinst,postinst,prerm,postrm}`, and `src/tools/resets-monitor/src/package-common.sh` for D3. Set version 1.1.0 and accurate package description/dependencies.
2. EXTEND `PAYLOAD_FILES`, `FILES`, `DIRECTORIES`, `check_managed_paths`, `save_originals`, `install_payload`, `restore_originals`, and `package_main` only for declared RAOM paths/lifecycle. Preserve original baseline and capture newly managed paths before mutation.
3. INSTALL RAOM command/service/configuration/profile and scoped compatibility changes. Replace old observation startup and competing MONIT links. Preserve client configuration/profile edits on upgrade and reset history throughout transitions.
4. SUPPORT clean downgrade to retained previous packages, aborted transitions, remove/purge, and complete restoration. Refuse ownership/content conflicts before mutation. Never activate services from maintainer scripts.
5. EXTEND `src/tools/resets-monitor/test/check-package.sh` and `src/tools/resets-monitor/test/check-build.sh` for V7–V8. Build through `./bin/lets deb build src/tools/resets-monitor/etc/deb.conf`; reuse existing focused package harness.

**Done when**

1. Package builds as `scr-resets-monitor_1.1.0_all.deb`; payload inventory matches full source subtree and declared integration paths.
2. Disposable native dpkg evidence passes V7–V8, including newly owned existing/absent paths, failed upgrade, client edits, history preservation, downgrade, and exact metadata restoration.
3. No service action occurs during lifecycle checks. Unresolved managed ownership fails closed; unrelated missing dpkg lists never trigger OS repair.
4. Task evidence identifies tested package hashes and fixture limits. Final locked-image, QA/RESULT, SHOW, and hardware acceptance remain later stages.

### TSK-0004 — VERIFY CONSUMED INTERFACES AND DOCUMENT OPERATION

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0003 |
| 2 | model | default |

**To do**

1. ADD `src/tools/raom/test/check-integration.sh` for V9. Run installed selector with actual delivered reset CLI in isolated fixtures. Run real supported MONIT syntax checks without starting host daemons.
2. ADD `src/tools/raom/README.md`; UPDATE `src/tools/resets-monitor/README.md`, `docs/DEVELOPER-GUIDE.md`, and relevant `docs/MONIT.md` integration references for V10. Keep historical image statements labeled historical.
3. DOCUMENT D1–D3, defaults, configuration validation, monotonic deadline, fixed boot mode, error-vs-launch failure, client-owned profiles, minimal sample limits, package migration, and rollback. Do not promise client remote services.
4. PREPARE exact-package acceptance procedure and evidence index under managed artifacts. Record scoped checks, source/package hashes, consumed-interface limits, and pending mandatory image/hardware stages. Publish through LETS during authorized implementation.

**Done when**

1. V9 executes actual dependency interfaces; fixtures do not masquerade as hardware results. Unsupported MONIT execution blocks this criterion rather than producing synthetic success.
2. V10 documentation matches package paths and behavior. Previous item references no longer imply observation-only startup for upgraded package.
3. Independent task validation can assess focused results without requiring final QA RESULT, SHOW, promotion, or developer hardware confirmation.
