# ITM-0008-RAOM-SAFE-RECOVERY-AND-WATCHDOG — Plan

## Goal

Give administrators one command, `scr-raom switch <mode>`, to request a protected reboot into safe or normal mode. Keep safe mode across reboots. Recover without counting acknowledged resets again. Protect MONIT with the full native watchdog in both modes.

## Context

1. CHN-0002 position 3. ITM-0001 and ITM-0007 are DONE. Target `feature/monit-stability` at `c5c580ef40b0dfc74b43f56ac11ca1686892e440`. ITM-0008 is BACKLOG, revision 0, hardware-required.
2. Authoritative wording and rulings are in `./bin/lets sdlc items show ITM-0008`, sections 1–20 and verbatim idea. “Switching between modes means rebooting the system”. Asked whether unreadable or unsavable counters must keep safe mode and refuse reboot, developer replied “Yes, refuse reboot”.
3. Developer requested “I want you to update the RAOM readme with the final algorithm, the switching commands and the NTP caveat as part of item 8”. Preserve the existing README algorithm and numbering when revising them. Root release notes use product release 3.0.2.
4. ITM-0007 REVIEW D-03/D-04/D-07/D-08/D-11 establish client inventory ownership, native dpkg delivery, verified feeder handoff, the keepalive-only sample, and historical hardware limits. This item changes the sample and recovery policy.
5. Developer correction: “Confirm the reboot caused by mode switch IS NOT counted towards resets to check against the threshold UNLESS the counter of BMC resets incrmented by more than 1”.

## Deliverables

| # | Deliverable | Source | Observable result and ownership |
| --- | --- | --- | --- |
| 1 | D1 — Reboot requests and persistent mode | §§2, 7, 14–16, 18–20 | A root caller can request only the opposite of a valid current-boot selection. Safe persists after any entry. Recovery requires a durable counter acknowledgment. |
| 2 | D2 — Reset decision after recovery | §§3–4, 8, 16, 19–20 | Exclude the acknowledged episode. For either identified switch reboot, exclude an observed +1 only. A larger increase stays fully eligible. Preserve raw history and window/error rules. |
| 3 | D3 — Protected MONIT startup | §§5–7, 10, 17 | Both profiles activate the full watchdog after verified MONIT startup. MONIT supervises client services. Keepalive covers protected gaps. |
| 4 | D4 — Reversible unified package | §§9–11, 16 | Proposed `scr-raom_1.1.1_all.deb` delivers both commands. Native dpkg covers install, upgrade, downgrade, remove and purge. |
| 5 | D5 — Operator and release documentation | §§9, 17–18, 20 and root AGENTS release rule | README procedures, diagrams, Structured English algorithm, API references and planned release notes agree with installed behavior. |

## Dependencies

1. Reset monitor owns SEMA reads, locked journal/cache commits, rotation and conservative time-window decisions. Existing `record` has no machine-readable return record. `status --json` reads cached history. Existing `check` accepts only threshold and window. D2 extends only the missing interfaces.
2. RAOM owns operator requests, persistent mode and boot selection. Native SysV owns reboot/shutdown. Existing MONIT adapters, process identity checks, native watchdog and keepalive perform handoffs. Use the supported native reboot command with fixed arguments. Tests substitute it only inside isolated fixtures.
3. Historical SCR-7CCC91 evidence records image 8.26.0, Debian 8.7, armv7l, MONIT 5.22.0, watchdog PID check and `/sbin/monit-status.sh`. The script checks `service monit status`. Its native status path is lock-free. No captured normal-service dependency requires replacing that script.
4. Client owns safe/normal MONIT service definitions and normal profile. Preserve customized conffiles. A retained 1.1.0 safe stanza can call `/etc/init.d/wd_keepalive start` after full watchdog activation. The captured keepalive init starts its binary without checking for full watchdog. Cover that native entry. Client scripts that bypass native init and open the hardware device directly exceed the supported interface.
5. Evidence roots under `.codex/sdlc/artifacts/items/ITM-0007/` are `planning/` and `implementation/hardware-package-layout/`. Retained `scr-raom` 1.1.0 SHA-256 is `216f0177e56c7212d833b457b364471f8d6556f9aed3e63850659ed0d2cd306b`. D-11 waived one synchronized-threshold hardware case for those bytes only.

## Design

1. **Fit.** Keep mode, reset arithmetic and service supervision with RAOM, reset monitor and MONIT respectively. Route SysV startup and decision-only `select` through the same persistent decision rules.
2. **Patterns.** Reuse `prepare_state`, `load_selection`, `publish_selection`, shared root/logging helpers, validated reset records and native service adapters. Keep runtime paths in trusted configuration.
3. **Context.** Keep the running selection boot-scoped. Keep the safe latch, recovery acknowledgment and one pending switch in the existing planned durable record. Bind counter observations to the source and destination boots. A changed boot ID alone cannot identify a switch-caused reset.
4. **Necessity.** `/run/scr-raom/selection` cannot survive reboot. A clock-invalid counter can still bound new resets. The old window API cannot apply that bound. Updating the safe sample fixes fresh installs. Guarding native keepalive starts also protects upgrades with a retained client profile.

## Out of scope

1. Live profile swaps, individual outgoing-service shutdowns, automatic recovery, deleting history and permanent threshold overrides.
2. Client inventory deployment, Cloudflare, platform-wide NTP/watchdog qualification, OS repairs, new daemons and generic transition or package-backup frameworks.
3. Hardware operation during planning, forced watchdog resets, inferred device authority and changes to historical records.

## Product algorithm

1. VALIDATE exact arguments, root privileges and opposite source mode under the existing service lock. Reject malformed, same-mode, missing, stale or corrupt selection with exit 2 before counter access, service changes or reboot.
2. PREPARE the reboot request.
   1. **2.1** CAPTURE a fresh pre-reboot BMC observation for correlation in either direction. NTP synchronization is unnecessary.
   2. **2.2** ***if*** target is safe ***then*** REQUEST safe without a threshold check or recovery acknowledgment. If the counter is unavailable, record unknown correlation. Safe entry still proceeds after the request saves.
   3. **2.3** ***if*** target is normal ***then*** USE that same observation as the recovery acknowledgment. On capture failure, retain safe and refuse reboot.
3. STORE target, source boot ID, correlation evidence and any required recovery acknowledgment together under `/var/lib/scr-raom/`. Validate private storage, write atomically, and sync file and directory.
   1. **3.1** ***if*** save fails ***then*** RETAIN the prior mode and refuse reboot. Untrusted storage cannot authorize normal startup.
   2. **3.2** REQUEST orderly reboot after a verified save. Keep current selection and feeder until native shutdown. Close the lock descriptor in the child.
   3. **3.3** REPORT 0 for submitted request, 2 for rejection/failure. Keep `status` and `profile` tied to the running boot. Restore prior decision on definite reboot rejection. A matching interrupted request can retry without advancing its boundary. Reject conflicting requests.
4. READ durable state on boot. For a submitted switch, bind the pending request once to its identified destination boot. Capture its first BMC observation before the NTP wait, including on safe entry. Record missing evidence as unavailable. Keep native prerequisites and verified feeding.
   1. **4.1** ***if*** safe persists or safe was requested ***then*** SELECT safe without a threshold check or NTP readiness wait.
   2. **4.2** ***if*** a normal request reaches a new boot ***then*** EVALUATE using its acknowledgment and the identified switch interval below. Keep safe as the reboot fallback until verified normal operation.
   3. **4.3** ***if*** ordinary evaluation applies ***then*** WAIT up to `NTP_SYNC_TIMEOUT_SECONDS` (default 60 seconds) after separately bounded startup. Native networking, logging and NTP can run. Keepalive feeds the timer. MONIT-managed applications and full MONIT checks wait.
   4. **4.4** SELECT safe on a proven strict threshold violation. On timeout or indeterminate evidence, apply `SAFE_MODE_ON_ERROR`. Invalid configuration selects the built-in safe profile. Preserve the reason. Persist any automatic safe entry before publishing it.
5. VALIDATE and start one selected MONIT. Verify binary, PID, explicit `-c` and selected pointer. Then verify full native watchdog active and keepalive absent.
   1. **5.1** ***if*** recovery reaches verified normal operation ***then*** CLEAR the latch durably. Retain the acknowledgment for later boots.
   2. **5.2** ***if*** startup, handoff or completion save fails ***then*** REPORT the failed stage. Retain safe fallback for incomplete recovery. Preserve verified feeding where available. Report unverified feeding explicitly.
   3. **5.3** REUSE the current selection for same-boot lifecycle retries. Read-only status and decision-only selection cannot certify completion.

### Reset evidence boundary

1. Use proposed `record --print-observation` for both endpoints. It returns a fresh committed observation under the reset lock. Only pre-reboot `switch normal` evidence acknowledges an old episode.
2. Extend `check --max-resets N --window SECONDS` with optional `--after-observation ACK` and `--switch-reboot BEFORE AFTER`. Pass bounded canonical records. RAOM identifies the submitted request and boots. Reset monitor validates the observations and owns the arithmetic.
3. Match the durable request, actual orderly reboot submission, source and destination boot IDs, and ordered observations from the same controller, firmware and counter epoch. Bind the destination before evaluation. Reject stale, rejected or ambiguously submitted requests as grounds for an exemption. If an intervening or unobserved boot makes attribution uncertain, report unavailable. Never substitute a later boot for a missing endpoint.
4. For that interval only, an increase of exactly 1 contributes zero eligible resets. An increase greater than 1 contributes the **full** increase. Zero contributes zero and earns no future credit. Missing, decreasing or incomparable counters give unavailable evidence. Safe selection still wins on a persisted-safe boot. Ordinary evaluation uses its configured error policy.
5. Consume correlation once. Reuse the same classified interval for repeat checks while it overlaps the window. Never subtract one from another interval. Keep raw journal observations, counters and deltas intact. Safe entry does not advance a recovery boundary.
6. After a valid acknowledgment, eligible increases at most N prove no exceedance even before a full window elapses. Otherwise use conservative timed bounds. Return 1 only for proven in-window exceedance and 2 for indeterminate timing. Resume ordinary evaluation once a trustworthy full window lies beyond affected evidence. Preserve the plain `check` contract.

## Safety

1. ITM-0008 is hardware-required. Preserve original `var/image_8.26.0`, kernel archive and README bytes and metadata. All mutation uses authorized disposable copies.
2. Build one `Architecture: all` archive with `etc/deb/raom/deb.conf`. Debian 1.1.1 fits the retained 1.1.0 `1.1.*` downgrade check. Product release is 3.0.2.
3. Dpkg owns binaries, links, conffiles and diversions. Diverted native originals supply backups. Reject foreign owners, occupied destinations and unsafe links, including collisions at the private state path.
4. Keep maintainer callbacks service-inactive. Fresh installation initializes ordinary evaluation. Upgrade preserves existing durable state and adopts a validated current 1.1.0 safe selection. Missing established state is a storage failure.
5. Preserve exact rollback archive, client conffiles, reset history and recovery state before downgrade/removal. Restore native paths through dpkg. Clean only package-owned additions. Document that 1.1.0 cannot enforce the new latch.

## Verification

| # | Criterion | Test and expected result | Defect or affected regression | Stage |
| --- | --- | --- | --- | --- |
| 1 | V1 / D2 — evidence boundary | Capture 100 before recovery despite unsynchronized NTP. At N=0, M=900, an identified switch interval 100→101 contributes 0 and returns 0. With valid in-window timing, 100→102 contributes both and returns 1 at N=0 **and** N=1. Check raw journal deltas +1/+2. | Old resets counted, legitimate +1 charged, or 1 subtracted from +2. | TSK-0001, installed TSK-0006 |
| 2 | V2 / D2 — new resets and uncertainty | After exempt 100→101, ordinary 101→102 counts at N=0. Repeat checks and window expiry never move the exemption. Test zero delta, ordinary reboot without request, equality, rotation, missing endpoint, skipped boot, decreased counter, changed identity/epoch and uncertain time. Ambiguous evidence returns 2 on evaluation. Plain check retains 0/1/2. | New resets masked, stale baseline applied to a replacement controller, or false threshold after clock jump. | TSK-0001, installed TSK-0006 |
| 3 | V3 / D1 — command guards | For both targets exercise opposite/same modes, wrong arity, unknown target, non-root, absent/stale/corrupt selection, lock contention. Invalid requests leave services, durable state, reset history and reboot call count unchanged. | Unauthorized reboot or selection initialization on rejection. | TSK-0002 |
| 4 | V4 / D1 — durability and retries | Inject counter failure, short/failed write, sync/rename error, command interruption and reboot rejection. Require no reboot before durable request save. Failed normal counter capture/save retains safe and refuses reboot. Missing safe-entry counter records unknown correlation. Retry without moving the boundary. Rejected submission confers no exemption. | Safe latch lost, advanced acknowledgment or false completion. | TSK-0002 |
| 5 | V5 / D1–D2 — reboot decisions | Change boot ID and recreate only volatile boot state. Manual, threshold and error-triggered safe survive repeated boots with no threshold call. Check correlation in both directions. Raw observations on safe entry never acknowledge old resets or invoke threshold evaluation. Missing first-boot evidence cannot transfer the exception to a later boot. Exercise recovery with both error flags, strict new threshold and failed boot. | A persistent safe boot clears itself, stale request replays, or recovery bypasses a new fault. | TSK-0002/0003, installed TSK-0006 |
| 6 | V6 / D3 — both feeders and supervision | Trace native lifecycle calls and process status. Verify one selected MONIT before arming, one full watchdog afterward and exclusive keepalive during protected gaps. Replay a retained legacy keepalive start against the active watchdog. Check native MONIT health with normal-only services absent. Absent MONIT fails the check. | Safe false alarm, competing feeders, lock recursion or premature arming. | TSK-0003, installed TSK-0006 |
| 7 | V7 / D3 — lifecycle failures | Inject invalid profile, stale PID/argv, failed watchdog start, failed keepalive and concurrent rearming during stop/restart. Require truthful status, ordered handoff and no successful completion on failure. Repeat start/force-reload retains chosen profile. | Planned PID gap triggers watchdog, hidden feeder failure or normal fallback. | TSK-0003 |
| 8 | V8 / D4 — package | Dpkg install, 1.1.0 upgrade, reinstall, failed upgrade, downgrade, remove and purge. Check archive identity, ownership/conflict refusal, client state/history, restored native paths and callback inactivity. | Lost safe selection on upgrade, overwritten client profile, stale state or broken rollback. | TSK-0004, final locked gate |
| 9 | V9 / D5 — operator contract | Trace both commands, errors, diagrams, fallback, NTP wait and feeder claims against CLI and boot cases. Check README and planned release text describe the one-off +1 exception and full larger delta. Preserve prior entry. | Misleading reboot instructions or premature released/hardware claim. | TSK-0005, final document review |
| 10 | V10 / D1–D4 — installed integration | Run dpkg-installed RAOM and reset API together in disposable isolated root. Use packaged dependency fixtures, simulated boots/reboot sink, target MONIT syntax and a harmless client service supervised by MONIT. Exercise both switch intervals and a later ordinary reboot. Retain which components actually ran. | Passing module tests with broken CLI, package mapping, incompatible profile or absent client supervision. | TSK-0006, final item QA |

### Mandatory gates

1. Apply `docs/SDLC-DEVELOPER-GUIDE.md#scope-and-verification`. Task validation uses mapped checks and applicable style. Every Bash handoff includes `.agents/skills/bash-style/SKILL.md`, `bash -n` and available ShellCheck. Independent snapshot QA runs full `./bin/lets sdlc gate unit`, applicable changed-path style and leased `gate system --holder ITM-0008`. A focused pass cannot replace a repository or image gate.
2. Under the shared SDLC image lock, verify quarantine, architecture/execution intent, active mounts, partition and source identity. Hash source, copy, mount only the disposable copy, capture baseline, install, test, uninstall all delivered packages, verify restoration, unmount, detach, rehash source and clean scratch before unlock. Use `./bin/lets sdlc test-package ITM-0008 --image IMAGE --deb DEB` with exact absolute inputs and approved functional/rollback assertions. Keep upgrade/downgrade evidence on suitable disposable baselines.
3. Record whole-tree comparisons under the existing contract, including content, added/deleted/moved paths, type, ownership, symlink targets, hardlinks and xattrs. Record configured exclusions and focused proof for affected excluded paths such as reset history. Fresh-package native install/purge uses explicit `--test-command` and `--rollback-command` assertions. Check baseline compatibility before the run. Native purge comparison omits permission bits and access/modification times. Record its limits. Preserve original modes and timestamps and use applicable existing restoration evidence for required metadata. Missing required proof blocks acceptance. Do not add general dpkg metadata tests, access-time equality gates or manual payload-copy machinery.
4. Restoration, fingerprint, source integrity, unmount/detach or cleanup failure quarantines the image. Stop image work. Separate approved recovery must prove restoration and cleanup. Ordinary leases never replace the image lock. Do not enumerate protected runtime siblings.

### Post-task item acceptance

1. Publish explicit implementation INPUT under `.codex/sdlc/artifacts/items/ITM-0008/` through `./bin/lets sdlc artifacts publish`. Include exact archive/hash, source, focused and locked results. Restore/verify bytes, paths and modes through artifact commands. Preserve historical bundles, product branch and control-state locations.
2. Independent validation and QA use detached source tree and INPUT digest. QA publishes a separate QA-stage RESULT for that pair without self-reference. SHOW exact pair, pinned RESULT, diff, tests, rollback and hardware obligations. Require explicit approval. Pass `--expected-artifacts DIGEST` to verified, approve, settle, prepare-promotion and promote. Missing index cannot downgrade a bound context.
3. Obtain separate developer authority for the device, image, exact archive/version/hash, installation, reboots, service actions and rollback. Historical `root@192.168.68.52` and `admin/hw_ed25519` identify only the prior route. Establish recovery access, saved originals and stop conditions.
4. Record initial boot ID, source/image hashes and policy. Install through dpkg. Exercise normal → safe → repeated safe reboot → normal recovery. Record expected/observed boot IDs, actual NTP/counters, profile/argv, supervised client-approved safe check and exclusive full watchdog. Record comparable BMC counters around authorized switches and boot IDs that establish attribution. Compare eligible counts with raw deltas. Verify old-episode recovery and genuine new threshold behavior under authorized conditions. Record tested rollback. A missing prerequisite stays pending.
5. Record verbatim developer result against exact device/image/package via `hardware pass|fail`. Keep REVIEW until confirmed. D-11 waiver cannot transfer. Keep 3.0.2 Planned through promotion. Coordinator marks Released only after item completion.

## BLK-0001 — Reboot-based RAOM recovery and delivery

### TSK-0001 — EXPOSE AND APPLY THE RESET ACKNOWLEDGMENT BOUNDARY

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. EXTEND `parse_args`, `show_usage`, `main` in `src/tools/resets-monitor/tool.sh` for capture, acknowledgment and the optional identified switch interval in D2. Reuse `record_observation` and validated committed records in `src/tools/resets-monitor/src/runtime/{record,history}.sh`.
2. APPLY the acknowledgment and switch interval to eligible window counts in `check_window` and `decide_window` in `src/tools/resets-monitor/src/runtime/time.sh`. Add V1–V2 cases to `src/tools/resets-monitor/test/check-runtime.sh`.

**Done when**

1. V1–V2 pass via `./bin/lets deb test runtime`. A capture failure emits no usable acknowledgment. V1 distinguishes full +2 from subtracting one. Existing bare commands and exit codes remain compatible.

### TSK-0002 — PERSIST SAFE MODE AND REQUEST A GUARDED REBOOT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | high |

**To do**

1. ADD D1 request dispatch to `parse_args`, `scr_usage`, `main` in `src/tools/raom/tool.sh`. Define trusted durable path and reboot executable in `src/tools/raom/etc/raom.conf`.
2. EXTEND `select_mode`, `load_selection`, `publish_selection` and shared boot initialization in `src/tools/raom/src/{decision,monit}.sh`. Use a versioned data-only record, owner-only directory/file, checked ancestry, atomic rename and sync. Keep the boot lock outside this durable data.
3. IMPLEMENT one-time source/destination binding in the pending request, including retries and verified completion. Keep safe-entry correlation separate from normal recovery acknowledgment. Keep current-boot status truthful while reboot is pending. Cover both SysV and standalone selection. Use `src/tools/raom/test/{check-cli,check-decision}.sh` with simulated reboot and storage failures.

**Done when**

1. V3–V4 and decision cases of V5 pass in fixtures. A synchronized next boot with old evidence alone can select normal. Recovery capture/save failure returns 2, retains safe and records zero reboot calls. Failed reboot submission leaves the original profile and feeder operating.
2. A persisted-safe boot skips NTP-backed decisions. An incomplete normal attempt has durable safe fallback. Unit-test completion with an explicit simulated readiness result; TSK-0003 supplies real service integration.

### TSK-0003 — ARM FULL WATCHDOG AFTER VERIFIED MONIT STARTUP

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | high |

**To do**

1. UPDATE `src/tools/raom/etc/safe.monitrc` to supervise native watchdog through the gated init adapter. Remove the sample's keepalive supervision. Client services remain client-defined.
2. EXTEND `monit_action`, `watchdog_action`, `selected_monit_running` and handoff checks in `src/tools/raom/src/monit.sh`. Arm directly under the held lock after verified launch. Make duplicate native/profile requests idempotent. Preserve lock-free native status and close inherited descriptors.
3. GUARD the retained native keepalive entry via `src/tools/raom/etc/compat/wd_keepalive.init` and the existing dispatcher/lock in `src/tools/raom/tool.sh`. Keep early SysV feeding and native status. Prevent a retained profile start/restart from displacing full watchdog or creating a second feeder. RAOM's own handoff calls the diverted original through a trusted path in `src/tools/raom/etc/raom.conf`. Avoid reacquiring its lock.
4. COMPLETE D1 only after verified profile, full watchdog and exclusive feeding. Preserve native restart/stop, fallback and safe failure behavior. Update `src/tools/raom/test/check-boot.sh` assertions for the shipped sample, legacy keepalive request and captured native checks.

**Done when**

1. V5 operational cases and V6–V7 pass through normal entry points with isolated process/service fixtures. Disabled normal services do not cause watchdog failure. Missing MONIT does. Failure cannot publish operational recovery success.

### TSK-0004 — PACKAGE THE REVERSIBLE UPGRADE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0003 |
| 2 | model | high |

**To do**

1. SET Debian 1.1.1 in `etc/deb/raom/control`. Keep one unified build through `etc/deb/raom/deb.conf`. Preserve existing conffiles, conflicts and diversions. Add one supported native diversion for `/etc/init.d/wd_keepalive` with its captured original and conflict checks.
2. IMPLEMENT fresh, upgrade, downgrade and cleanup handling in `etc/deb/raom/package-common.sh` (`package_main` and existing diversion checks). Use the dpkg target root throughout. On downgrade to 1.1.0 or aborted upgrade, return the new diversion to its exact original path and owner at the proper callback stage. Keep shared diversions intact. Protect the durable record during partial upgrades. Retain rollback data before removing package-owned additions.
3. UPDATE `src/tools/resets-monitor/test/{check-build,check-package}.sh` archive expectations and `check_lifecycle`. Exercise the actual retained 1.1.0 archive and candidate in both directions. Keep synthetic failure versions distinct from the delivered version.

**Done when**

1. V8 passes with real archives in isolated dpkg roots. Exact archive, version, architecture and test results recorded. Modified client conffiles/history survive. A running 1.1.0 safe selection survives candidate upgrade and reboot simulation. No callback calls a service or reboot.

### TSK-0005 — DOCUMENT OPERATOR RECOVERY AND RELEASE CONTENT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0004 |
| 2 | model | default |

**To do**

1. REVISE `src/tools/raom/README.md` sections 2 and 3, including existing architecture/boot/decision diagrams and §2.2.1 algorithm. Preserve authored edits and useful numbering. Cover both commands, the +1-only switch exception, full larger deltas, ordinary reboots, unknown evidence, proof of completion, startup delays, persistent safe, watchdog and rollback.
2. UPDATE affected references in `docs/MONIT.md`, `docs/DEVELOPER-GUIDE.md` and `src/tools/resets-monitor/README.md`. Document optional API arguments, counter/time limits and Debian 1.1.1 examples.
3. RECONCILE root `RELEASE-NOTES.md` with implemented behavior and limitations. Preserve 3.0.1, newest-first order and “3.0.2 — Planned”. State the switch-reboot counting rule in brief product-facing language. Omit internal IDs and ceremony names. Coordinator reconciles existing main edits to this owned document. Shared `AGENTS.md` edits stay with their owner.

**Done when**

1. V9 passes against command help and focused test results. README distinguishes request acceptance from verified target operation, timer feeding from MONIT supervision, and a timeout from successful NTP synchronization. Release status remains Planned.

### TSK-0006 — VERIFY THE INSTALLED RECOVERY PATH

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0005 |
| 2 | model | default |

**To do**

1. EXTEND `build_fixtures` and isolated invocation in `src/tools/raom/test/check-integration.sh`, plus `main` and `select_mode_check` in `src/tools/raom/test/integration/run.sh`. Use dpkg-installed tools, an isolated reboot sink and controlled boot identities. Change only test boundaries needed for V10. Never expose a host reboot, service manager or watchdog device.
2. EXERCISE the real reset CLI, packaged RAOM, target-compatible MONIT syntax, actual MONIT supervision of a harmless fixture and captured native health behavior. Test the identified +1 and full +2 cases across volatile state loss. Follow with an ordinary reboot at N=0. Use separate fresh fixture state for independent scenarios. Label simulated counters, NTP, reboots and feeders.
3. REBUILD after packaged source/docs change. Retain exact `.deb`, source and tool identities, logs and expected/observed results for INPUT selection. Use explicit managed evidence paths. Never ship fixture configuration as client inventory.

**Done when**

1. V10 passes for the built candidate in disposable dpkg integration. A lost old acknowledgment, missing watchdog activation or broken package-to-CLI wiring makes the test fail. Record prerequisite failures honestly. Final detached QA, locked image checks, SHOW, promotion and hardware confirmation remain post-task obligations.
