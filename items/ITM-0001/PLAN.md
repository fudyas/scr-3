# ITM-0001-KERNEL-RESET-MODULE-VENDOR-BUILD — Plan

## Goal

Build existing `scr_reset_monitor.ko` against supplied platform kernel tree. Deliver reproducible module, build commands, input hashes, static checks, and compatibility limits.

## Context

Customer source: “The var/ folder now contains the kernel sources of the exact HW platform. I want you to build the module against the kernel sources there. Create and run such SDLC item”.

Archive: `var/kernelDeb_2.0.0.0_3.10.105_including_RS485_ext_driver__16_05_2018.tar.gz`, SHA-256 `a786b745424c93946c2e1bbcabae8325e3f95c58c3308c5e0160478860b01a3c`.

README: `var/Kernel_2.0.0.0_3.10.105_MSD_README.txt`, SHA-256 `7f6ddc8643e043f12029ed40549a219237a5d6aa0a56c25dc20b8a2da40b6eac`.

Legacy `REQ-0001-GOAL-COUNT-SYSTEM-RESETS` supplies current module files only. Source pins appear in TSK-0002. Supplied tree reports `3.10.105-imx6`, GCC `4.8.4`, build `#4`. Prior hardware reports build `#5`. Managed compiler is Linaro GCC `4.8.3` prerelease. Missing host `file` currently blocks managed preflight.

## Design

1. **Fit:** Import two pinned module files. Build external module against disposable supplied-tree copies. Preserve module behavior.
2. **Patterns:** Reuse LETS compiler wrappers, pinned runtime, Kbuild, and toolchain tests. Replace unavailable `file` with equivalent native `readelf` architecture checks.
3. **Context:** Preserve vendor configuration and generated inputs. Report platform provenance separately from running-kernel compatibility. Retain legacy history and quarantine.

## Out of scope

1. Image/package changes, installation, quarantine recovery, hardware access, module loading, reboot, or hardware acceptance.
2. Kernel/U-Boot changes, activation fixes, reset-cause features, or legacy requirement resumption.
3. Global dependency installation, compiler replacement, or unrelated legacy edits.

## Safety

1. PRESERVE original `var/` bytes, ownership, modes, timestamps, links, and xattrs. USE no-atime reads for kernel inputs.
2. KEEP extraction, host-helper rebuilds, and module outputs outside `var/`. NEVER access source image or quarantined copy.
3. VALIDATE archive member paths and links before extraction. REJECT escapes, unsafe types, or unexpected root names.
4. KEEP kernel source, `.config`, generated configuration/release headers, and symbol inputs unchanged across module builds.
5. ALLOW host Kbuild-helper rebuilds inside disposable copies only. RECORD commands and resulting helper identities.
6. USE native `readelf` solely for host-tool preflight. ROUTE ARM compiler/binutils operations through `./bin/lets toolchain`.
7. RETAIN module under `.lets/sdlc/artifacts/ITM-0001/<module-sha256>/scr_reset_monitor.ko`. TRACK manifest and evidence in reviewed tree.
8. KEEP artifacts explicitly offline-build outputs. Debian ownership, lifecycle, rollback, image-lock tests, and hardware confirmation require separate installation scope.
9. STOP after three failures at same stage, unsafe extraction, input drift, or missing required evidence. PRESERVE failure logs.

## BLK-0001 — BUILD MODULE AGAINST SUPPLIED VENDOR TREE

### TSK-0001 — RESTORE MANAGED TOOLCHAIN PREFLIGHT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | default |

**To do**

1. UPDATE `lets/lib/devenv/toolchain.sh` runtime/compiler ELF checks to use locale-stable native `readelf -h`.
2. REQUIRE ELF32, little-endian data, and Intel 80386 machine for managed runtime loader and each allowlisted tool.
3. RETAIN hashes, manifests, runtime libraries, compiler banner, allowlist, ownership, link containment, and environment checks.
4. EXTEND `tests/toolchain/run.sh` with real valid-i386, wrong-class/machine, malformed-file, and missing-reader rejection cases.
5. RUN existing toolchain functional suite with cached verified runtime/compiler.

**Done when**

1. `./bin/lets toolchain info --json` succeeds without host `file`.
2. Valid cached i386 binaries pass. Wrong architecture/class, malformed input, and unavailable reader fail closed.
3. Every allowlisted tool works. Managed smoke compile produces ELF32 ARM object.
4. Compiler/runtime provenance remains unchanged. No global install or validation bypass occurs.

### TSK-0002 — PIN INPUTS AND BUILD MODULE TWICE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | high |

**To do**

1. IMPORT only current `scr_reset_monitor.c` and `Makefile` into `src/scr_reset_monitor/`.
2. REQUIRE source SHA-256 `3377a2ca4fa77f29958234282d1d1ce0d6eaccb5526475ce0a6517df18c7fb5e` and Makefile SHA-256 `a4d90d460a003f43d60e7d479615b2f61c81e6cd0c3d31fa82b0c68d777f9e3d`.
3. RECORD legacy input path under `.codex/worktrees/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/sdlc/requirements/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/src/scr_reset_monitor/`.
4. ADD `scripts/build-reset-module.sh` for bounded external-module builds through existing LETS toolchain environment.
5. COPY supplied archive with no-atime reads into item-owned scratch outside `var/`.
6. VERIFY pinned archive and README hashes plus original metadata before extraction.
7. EXTRACT distinct `build-a` and `build-b` kernel/module workspaces after archive safety checks.
8. CAPTURE `.config`, generated headers, `Module.symvers`, `System.map`, `vmlinux` build ID, release, compiler banner, and source hashes.
9. REBUILD required host Kbuild helpers only inside disposable trees. RECORD host compiler and exact helper commands.
10. BUILD external module through `./bin/lets toolchain env -- make` against each supplied prepared tree.
11. REQUIRE unchanged kernel source/configuration/generated-input/symbol hashes after each build.
12. COMPARE complete `.ko` bytes across both clean builds.
13. RETAIN content-addressed module, compiler output, commands, and static-tool output under item artifact directory.
14. VERIFY original kernel-input hashes and metadata after completion. REMOVE only item-owned scratch after evidence retention.

**Done when**

1. Imported source files match exact approved hashes. No other dirty legacy file enters item.
2. Both independent builds finish without unresolved modpost errors. Complete `.ko` bytes and SHA-256 match.
3. Build records prove supplied vendor tree usage and managed ARM compiler/binutils usage.
4. Original `var/` inputs and legacy worktree edits remain unchanged. No image, package, target, or module-load action occurs.
5. Script rejects changed archive/source pins and unsafe extraction inputs before build.

### TSK-0003 — RECORD STATIC ACCEPTANCE AND DELIVERY LIMITS

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | default |

**To do**

1. ADD `evidence/ITM-0001/build-manifest.json` and `evidence/ITM-0001/build-report.md` with exact input/output hashes and commands.
2. VERIFY ELF32 little-endian ARM EABI5, module name, and exact supplied-tree release/vermagic through managed binutils.
3. COMPARE undefined symbols against exported entries in supplied `Module.symvers` and `System.map`.
4. VERIFY every emitted relocation against supplied `arch/arm/kernel/module.c` loader support. REJECT unsupported relocations.
5. COMPARE supplied configuration and `vmlinux` build ID against recorded prior hardware evidence where identities exist.
6. DOCUMENT source build `#4`, prior hardware build `#5`, and GCC `4.8.3` versus recorded `4.8.4` differences.
7. ADD `docs/RESET-MODULE-BUILD.md` with reproducible build command, retained module path/hash, source provenance, and static acceptance limits.
8. RUN toolchain regressions, script syntax checks, meaningful pin/extraction rejection checks, and `git diff --check`.
9. PROVIDE exact module bytes, reviewed manifest, complete diff, and test evidence for independent validation/QA and SHOW.

**Done when**

1. Static report covers every ELF, vermagic, symbol, relocation, reproducibility, and preservation criterion with retained evidence.
2. Module path survives worktree removal. Artifact hash matches reviewed manifest and both build results.
3. Documentation claims supplied-tree build success only. Running-kernel compatibility and hardware acceptance remain unproven.
4. Independent validation and detached-snapshot QA can assess all criteria without source-image or device access.
