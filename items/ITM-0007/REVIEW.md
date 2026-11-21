# ITM-0007-RAOM-SYSV-STARTUP-SERVICE — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Configure RAOM decision and MONIT profiles

1. **Overrides:** Initial brief sections 5–6 and 8, preliminary MONIT-independent startup recommendation, and customer email requirement against MONIT loading RAOM services. No approved plan exists.
2. **Decision:** Developer: "The RAOM service runs after NTP is available" and "The service launches MONIT with the safe/normal mode configuration".
3. **Decision:** Developer: "Create a default configuration for the service with >N resets in M seconds - such that YOU can test it, the RAOM client will configure their values".
4. **Decision:** Developer: "RAOM needs to enter safe mode if no NTP sync occured for more than K seconds (configurable)".
5. **Decision:** Developer answered "YES" to RAOM reading configuration and calling `scr-resets-monitor check --max-resets N --window SECONDS`. Existing utility owns threshold calculation. No duplicate counter algorithm.
6. **Decision:** Developer: "Yes, we still need monitoring the safe mode services, no reason to duplicate monit's job". MONIT owns safe/normal profile service supervision. Do not add parallel RAOM supervision.
7. **Decision:** Developer: "It is now 192.168.68.52". Supersedes 192.168.68.54 as inspection target.
8. **Boundary:** Planning and read-only inspection only. No package install, service restart, watchdog operation, reboot, or physical output authorized here.
9. **Pending:** Non-NTP exit-2 policy, exact timing boundary, and boot-mode persistence remain proposed design details for concrete plan review. NTP timeout safe-mode behavior is settled.

## D-02 — Configurable safe mode on errors

1. **Overrides:** D-01 unconditional NTP-timeout safe mode and pending non-NTP error policy. Error-triggered safe mode now depends on configurable flag. Reset threshold remains separate.
2. **Decision:** Developer: "Safe mode on errors (missing NTP, filesystem issues, configuration not accessible, etc) - configurable, if set to true - enter safe mode".
3. **Scope:** Error policy covers NTP synchronization timeout, unavailable reset evidence, filesystem failures, and inaccessible configuration. Do not report these errors as a valid below-threshold result.
4. **Proposed configuration:** `SAFE_MODE_ON_ERROR=true` by default. False permits normal-profile selection on errors where startup remains possible. Positive threshold decision selects safe mode regardless of flag.
5. **Pending:** Built-in fallback when configuration cannot be read or validated requires developer answer. Proposed fallback is true; never assume unreadable configuration contains false.
6. **Boundary:** Mode selection cannot guarantee successful startup when MONIT, selected profile, executable dependencies, or required filesystems are unavailable. Preserve error evidence and report failed startup accurately.

## D-03 — Built-in fallback and client-owned safe profile

1. **Overrides:** D-02 pending configuration fallback; initial brief requirement to deliver customer email service inventory; Cloudflare prerequisite or installation scope.
2. **Decision:** Developer: "Built-in true if fails to read its own configuration. CloudFlare is out of this item scope, the client will define what goes into the safe mode monit config".
3. **Scope:** Built-in safe-mode-on-error defaults to true before configuration access. Configuration-read failure selects safe mode.
4. **Scope:** Client defines safe-mode MONIT service contents. This item owns profile selection and integration, not deployment or qualification of client service inventory. Cloudflare excluded entirely.
5. **Boundary:** Startup remains subject to MONIT and selected profile availability. Report failed launch accurately. Existing watchdog continuity during boot gate remains integration safety requirement.

## D-04 — Build and verify through Debian packages

1. **Overrides:** TSK-0003 private-payload copying and manual metadata restoration/test machinery, and corresponding Safety/Verification requirements that duplicate dpkg responsibilities. Approved RAOM behavior remains unchanged.
2. **Decision:** Developer: "Why don't you build and test via deb package ? Why make custom copies and then try to overcome the issues this  create ? Revert back, test through deb. Remove all unnecessary \"manual\" non-dpkg tests".
3. **Scope:** Build a real Debian archive. Test installation, upgrade, downgrade, removal, and purge through dpkg. Remove custom-copy test paths, tar fingerprint comparisons, access-time equality gates, and unnecessary manual lifecycle simulations.
4. **Implementation:** Use dpkg-managed installed paths and standard Debian configuration, ownership, and diversion mechanisms where required. Remove the generic private-payload copying and backup engine from new delivery. Keep only necessary project-specific migration and service integration callbacks.
5. **Scope:** Preserve focused RAOM decision tests and actual installed behavior tests. Verify project-specific integration, configuration preservation, history preservation, and rollback outcomes through installed packages. Do not requalify dpkg metadata behavior.
6. **Boundary:** Preserve historical packages, reports, failed evidence, source images, and kernel files. Retired metadata failures remain historical evidence, not current acceptance gates. Original hardware-image preservation remains required.
7. **Boundary:** Standard dpkg conflicts remain errors. Do not invent SCR ownership claims or repair global package inventory. The earlier manual nine-path ownership-adoption proposal is superseded by the Debian-native approach, not silently approved.
8. **Boundary:** No target installation, service action, reboot, promotion, or hardware success follows from this decision. Independent validation, required repository gates, exact-revision SHOW, and separate hardware confirmation remain required.

## D-05 — Final design documentation and shared Bash conventions

1. **Overrides:** Product-document history and legacy uninstall explanations; short N/M/K configuration names; duplicated root checks; embedded runtime paths and custom RAOM diagnostic formatting. Prior exact source/INPUT pair needs fresh verification after these edits.
2. **Decision:** Developer: "remove the history record tracking in docs, present with the final intended design (e.g.: no need to explain how scr-resets-monitor needs to be uninstalled)".
3. **Decision:** Developer: "src/bin/src-raom and other scripts needs to adhere to the bash style like in src/bin/src-resets-monitor including empty lines and comments".
4. **Decision:** Developer: "give keys in src/tools/raom/etc/raom.conf meaningful names" and "what is the purpose of src/tools/raom/etc/compat folder ?".
5. **Decision:** Developer: "src/tools/raom/tool.sh needs to load src/tools/raom/etc/raom.conf where all runtime paths are defined like LETS does it".
6. **Decision:** Developer: "the require_root function repeats itself - move to lib/run.sh".
7. **Decision:** Developer: "src/tools/raom/src/decision.sh and others need to reuse lib/log.sh, it also need bettere comments inside functions" and "print usage and check arguments as LETS tool do".
8. **Scope:** Apply fixes in retained integration workspace. Keep product guides about current supported design. Preserve prior immutable SDLC records and package evidence separately.
9. **Boundary:** Retain safe configuration fallback, data-only client configuration parsing, fixed boot mode, actual dpkg verification, and shared logger stream discipline. No new hardware action or promotion authority.

## D-06 — Reload Bash guidance and review completed fixes

1. **Overrides:** Completion sequence for D-05. Reload current Bash skill after fixes, before final acceptance.
2. **Decision:** Developer: "When done fixing, reload the updated bash skills, then review the code and check where its style needs fixing and where the code can be simplified".
3. **Scope:** Review changed code against freshly read Bash guidance. Correct concrete style issues and unnecessary complexity while preserving approved behavior.

## D-07 — Coordinate watchdog activation with RAOM lifecycle

1. **Overrides:** D2/TSK-0002 native watchdog integration and native MONIT stop delegation where they leave MONIT supervision active during mode selection or a planned stop/restart. Necessary package adapters and final-design documentation in TSK-0003/TSK-0004 follow this decision.
2. **Decision:** Developer: "Who and when launches the watchdog to monitor MONIT ? You need to be part of this process to enter safe/normal mode before the watchdog is armed and let it work onnly after the mode is selected. Proceed with the fix and retest".
3. **Scope:** Integrate watchdog activation with committed safe/normal selection and selected MONIT readiness. Coordinate planned MONIT stop/restart so watchdog cannot treat its intentional PID gap as a failure. Preserve hardware feeding through native keepalive handoff. Keep MONIT as service supervisor and client-owned safe-service inventory unchanged.
4. **Verification:** Prove no MONIT watchdog supervision before selection, correct activation after selected MONIT startup, safe planned lifecycle handoff, exclusion of concurrent rearming, retained lock fix, and exact-package hardware retest.
5. **Boundary:** Use reversible Debian package and retained integration. Existing native watchdog checks resume after valid activation. No permanent watchdog disablement, physical reset loops, client service expansion, or source promotion inferred. Latest instruction authorizes necessary target install, native service actions, controlled reboot, and rollback for retest on 192.168.68.52 with admin/hw_ed25519.

