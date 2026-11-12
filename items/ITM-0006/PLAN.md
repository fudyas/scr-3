# ITM-0006-SDLC-MIGRATION-READINESS — Plan

## Goal

Finish SCR SDLC migration with independently verified readiness for OFFLINE kernel-module rebuild. Preserve legacy content, index distinctions, history, packages, and hardware evidence. Deliver canonical pinned module inputs, working managed compiler preflight, durable archive restoration proof, resolving documentation, and fresh UNAPPROVED ITM-0001 plan. Compile no reset module.

## Context

### Customer source

> Issue tasks cleanup where needed suggest what leftovers of the previous SCR SDLC need to be removed
>
> Later user ruling:
> Create a new SDLC chain that transits from old to new SDLC. Add all items to it (except rebuilding the module). The state of the repo after the chain must be "ready for kernel module rebuild" according to the new ceremonies
>
> Later user ruling:
> All these folders belong to the planning, implementation and QA stage and should be managed under .codex/sdlc as in Specz (with claude)

Standing migration authority, verbatim:

> Approve this and pre-approve all other items in this chain until the migration is complete

Separate rebuild source, verbatim:

> The var/ folder now contains the kernel sources of the exact HW platform. I want you to build the module against the kernel sources there. Create and run such SDLC item

### Authority and prerequisite state

1. CHN-0001 order: ITM-0002 → ITM-0005 → ITM-0004 → ITM-0003 → ITM-0006. ITM-0001 remains outside chain, dependent on ITM-0006.
2. Planning checkout: `/home/fudya/devel/scr`, branch `feature/monit-stability`, initial audited base `62b3a9e4bf3d50ad09ea71c17164adcbcf65fe2e`. Current installed base: `8b6a693237700ba7779c5c78fef640fdc0855c5f`. Planner owns this draft only.
3. Relevance CONFIRMED. Plan READY for coordinator approval. Draft remains UNAPPROVED until approval ceremony. Prerequisite completion metadata is complete.
4. Completed ITM-0003/0004 source trees, installed commits, INPUT/RESULT locators, current interfaces, and resolving index appear below. No prerequisite completion remains pending.
5. Coordinator records checked current-plan approval under standing migration authority. Planner never approves or commits. No ITM-0006 execution before prerequisite DONE states.
6. ITM-0001 has no standing plan approval. Existing r1 is stale, unapproved history. Replacement remains BACKLOG with no approved revision.
7. Effective REVIEW decisions: none. Complete source records: `.lets/sdlc/logs/ITM-0006/intake-current.json`, `rebuild-item-current.json`, and `rebuild-plan-r1-history.md`.
8. Fresh `items show ITM-0006` agrees with intake: BACKLOG, r0, dependencies ITM-0002/0003/0005. Chain additionally orders ITM-0004 first.
9. This refresh consumes coordinator-supplied ITM-0003/0004 completion evidence. No repeated source audit or gate run occurred.
10. Sequencing choice: retain root-permitted pre-promotion frozen-foundation route for independent ITM-0001 replacement plan. Final pair closes through external post-promotion acknowledgement.
11. Main has unrelated user unstaged `.gitignore` addition `emails/`, SHA-256 `95223e3194ab34676ead1d1b8d94a8c34d9a46cf3763f6b1fcaffb5a0acb5504`. Preserve exact bytes and staging distinction. Main is not clean.
12. Item worktrees start from committed `8b6a693237700ba7779c5c78fef640fdc0855c5f`. Never copy user working edits. No `emails/` data inspection or archival is authorized.
13. Supplied chain check confirms unchanged order, only ITM-0006 unfinished, and ordinary leases free. No hardware, image, or module authority follows.

### Verified and pending inputs

| # | Input | Identity and limits |
| --- | --- | --- |
| 1 | ITM-0002 source | `9f6d26bcab95a09ac643eefa96c7817cac9d4aba`, installed `62b3a9e4bf3d50ad09ea71c17164adcbcf65fe2e` |
| 2 | ITM-0002 historical import | INPUT `6ebd9151f9187333775141e81b3b17d653074e70865de8213b11c2f54b778881`, original-path maps for 96 former root payloads |
| 3 | ITM-0002 final pair | INPUT `d04ef0f55ec933559f8d6bb8f1c7986175a478ace786bd28dbf167fd7df29094`, RESULT `3f138507ca7f77937f42c36619b3011c4a6bb71835f6d519c0b3d9be7ebbd3ec` |
| 4 | ITM-0005 source | `9f6d26bcab95a09ac643eefa96c7817cac9d4aba` |
| 5 | ITM-0005 final pair | INPUT `0dafde9ce21b89d7e82ef07378bed48a35016380eff27240fcadb786660002c5`, RESULT `407902732e2dd731785e465a0d9094aba1c395256fb1a29de733c4db0f35977d` |
| 6 | ITM-0004 final acceptance | DONE, tasks 2/2. Installed commit `41bf1462c5ff6f6de5149a24ff331f4ddc91ee18`. Source tree `d3a5a0e1a757a80784ce1810e543912c2a91d8f0`. INPUT `0670aa05932f3a48d5693f884c8bef8e9adc2c684d56263ffc1e3a8ac6eac804`. RESULT `954af6859a3e436bda98cf341d9b2d08096e39317daae4f4d097eced3ab6c618` |
| 7 | ITM-0003 final acceptance | DONE, tasks 3/3. Installed commit `8b6a693237700ba7779c5c78fef640fdc0855c5f`. Source tree `b0d6a5a9a8d8eb6bc1a52b2731a4b678ecda7545`. INPUT `c4d12274bfaebaca16e712f6a7eb8f45ac880b76fe238cffd3f492eb5d2ec772`. RESULT `938d58abf95124f46d426bc6dfc582b99d3b4fbd4b81587f1c255a1834ff6882` |
| 8 | Durable bundles | `artifacts/bundles/DIGEST.json` on `sdlc`, resolved through `./bin/lets sdlc artifacts list ID --json` |
| 9 | Existing managed records | `.codex/sdlc/artifacts/legacy/scr-pre-item/`, `items/ITM-0002/implementation/`, and `items/ITM-0005/implementation/` |

1. ITM-0002 retains 87 historical and nine current root artifacts. Product `contracts/` and `evidence/` must remain absent.
2. ITM-0005 retains 54 RECOVERY-REQUIRED entries, 21 unreadable texts, 11 pruned suspected mount subtrees, and unresolved image identities.
3. Failed image and four clones remain forbidden offline inputs. Two historical baseline atime drifts remain recorded, never repaired or concealed here.
4. Revision-14 identity `70415f436cfc2bbe4b4df38af2e02e6a56fd69950c718021143ea66662a74a58` lacks verified approved-plan bytes/locator.
5. Local revision-15 draft hash `8a139fe5726d538c58b2fce1e38d95c46fc4c6f39bfaa1830c9bbafbcd871153` differs from retained historical approval claim.
6. Historical `auto-approved` hash is `8801ca2266b6f90afd0e1a937926d3d3f88f4965a67c233be1e8ae5862533618`, dated `2026-09-27T07:14:31+00:00`. Historical state also says `plan.status: draft`.
7. ITM-0003 supplies exact event/document/state evidence and additive clarification. Frozen ITM-0005 reports remain unchanged. Historical authority grants no current execution permission.
8. Historical guide hashes prove capture context only. Current installed guide/index identities appear below, separate from historical capture hashes.
9. ITM-0004 independently verified source/adapter/golden/20-method invariants and documented `lock-run` boundary fixes. All 20 criteria passed, with unit 519/system 8/style 0.
10. ITM-0004 19-entry INPUT restoration and 26-entry RESULT verification passed. Main was clean at that historical completion. Current user edit remains protected. Item worktrees removed. Use MAIN and durable bundle locators.
11. Installed ITM-0004 guide SHA-256: `99908d49f8aa1986ef41e04222fddd87b8d47ed17b693a372de9d6cf35443555`. Consumer contract SHA-256: `33c7441f5c30b3e9aca2c816b865b09ecf1cca01c50a1e296dca6267d1032f66`.
12. These identify completed ITM-0004 context. ITM-0003 final guide identity below supersedes this historical guide hash for current contract.
13. ITM-0003 approved plan: `.lets/sdlc/logs/ITM-0003/approved-plan-r1.md`. Checked draft SHA-256: `ad69c9ad190d4f111a08bd87495c5638d665856c09017251b93319b47e30c2fa`.
14. ITM-0003 14-entry preservation INPUT: `d22e41f9839d2315b3a30fc8ae54fe789745f15597b762d44319a50c30ca8fcc`, referenced by final 24-entry INPUT. Independent restoration passed.
15. ITM-0003 added narrow Plan-section lifecycle sentence to canonical SDLC guide. It places final QA/RESULT/SHOW/promotion after task validation. Engine/role/skill/template remained unchanged.
16. ITM-0003 all 28 criteria independently passed. Fresh 24/96 restoration, link, and fidelity checks passed. Actual unchanged-runtime unit 519/system 8 reuse was explicitly verified. No new generic run is claimed.
17. Ten old tracked `.codex` files are durably preserved under `legacy/scr-revision-15-planning/.codex/` with original-path maps, then deleted from product.
18. Four ITM-0003 worktrees were removed. Use MAIN and durable bundle locators. Current index owns complete current/history guidance and root-metadata distinctions.
19. Installed `docs/RESET-MODULE-INDEX.md` SHA-256: `5cc7a6fa170734a74d7046df1a613c407668239c819766a990eb014dcfd02390`.
20. Installed `docs/DEVELOPER-GUIDE.md` SHA-256: `eb701fd964c531cc3830068c2f81004a159ed9fb13dc7df37294f1833a971fed`.
21. Installed `docs/SDLC-DEVELOPER-GUIDE.md` SHA-256: `370fde2c73c2c6fe55feb00181303bffb3c2d0a69cb32bd0f8cdcb6c86cf11a5`.
22. Installed `docs/audits/SDLC-MIGRATION.md` SHA-256: `d2b03465068fa389df17fdbb302e3b3142ee571c8f885db2e4868531e3dbf078`.
23. ITM-0006 updates index only for actual final canonical/archive/readiness links. Completed historical/current guidance remains authoritative.

### Legacy and source facts

1. Legacy checkout: `/home/fudya/devel/scr/.codex/worktrees/REQ-0001-GOAL-COUNT-SYSTEM-RESETS`, branch `sdlc-req/req-0001-goal-count-system-resets`.
2. Observed legacy HEAD: `7610f9249db5640e7db82fbed20d23ff1f3b6c6d`. Git worktree metadata: `/home/fudya/devel/scr/.git/worktrees/REQ-0001-GOAL-COUNT-SYSTEM-RESETS`.
3. Observed state includes staged renames/additions, unstaged source/tooling changes, deleted package paths, and unique untracked revision 8–15/package/recovery evidence.
4. Orphan source: `/home/fudya/devel/scr/.codex/worktrees/REQ-0001-GOAL-COUNT-SYSTEM-RESETS-round-1/payload`. Its package-state and release bytes need preservation.
5. Legacy root `var` and `admin` are symlinks. Record link metadata only. Never traverse these targets during archive discovery or restoration.
6. Bounded metadata audit covered 403 entries and 2086792 regular bytes across explicit source/docs/tool/test/skill roots and orphan payload. All observed uid/gid were 1000.
7. This partial audit found no access errors. It does not prove whole-workspace completeness, all xattrs, ignored-file coverage, or archive restoration feasibility.
8. Native `/usr/bin/readelf` and `/usr/bin/tar` exist. Host `file`, `getfattr`, and `getfacl` were absent. Managed Python exposes metadata/xattr APIs.
9. Current `toolchain_runtime_verify` and `toolchain_install_verify` depend on host `file`. Existing functional test covers tools and tiny ARM smoke compile.
10. `ArtifactSource.read_entry` preserves regular bytes/mode. TAR/Git containers plus metadata manifests must preserve richer archive properties.
11. Original `var/` byte reads, extraction, package actions, module builds, and toolchain mutation were not part of planning audit.

| # | Input | Exact pin and destination |
| --- | --- | --- |
| 1 | Legacy `sdlc/requirements/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/src/scr_reset_monitor/scr_reset_monitor.c` | SHA-256 `3377a2ca4fa77f29958234282d1d1ce0d6eaccb5526475ce0a6517df18c7fb5e`. canonical `src/scr_reset_monitor/scr_reset_monitor.c` |
| 2 | Legacy same-directory `Makefile` | SHA-256 `a4d90d460a003f43d60e7d479615b2f61c81e6cd0c3d31fa82b0c68d777f9e3d`. canonical `src/scr_reset_monitor/Makefile` |
| 3 | `var/kernelDeb_2.0.0.0_3.10.105_including_RS485_ext_driver__16_05_2018.tar.gz` | Historical pin `a786b745424c93946c2e1bbcabae8325e3f95c58c3308c5e0160478860b01a3c`. fresh no-atime verification during approved execution |
| 4 | `var/Kernel_2.0.0.0_3.10.105_MSD_README.txt` | Historical pin `7f6ddc8643e043f12029ed40549a219237a5d6aa0a56c25dc20b8a2da40b6eac`. fresh no-atime verification during approved execution |
| 5 | Managed compiler archive | `linaro-arm-linux-gnueabihf-4.8-2014.04`, SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152` |
| 6 | Managed runtime | `ubuntu-trusty-i386-2019`, seven package pins in `lets/etc/toolchain/toolchain.conf` |

1. Both module pins matched independent no-atime reads during planning. Those reads preserved observed file stat fields.
2. Preserve current sync-retry behavior in `scr_claim_guard`, `scr_create_record`, `scr_verify_identity`, and `scr_retry_worker`. Import exact bytes, without redesign.
3. Vendor evidence reports `3.10.105-imx6`, GCC `4.8.4`, build `#4`. Prior hardware reports build `#5`.
4. Managed GCC is `4.8.3` prerelease, banner `Linaro GCC 4.8-2014.04`. Offline preparation cannot prove running-kernel compatibility.

## Design

1. **Fit:** Finish migration through existing item/chain engine. Place two product inputs under `src/scr_reset_monitor/`. Fix host preflight inside existing toolchain helper.
2. **Patterns:** Reuse pinned compiler/runtime verification, LETS wrappers, artifact publish/restore/verify, original-path maps, independent validation, and detached exact-pair QA.
3. **Context:** One block owns archive, canonical inputs, toolchain, docs, and readiness handoff. Dependencies stay within block. Existing safety engine remains unchanged.
4. Archive containers retain links, metadata, index payload, patches, and Git history. Independent disposable restoration proves recoverability before retirement.
5. Product docs identify stable archive/provenance locators. Managed reports identify final source and complete INPUT. Independent RESULT remains separate, without circular hashes.
6. Independent ITM-0001 planner consumes frozen readiness foundation. Coordinator commits checked replacement plan through LETS without approval. Later binding acknowledgement resolves final ITM-0006 pair externally.
7. Foundation bundle precedes replacement plan. Replacement references only frozen source/foundation, never final ITM-0006 INPUT or RESULT. Final INPUT can record replacement revision/locator.
8. External acknowledgement binds final pair to that plan after promotion. Independent read-only closure verifies binding before DONE. Neither closure nor later plan revisions enter accepted INPUT.

## Out of scope

1. Any `scr_reset_monitor.ko` compilation, vendor kernel/helper rebuild, module behavior change, module load, reset-cause feature, or ITM-0001 approval/execution.
2. Source-image payload access, image copy/mount/mutation, quarantine recovery, marker clearance, package installation, hardware access, flashing, reboot, or physical output.
3. Privilege escalation, host/global dependency installation, compiler/runtime replacement, or weakening architecture/hash/ownership/environment checks.
4. Broad runtime scans, relocation of `.lets` control state, shared toolchain cleanup, normal Git history removal, or legacy REQ resumption/obsoletion.
5. Import of legacy packages or unrelated source into product. Archive preservation does not activate archived scripts, instructions, packages, or hardware claims.
6. Forced worktree removal, stash/reset, discarding dirty edits, rewriting hashed historical reports, or claiming complete recovery for unreadable material.

## Safety

1. This is source/offline readiness work. No image modification or delivered Debian package applies. Package/hardware acceptance remains inapplicable, not waived or passed.
2. Future image change requires hardware-required marker before approval, reversible Debian ownership, maintainer scripts, immutable first backups, upgrades, architecture checks, and ownership/conflict detection.
3. Future uninstall of all delivered packages must restore bytes, types, ownership, modes, timestamps, symlinks, hardlinks, xattrs, and moved/added/deleted paths.
4. Future functional/package tests require shared image lock from copy through mount/install/test/uninstall/restoration/unmount/cleanup and final source proof. Ordinary leases cannot replace it.
5. Cleanup/restoration failure retains quarantine and blocks reuse until separately approved recovery succeeds. Current protected image/runtime paths stay untouched and logically quarantined.
6. Future hardware procedure requires explicit developer authority and exact device/image/package version/hash, expected behavior, observed behavior, logs, rollback, and verbatim confirmation.
7. Plan/SHOW approval, historical reports, and automated tests establish no hardware success or device authority. This plan schedules no real-hardware procedure.
8. PRESERVE original `var/` source images, kernel archive, and README bytes/metadata. Only two named kernel inputs permit later approved no-atime reads.
9. REQUIRE `O_NOATIME` and no-follow source descriptors, stable pre/post metadata, safe ownership/access, and bounded extraction outside `var/`. No atime-changing fallback.
10. EXCLUDE `.lets`, `.codex/sdlc` runtime siblings, original `var/`, image roots, shared toolchains, and external symlink targets from archive traversal.
11. CAPTURE excluded boundary names/dispositions without traversal. Preserve required old content via existing durable records or explicit retained locations.
12. FAIL closed on unreadable unique material, unstable source, unsupported metadata, insufficient space, unsafe archive members, or unresolved ownership.
13. KEEP dirty legacy workspace intact with explicit dormant disposition and zero offline build dependency. Exact retained exceptions cannot become fake archive PASS.
14. REQUIRE archive restore equality for bytes/types/modes/uid/gid/mtime/atime/link targets/hardlink topology/xattrs and staged/unstaged/untracked/history state.
15. RECORD inode/device/ctime as capture provenance. Fresh filesystem restoration cannot generally reproduce inode or ctime. Never require or claim such equality.
16. PRESERVE main edits and index. Use `GIT_OPTIONAL_LOCKS=0` on every read-only legacy status/diff/ls-files probe. Capture raw index/shared-index dependencies and staged objects before archive. No update-index, source-ref mutation, force-add, stash, reset, or manual ledger changes. Restore writes target disposable repository only.
17. STORE all generated capture scripts, manifests, proofs, logs, and reports under `.codex/sdlc/artifacts/items/ITM-0006/` with explicit stage and purpose.
18. PUBLISH explicit regular archive/report manifests through LETS. Binary TAR/Git bundles retain internal metadata. Base64 alone proves no metadata fidelity.
19. REQUIRE exact `--expected-artifacts DIGEST` on verified/approve/settle/prepare-promotion/promote. Missing index never downgrades existing bundles to source-only.
20. STOP after three failures at same stage, tooling blocker, safety failure, or material scope/authority change. Preserve evidence and owned ordinary-lease cleanup.
21. ROLLBACK product changes through reviewed reverse diff. Restore archived content only into conflict-free disposable locations until separately authorized original-path restoration.
22. RETAIN immutable bundles, original-path maps, branch history, current ledger checkout, locks/quarantine, and all unresolved originals throughout rollback.

## BLK-0001 — COMPLETE OFFLINE REBUILD READINESS

Product ownership: `lets/lib/devenv/toolchain.sh`, `tests/toolchain/run.sh`, exactly two `src/scr_reset_monitor/` files, `docs/RESET-MODULE-BUILD.md`, and narrow final links in `docs/RESET-MODULE-INDEX.md`. Existing compiler configuration, wrappers, safety engine, and historical payloads remain read-only.

Managed ownership: `/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0006/{implementation,qa}/`, including archive containers, metadata manifests, source provenance, restoration evidence, readiness, and binding records. Independent roles own their reports. Coordinator owns workflow state and separate ITM-0001 unapproved-plan commit.

All relative product paths refer to coordinator-assigned absolute ITM-0006 worktree. Main legacy sources remain read-only except separately proved clean redundant-path retirement in TSK-0004. No cross-block dependency exists.

Worker ownership: TSK-0001 owns archive/history artifacts. TSK-0002 owns only `lets/lib/devenv/toolchain.sh`, `tests/toolchain/run.sh`, and toolchain-preflight artifacts. TSK-0003 owns two canonical module files, vendor/source provenance artifacts, and its disposable scratch. These tasks have disjoint writes and can run concurrently. Coordinator serializes shared artifact publication. TSK-0004 owns restoration/disposition reports and documentation. TSK-0005 owns readiness foundation/rebuild handoff. TSK-0006 owns final INPUT/handoff. Independent validation occurs at block boundary. Early independent archive-fidelity ACK remains mandatory before actual retirement. No per-task generic unit reruns without changed behavior.

### TSK-0001 — CAPTURE BOUNDED LEGACY ARCHIVE AND HISTORY

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. VERIFY all prerequisite DONE states and final installed source/INPUT/RESULT against approved Context before execution.
2. RECORD final prerequisite identities and ITM-0003 index hash in managed `implementation/prerequisites.json`.
3. INVENTORY exact legacy checkout and orphan payload through no-follow, no-atime bounded metadata traversal. Exclude protected Safety boundaries.
4. RECORD each permitted path, type, size/hash, mode, uid/gid, atime/mtime, links, xattrs, hardlink group, Git state, and original-path map.
5. RECORD excluded paths, owner/access limits, ordinary claims/leases, namespace-limited mount/loop observations, and active references in `implementation/legacy-inventory.json`.
6. INCLUDE unique revision 8–15 evidence, historical package bytes/hashes, source/build/recovery tooling, hardware reports, and ignored permitted artifacts.
7. CAPTURE legacy HEAD/ref history, raw index, stage mappings, staged/unstaged binary patches, untracked bytes, and every index-referenced object.
8. PRESERVE shared-index dependencies and staged deletion/rename/mode/symlink distinctions. Retain reachable Git history through explicit branch bundle or equivalent complete Git object archive. Branch bundle alone cannot retain uncommitted staged blobs. Archive index-only objects explicitly, including every stage number and referenced blob SHA.
9. RECORD package version/hash and historical acceptance/failure limits. Never execute archived package scripts or promote historical hardware reports to new acceptance.
10. CALCULATE exact selected byte/member totals, archive expansion bounds, available disk/memory, and publication overhead before capture.
11. CREATE regular TAR/Git containers under managed `implementation/archive/`, with metadata manifest and repeatable capture/restore procedure.
12. SEGMENT large payloads into bounded regular parts when required by measured publication memory. Record part order, size, hashes, and total reconstruction bound.
13. REJECT absolute/traversal members, unsafe types, symlink/hardlink escapes, duplicate paths, source races, and unbounded expansion before extraction.
14. PRESERVE external boundary symlink text as inert metadata. Never follow it or restore it into live runtime locations.
15. PUBLISH archive, metadata, and provenance as explicit INPUT stage `implementation` through `./bin/lets sdlc artifacts publish`.
16. RECORD durable archive bundle locator in `implementation/archive-provenance.json`. Keep self-digest/publication acknowledgement outside hashed archive report.

**Done when**

1. Every allowed legacy path has exact archived or retained disposition. Unique staged/unstaged/untracked/ignored content needs explicit coverage beyond partial planning inventory. Protected, reproducible, or dormant exclusions need exact reasons. Unique contents and staging distinctions remain recoverable candidates, pending independent restore.
2. Complete selected Git history, HEAD, raw index, index objects, staged/unstaged binary patches, untracked content, packages, and hardware evidence have durable locators.
3. Bounds, ownership/access, no-follow/no-atime capture, xattr capability, exclusions, and source-stability evidence are recorded. No protected traversal or privilege change occurs.
4. INPUT includes binary containers with internal metadata and original-path mappings. Archive sources remain intact. No retirement or complete-restoration claim occurs yet.
5. Required unreadable unique content blocks full recoverability acceptance. Honest retained exception preserves original and bars deletion until separate resolution.
6. ITM-0002 original/current 96-payload maps and ITM-0003 additional collections remain referenced without duplicate ownership or rewritten historical bytes.

### TSK-0002 — RESTORE NATIVE TOOLCHAIN PREFLIGHT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. UPDATE `toolchain_runtime_verify` and `toolchain_install_verify` in `lets/lib/devenv/toolchain.sh` to share locale-stable native `readelf -h` validation.
2. REQUIRE successful native reader, valid header, ELF32, little-endian data, and Intel 80386 machine. Apply to loader and every allowlisted compiler/binutils binary.
3. KEEP archive/runtime hashes, manifests, license evidence, compiler banner, allowlists, executable checks, link/ownership containment, and environment sanitation.
4. REJECT missing native reader and malformed/truncated files before managed binary execution. Avoid managed-readelf recursion through `toolchain_load`.
5. EXTEND `tests/toolchain/run.sh` with actual valid-i386, wrong-class, wrong-machine, wrong-endianness, malformed-file, and missing-reader fixtures.
6. EXERCISE real header parsing and rejection. Do not replace wrong-architecture bytes with mock error strings or bypass hashes on installed toolchain.
7. RUN shell syntax, `./bin/lets toolchain info --json`, all allowlisted tool version checks, and existing toolchain functional/smoke suite.
8. RECORD exact commands, exits, tool hashes/banner, fixture identities, and managed tiny ARM object in `implementation/toolchain-preflight.json`.

**Done when**

1. Managed info reports verified original compiler/runtime without host `file`, global install, compiler replacement, or validation bypass.
2. Actual invalid class/machine/endian/malformed/missing-reader cases fail closed. Valid installed i386 runtime and all allowlisted tools pass.
3. Existing `managed_toolchain_smoke` produces ELF32 ARM object through LETS. No reset-module compilation or vendor helper rebuild occurs.
4. Pinned manifests/hashes/banner, ownership/link containment, and environment sanitation remain effective. Source/helper regression evidence covers changed behavior.
5. Independent validator can reproduce both successful preflight and each rejection from retained fixtures and commands.

### TSK-0003 — IMPORT CANONICAL INPUTS AND VERIFY VENDOR PROVENANCE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. COPY only pinned legacy `scr_reset_monitor.c` and `Makefile` into assigned product `src/scr_reset_monitor/` through safe no-atime reads.
2. VERIFY both hashes from Context before and after import. Record origin, legacy HEAD/index/working-state distinction, and review limits.
3. PRESERVE `scr_claim_guard`, `scr_create_record`, `scr_verify_identity`, and `scr_retry_worker` bytes. No other legacy code/package enters product.
4. RECORD original named kernel archive/README metadata before access. Open only those two files with no-atime/no-follow descriptors.
5. VERIFY exact Context pins and source stability. Copy kernel inputs into item-owned scratch outside `var/` without changing original metadata.
6. VALIDATE member names, types, roots, link targets, member counts, and expansion bounds before disposable extraction.
7. EXTRACT only into safe disposable offline workspace. Do not execute archive code, rebuild helpers, compile module, or open image payloads.
8. CAPTURE `.config`, generated configuration/release headers, `Module.symvers`, `System.map`, `vmlinux` build ID, kernel release, compiler provenance, and relevant hashes.
9. RECORD supplied build `#4` versus historical hardware `#5`, and GCC `4.8.4` versus managed `4.8.3` prerelease. Preserve uncertainty.
10. VERIFY original kernel-input bytes and restorable metadata after reads using same no-atime discipline. Preserve source image by excluded-access boundary.
11. PUBLISH `implementation/source-provenance.json`, `vendor-provenance.json`, exact command logs, and safe extraction procedure as managed INPUT.
12. REMOVE only item-owned disposable extraction after evidence retention. Kernel source archive and README remain original inputs for later approved ITM-0001.

**Done when**

1. Canonical product files match both exact pins and work independently of legacy checkout. Current sync-retry code remains unchanged.
2. Vendor archive/README pins and metadata preservation pass. No silent atime-changing fallback, original image read, kernel mutation, or archive-path escape occurs.
3. Vendor config/header/symbol/build provenance has exact locators and hashes. Required missing or inconsistent input blocks readiness with evidence.
4. Build numbers/compiler differences remain explicit. Offline facts establish no running-kernel compatibility, module success, package acceptance, or hardware success.
5. Later ITM-0001 can identify inputs through canonical paths and durable provenance without previous rebuild or legacy workspace dependency.

### TSK-0004 — PROVE ARCHIVE RESTORATION AND RESOLVE LEGACY REFERENCES

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001, TSK-0003 |
| 2 | model | high |

**To do**

1. REQUEST coordinator-dispatched independent validator restoration from published archive bundle into fresh disposable checkout through public `artifacts restore` and `artifacts verify`.
2. RECONSTRUCT segmented containers within recorded bounds. Extract only reviewed members into isolated destination, with no live external links.
3. COMPARE every restored byte/type/mode/uid/gid/atime/mtime/link/xattr and hardlink group against capture. Compare permitted-source pre/post metadata separately. Use no-atime reads during comparison and restore directory timestamps after child extraction.
4. RESTORE archived Git history, raw index and dependencies, staged/unstaged changes, deleted paths, and untracked content in isolated Git/worktree layout.
5. COMPARE original and restored HEAD/tree/object identities, index entries/bytes, binary patches, status categories, and package/evidence hashes.
6. RECORD capture inode/device/ctime separately from restorable properties. Never claim fresh inode or ctime equality.
7. PUBLISH independent `qa/archive-restoration.md` and machine-readable comparison as historical QA INPUT for final readiness selection.
8. VERIFY archive/staging/source completeness, claims, leases, active references, and visible mounts/loops before any proposed retirement.
9. ***if*** candidate is dirty, claimed, referenced, protected, unreadable, incompletely restored, or namespace visibility is insufficient ***then***
   9.1. KEEP exact original path intact.
   9.2. RECORD dormant retained disposition, unresolved reason, owner, and zero offline build dependency.
10. ***if*** candidate is clean, unclaimed, fully preserved, independently restored, unreferenced, and concretely authorized ***then***
    10.1. REMOVE only that redundant path through supported non-force worktree operation or bounded orphan cleanup.
    10.2. RECORD exact removed path, preconditions, restoration locator, and rollback procedure.
11. PRESERVE `sdlc-req/req-0001-goal-count-system-resets`, normal Git history, current ledger checkout, active control state, and all protected runtime exclusions.
12. WRITE final `implementation/archive-provenance.json` and `legacy-disposition.json` with every retained/archived/removed path and stable bundle/member mappings.
13. UPDATE `docs/RESET-MODULE-INDEX.md` narrow ITM-0006 entries to final canonical sources, archive/provenance locators, retained exceptions, and exact recovery commands.
14. ADD `docs/RESET-MODULE-BUILD.md` describing offline prerequisites, canonical pins, managed compiler, vendor provenance, limits, and separate ITM-0001 approval gate.
15. VERIFY all changed live links and historical index consumers after materialization. Keep historical embedded paths unchanged with external original-path mappings.

**Done when**

1. Independent fresh restoration proves complete selected archive content, metadata, staging distinctions, and history before any original removal.
2. Dormant dirty workspace can remain intact. Every leftover has exact reason and no active rebuild dependency. No unsafe cleanup is required for completion.
3. Unreadable or unrestorable required unique material cannot masquerade as complete recovery. Original remains and relevant acceptance stays blocked.
4. Every actual retirement is clean/unclaimed/unreferenced and independently restorable. No force/stash/reset, sole-file loss, branch removal, or legacy REQ resumption occurs.
5. ITM-0003 index remains resolving through stable immutable archive/provenance locators. Current documentation has no dependency on removed or dormant source paths.
6. Original/current 96-payload recovery, ITM-0003 extra archives, revision 8–15, historical packages, orphan payload, source/tooling, and hardware reports remain accounted for.
7. Product root `contracts/` and `evidence/` remain absent. Generated implementation/QA reports remain managed artifacts, never force-added source files.
8. Build guide states current observable-boot scope and static/offline limits. No reset-cause or hardware claim expands imported source behavior.

### TSK-0005 — VERIFY READINESS AND PREPARE UNAPPROVED REBUILD PLAN

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002, TSK-0004 |
| 2 | model | high |

**To do**

1. FREEZE final product source through coordinator-owned authorized commit. Record actual commit/tree and canonical/doc hashes in `implementation/readiness-foundation.json`.
2. VERIFY current AGENTS/skills/roles/guides and installed LETS item/chain/safety interfaces against completed prerequisite contracts.
3. RUN applicable task unit/system/safety/toolchain gates and shell syntax/whitespace checks. System gate uses owned stack lease. Retain independent validator evidence separately. Reuse unchanged passing evidence within each role unless changed behavior, new failure, or unresolved concern requires repetition.
4. RECORD Python style as inapplicable for Bash/C/docs-only product diff. Apply style gate to any approved changed-existing/new Python source, excluding deletions.
5. VERIFY no conflicting claims/ordinary leases or active build references. Distinguish namespace-visible mount/loop facts from global unknowns.
6. KEEP image quarantine held and excluded from offline build. Readiness cannot require recovery, image access, marker removal, or broad runtime scans.
7. PUBLISH frozen readiness foundation, gate evidence, canonical/vendor provenance, and archive/reference proofs as explicit managed INPUT.
8. REQUEST coordinator-dispatched independent `sdlc_planner` for replacement ITM-0001 plan using frozen source/foundation locators, canonical files, and retained old r1.
9. REQUIRE replacement scope: two independent clean vendor-tree builds, byte-identical `.ko`, static ELF/release/vermagic/symbol/relocation evidence, and durable artifact delivery.
10. REMOVE duplicated source-import, archival, toolchain-fix, and migration ownership from replacement. Keep kernel/archive metadata safety and compatibility limits.
11. REQUIRE planner to use current template and `./bin/lets sdlc items plan check ITM-0001`. Planner edits draft only.
12. HAVE coordinator commit independently checked replacement through `./bin/lets sdlc items plan commit ITM-0001`, preserving old r1 history.
13. VERIFY ITM-0001 stays BACKLOG with null current approved revision. No schedule/build/load follows from migration authority.
14. RECORD exact replacement revision, PLAN hash, ledger locator, independent check, and developer-approval obligation in `implementation/rebuild-handoff.json`.
15. REFERENCE immutable readiness foundation in replacement plan. Resolve later final ITM-0006 pair through external binding acknowledgement, avoiding circular final-result hashes.

**Done when**

1. Required task source checks pass with exact command/exit/log evidence and no skipped required task gate. Independent validator judges task criteria. Final detached QA and item acceptance remain pending.
2. Readiness foundation identifies actual source commit/tree, canonical pins, vendor provenance, archive restore proof, active interfaces, unresolved protected exceptions, and rollback.
3. Fresh independently checked replacement ITM-0001 plan is committed UNAPPROVED, current, canonical-path based, and free of duplicated migration tasks.
4. Old ITM-0001 r1 remains historical. Current plan requires separate explicit developer approval before scheduling or either module build.
5. No prerequisite circularity exists: replacement consumes frozen source/foundation, while later external binding identifies final migration INPUT/RESULT.
6. Original `var/` bytes/metadata, complete permitted legacy history, durable managed artifacts, active control state, and quarantine remain preserved.

### TSK-0006 — PUBLISH COMPLETE READINESS INPUT AND CONSUMER HANDOFF

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0005 |
| 2 | model | high |

**To do**

1. WRITE `implementation/readiness.json` and `readiness.md` with criterion map, actual source commit/tree, canonical paths/hashes, prerequisite pairs, archive/rollback locators, checks, and retained exceptions.
2. INCLUDE exact fresh ITM-0001 plan revision/hash, independent check evidence, and separate approval obligation. Assert no reset-module compilation occurred.
3. SELECT complete INPUT: foundation, provenance, archive containers or immutable bundle references, independent restoration proof, gates, readiness, and rebuild handoff.
4. PUBLISH through managed artifacts command with stage `implementation`. Exclude final self-digest, mutable publication sidecars, and final QA RESULT.
5. RESTORE selected INPUT through `artifacts restore` in fresh disposable checkout. Run `artifacts verify` against durable bundle and restored immutable copy.
6. COMPARE selected report/container bytes, sizes, modes, hashes, and original-path maps. Resolve every referenced earlier archive bundle and independent restoration proof.
7. RECORD actual restore/verification commands, exits, and comparisons. Keep publication acknowledgements and final-selection verification sidecars outside their own hashed INPUT.
8. FREEZE complete evidence selection. Earlier restoration-reference proof can enter INPUT. Final selection requires separate restore/verification evidence without self-digest rewriting.
9. MARK final detached QA RESULT, exact-pair approval, promotion, installed identity, and chain completion as PENDING item acceptance.
10. PROVIDE coordinator complete diff, task checks, selected immutable INPUT locator, restore evidence, rollback, pending exceptions, and consumer instructions.
11. REQUEST independent block validation through coordinator. Implementation worker neither self-validates nor performs final QA, approval, or promotion.

**Done when**

1. Readiness report supplies complete engineering evidence and honest retained exceptions for independent task validation. Final item acceptance remains pending.
2. Complete INPUT is durable and restored through public artifact commands. Actual byte/mode/hash/path comparisons pass for final selection and referenced archive evidence.
3. Handoff states every remaining snapshot/QA/RESULT/approval/promotion obligation and exact artifact guards. No future acceptance result is needed to validate task.
4. Actual source commit/tree, complete INPUT locator, current UNAPPROVED ITM-0001 plan revision, and task restoration evidence resolve without self-reference.
5. All original/current workflow payloads remain recoverable through durable records and verified archive restore. Product `contracts/` and `evidence/` remain absent.
6. Current guide/index/build consumers resolve. No active rebuild dependency targets dormant legacy workspace, failed image, four clones, or protected recovery namespace.
7. ITM-0001 remains unapproved and unbuilt. Independent validator can assess every task criterion without final QA RESULT, installed commit, or chain-complete claim.

## Item acceptance AFTER task validation

These duties follow independent validation of all six tasks and block assembly. They are mandatory item-completion gates, never implementation-task prerequisites.

1. ASSEMBLE validated block into retained integration through coordinator/integration roles. Present complete diff and preserve unrelated edits.
2. SNAPSHOT integration source and complete selected INPUT through supported worktree ceremony. Record exact `(source_tree, input_digest)` pair.
3. ***if*** integration changes frozen source, selected evidence, or consumer references ***then***
   3.1. REFRESH readiness foundation and affected downstream evidence, including current unapproved ITM-0001 plan when its inputs change.
   3.2. REPEAT affected independent validation before final QA. Never reuse stale source/INPUT acceptance.
4. DISPATCH independent QA against detached snapshot and immutable INPUT. Implementation worker cannot perform this role for own work.
5. REQUIRE final independent QA unit and system gates on final applicable snapshot. System gate uses owned stack lease.
6. REQUIRE applicable safety/toolchain/style checks and every acceptance criterion, including durable restoration, canonical pins, metadata preservation, and historical/current index links.
7. REUSE unchanged passing checks within same role. Repeat only for changed behavior/source/evidence, new failures, unresolved concerns, or required changed-merge verification.
8. REQUIRE QA to publish separate RESULT stage `qa`, bound to exact source tree and INPUT digest. Historical QA INPUT cannot substitute.
9. RECORD verification only after passing independent QA and matching RESULT: `worktree verified ITM-0006 --expected-tree TREE --expected-artifacts DIGEST`.
10. SHOW exact source/INPUT pair, pinned RESULT, complete diff, tests, restore proof, rollback, and pending protected/hardware obligations.
11. RECORD exact-pair approval through coordinator under applicable recorded authority. Plan approval alone never establishes SHOW or hardware acceptance.
12. USE `worktree approve ITM-0006 --expected-tree TREE --expected-artifacts DIGEST` for accepted pair. Settle through `worktree settle ITM-0006 --expected-tree TREE --expected-artifacts DIGEST --message TEXT`.
13. ACQUIRE maintree before preparation. Use `worktree prepare-promotion ITM-0006 --expected-artifacts DIGEST --json`.
14. VERIFY prepared commit. Changed merge tree requires system verification. Changed reviewed source/INPUT requires refreshed independent acceptance.
15. PROMOTE exact prepared commit through `worktree promote ITM-0006 --expected-commit COMMIT --expected-artifacts DIGEST`.
16. VERIFY actual installed commit and final source/INPUT/RESULT binding before completion bookkeeping. Missing artifact index cannot downgrade existing bundles to source-only.
17. RECORD external binding acknowledgement with final source/INPUT/RESULT, installed commit, current unapproved ITM-0001 plan locator, and consumer resolution instructions.
    17.1. REQUEST independent read-only closure verification of installed identities, replacement-plan applicability, unchanged accepted pair, and external consumer binding.
    17.2. RECORD closure verdict through supported ledger/log commands before item DONE. Keep closure PENDING during pre-promotion QA.
18. KEEP acknowledgement outside accepted INPUT through supported bookkeeping/publication. New selected INPUT requires fresh snapshot/QA and matching RESULT.
19. VERIFY all original/current workflow payloads remain recoverable through durable records and independent archive restoration. Product `contracts/` and `evidence/` remain absent.
20. VERIFY current guide/index/build consumers resolve without dormant legacy source, failed image, four clones, or protected recovery namespace dependencies.
21. VERIFY ITM-0001 remains unapproved and unbuilt. Final readiness establishes offline engineering prerequisites, never module, image, package, or hardware success.
22. RELEASE only owned ordinary leases on every exit. Preserve quarantine, shared image lock policy, original sources, normal history, and unresolved protected exceptions.
23. MARK item DONE only after all applicable gates and installed promotion pass. Derive chain completion only after every required chain member is DONE.
24. REPORT final pair/RESULT/installed identities, archive/rollback locators, fresh unapproved rebuild plan, retained exceptions, and separate future hardware obligations.
