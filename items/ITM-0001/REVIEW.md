# ITM-0001-BMC-RESET-MONITOR-UTILITY — Review

This review holds the user's decisions on this item. Where a decision disagrees with `PLAN.md`, the decision wins. `PLAN.md` stays unchanged.

## D-01 — Remove rotation tests

1. **Overrides:** Plan r3 TSK-0006 To do 1 (rotation test file), To do 13, Done when 1, 5, and 6. Rotation-specific test obligations in Done when 3 and later task/acceptance gates are also removed. Other behavior and package restoration requirements remain.
2. **Decision:** Developer: "Remove these tests, proceed with the implementation". Remove active rotation tests and their exclusive harnesses. OS owns rotation policy. Keep production rotation integration, non-rotation tests, package restoration, and required hardware confirmation. Do not rerun archived rotation probes or claim removed coverage passed.
3. **Context:** Developer: "Where in the plan did we need to test logs rotation if I said that logs rotation is the target OS responsibility ?" Approved PLAN.md remains unchanged. Historical evidence remains preserved.

## D-02 — Proceed with next task and preserve source images

1. **Overrides:** Historical quarantine/recovery holds as prerequisites to starting TSK-0008, including plan r3 TSK-0008 To do 6/6.1 and conflicting retained-hold wording. Approved PLAN.md remains unchanged.
2. **Decision:** Developer: "Drop all quaranteed / blocks now. You must proceed autonomously preserving images under var/ intact for future reuse. Resume, don't stop too much".
3. **Decision:** Developer correction: "Correction: the dance around old SDLC is taking too long. Just proceed to the next task". Proceed with TSK-0008 implementation and fresh verification. Do not spend task execution on retired SDLC recovery ceremonies.
4. **Boundary:** Original image/kernel bytes and metadata under var/ remain preserved. Mutable verification uses disposable copies. Historical records remain evidence, never fabricated restoration or runtime success.
5. **Boundary:** Current source-integrity, package ownership, reversibility, isolated execution, cleanup, independent validation, and truthful result reporting remain. D-01 remains effective. Device operations and exact-revision SHOW approval remain separate.

## D-03 — Verify item deliverables, not global OS inventory

1. **Overrides:** Plan r3 global complete-dpkg-inventory prerequisite in Safety 10/23 and TSK-0008 To do 6.2/6.3. Corresponding package preflight and tests must follow item scope. Approved PLAN.md stays unchanged.
2. **Decision:** Developer: "Again you try to test the target OS instead of the deliverables of this item."
3. **Scope:** Verify paths and behavior delivered by this item. Missing file lists for unrelated OS packages do not require OS repair or prevent item testing.
4. **Boundary:** Retain checks for known package conflicts and SDLC ownership overlaps on managed paths, unsafe path types, backups, upgrade preservation, and exact restoration. Missing records never establish that a path is unowned.
5. **Boundary:** Preserve original var/ images and metadata. Use disposable copies under shared image lock. Retain source checks, architecture, cleanup, independent validation, exact-revision SHOW, and separate hardware acceptance.

## D-04 — Discard implementation and restart in Bash

1. **Overrides:** Entire plan r3 implementation design, C/kernel sources, toolchain dependency, scattered source/package layout, completed task results, and prior SHOW candidacy. Old approval does not approve replacement plan.
2. **Decision:** Developer: "The entire item was wrongly implemented and needs to be discarded." Source request retained verbatim in planning/bash-restart-20261112/customer-source.txt.
3. **Decision:** Simple Bash scripts under `src/resets-monitor/src`; SysV and Debian control/pre/post scripts under `src/resets-monitor/scripts`; item configuration under `src/resets-monitor/etc`.
4. **Decision:** `./bin/lets deb build src/resets-monitor/etc/deb.conf` copies configured `INCLUDE_FILES` mappings with rsync semantics and `EXCLUDE_FILES` into `build/resets-monitor/`. Debian archive stays under ignored `build/`.
5. **Decision:** Remove current implementation and tracked `docs/audits`, `docs/RESET-MODULE*`; clean rejected item history; rewrite item title/brief and plan again.
6. **Clarification:** Developer: "Retain API, the scope of the item is the same - 1+2 of RAOM". Functional scope, decision-only behavior, explicit threshold/window, and exits 0/1/2 remain.
7. **Boundary:** D-01 and D-03 remain effective. No compiler/toolchain or broad OS qualification in replacement. Original `var/` files remain intact. New plan and package need their own acceptance.
8. **Cleanup:** Rejected ITM-0001 worktrees/branches removed. Main cleanup commit removes old kernel source and requested documentation. Fresh empty integration supersedes previous verified context through public tooling. Historical ledger/artifacts remain rejected history.

## D-05 — Match LETS tool layout and module size

1. **Overrides:** Current source refactor's direct-execution guard in `tool.sh`, separate `arguments.sh` and `command.sh`, overly narrow module split, and source-loading ownership.
2. **Decision:** Developer: "tool.sh can never run directly, remove [ \"${BASH_SOURCE[0]}\" != \"$0\" ] || main \"$@\"". Keep sourced tool files from invoking `main` automatically.
3. **Decision:** Developer: "the src-reset-monitor entry point must load all the lib/ like lets.sh does and all the src/, tools.sh uses them directly without sourcing". Make the central entry point load shared libraries and tool modules before command dispatch. The command layer uses loaded functions.
4. **Decision:** Developer: "arguments.sh - move into tools.sh see how arguments and usage are handled by LETS tools and copy this behavior" and "command.sh - should be handled in tools.sh not a standalone module". Developer clarification: "I meant tool.sh not tools.sh". Keep argument parsing, usage, and command dispatch in sourced `tool.sh`, following LETS tool conventions.
5. **Decision:** Developer: "make simple file names, merge similar together, e.g.: clock-health.sh -> clock.sh, don't be too granular on modules and functions". Group related helpers in cohesive modules with short names.
6. **Process:** Developer: "Ask me where in doubt. See LETS - it's the best reference for simple modular bash scripting." Use LETS patterns as reference and ask when layout intent remains unclear.
7. **Standing guidance:** Apply these layout rules to upcoming Bash tool implementations. Preserve simple implementations, documented functions, and useful in-code comments.

## D-06 — Consolidate Bash modules and load them from entry points

1. **Overrides:** Current `lets_info` and `lets_usage` names, separate storage/files/history modules, separate clock/window modules, and `src/tools/resets-monitor/src/runtime.sh` loader.
2. **Decision:** Developer: "replace lets_XXX with scr_XXX in functions names". Rename tool metadata functions to `scr_info` and `scr_usage`.
3. **Decision:** Developer: "leave one empty row between blocks of statements that go together". Separate statement blocks with one blank line.
4. **Decision:** Developer: "starge+files+history - belong in one file - history.sh". Merge storage, file, and history functions in `history.sh`.
5. **Decision:** Developer: "remove: src/tools/resets-monitor/src/runtime.sh". Remove the loader module. Central and installed entry points source the required runtime modules before `tool.sh`.
6. **Decision:** Developer: "clock and windows should go into a single file - time calculations". Merge clock and reset-window functions in `time.sh`.
7. **Context:** Developer asked: "src/tools/resets-monitor/src/scr-resets-monitor - why needed ?" This file is the package's installed `/usr/sbin/scr-resets-monitor` entry point. It loads installed runtime modules and `tool.sh`; the central source-tree entry cannot replace it because that entry depends on project configuration and shared development libraries.
8. **Standing guidance:** Apply these module, naming, and spacing rules to upcoming Bash tool implementations.

## D-07 — Apply reviewed code simplifications

1. **Overrides:** Retain unused `scr_info` and `scr_usage` metadata wrappers; repeat runtime module filenames in source, installed, and test entry points; duplicate package payload paths in `FILES` and `PAYLOAD_FILES`; and keep commit operations in standalone `commit.sh`.
2. **Decision:** Developer: "Apply the above improvements". Remove unused `scr_info` and `scr_usage` functions. Keep `show_usage` as command help.
3. **Decision:** Place runtime modules under `src/tools/resets-monitor/src/runtime/`. Have source, installed, and test entry points load runtime `*.sh` files from that directory.
4. **Decision:** Define `PAYLOAD_FILES` once. Derive `FILES` by adding the managed startup link, runtime data, markers, and lock paths.
5. **Decision:** Move journal/cache commit functions into `history.sh` and observation orchestration into `record.sh`. Remove `commit.sh`.
6. **Boundary:** Preserve runtime behavior, API, package ownership, upgrade/rollback, and restoration evidence. No package promotion or target operation is authorized by this refactor.

## D-08 — Use one source and installed command entry point

1. **Overrides:** Separate source-tree `src/bin/src-resets-monitor` and installed `src/tools/resets-monitor/src/scr-resets-monitor` command entry points.
2. **Decision:** Developer asked: "The tools.sh needs to be called from src/bin/src-resets-monitor, why src/tools/resets-monitor/src/scr-resets-monitor is needed ?" Use `src/bin/src-resets-monitor` as the single command entry point for source-tree use and installed `/usr/sbin/scr-resets-monitor` use.
3. **Implementation:** Make the entry point load shared project libraries and `src/tools/resets-monitor/src/runtime/*.sh` in the source tree. In the installed package, load modules from `../lib/scr-resets-monitor/runtime/` and `tool.sh` from the installed library directory.
4. **Decision:** Remove `src/tools/resets-monitor/src/scr-resets-monitor`. Map the central entry point to the package's `/usr/sbin/scr-resets-monitor` path.
5. **Boundary:** Keep the same runtime API, package paths, behavior, ownership, upgrade, and restoration criteria. Do not promote or perform target/hardware operations.

## D-09 — Install the complete source subtree under `/usr/local/scr`

1. **Overrides:** D-08's `/usr/sbin` command path and separate installed runtime/module layout.
2. **Decision:** Developer: "The debian package needs to install under /usr/local/scr the subtree of the repo starting under src/ + install /usr/bin/ links into this location".
3. **Implementation:** Copy the complete repository `src/` subtree to `/usr/local/scr/`, preserving paths. Install `/usr/bin/scr-resets-monitor` as a symlink to `/usr/local/scr/bin/src-resets-monitor`.
4. **Integration:** Keep the existing `scr-resets-monitor` API. Update SysV, logrotate, monit examples, tests, and documentation to use the new paths. Remove the redundant installed wrapper.
5. **Boundary:** Retain package ownership, original-file backup, upgrade, rollback, and full restoration checks. This decision does not authorize package promotion or target/hardware operations.

## D-10 — Remove source-image acceptance checks

1. **Overrides:** Plan r5 Verification 11–12, Mandatory gates 3–4, and Post-task item acceptance 4, to the extent they require checks against `var/image_8.26.0` or another source image.
2. **Decision:** Developer: "Remove the var/image_8.26.0 checks, promote the item now" and "Remove the var/image_8.26.0 checks, promote the item now".
3. **Scope:** Do not run or require source-image install, runtime, restoration, or cleanup checks for this item. Preserve all files and metadata under `var/`.
4. **Boundary:** Keep exact-package target testing and hardware confirmation requirements. Use the real target after exact SHOW approval. This decision does not authorize reboot, reset, power loss, or firmware/watchdog changes.
5. **Boundary:** Keep repository gates, focused Bash checks, native package lifecycle checks, package hash binding, exact-revision SHOW, and promotion checks.
