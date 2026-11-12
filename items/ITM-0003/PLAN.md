# ITM-0003-SDLC-LEGACY-DOCUMENTATION-CLEANUP — Plan

## Goal

Deliver useful current-versus-historical reset-module index and safe developer image guidance. Preserve historical bytes, hashes, modes, and provenance. Retire ten active-looking revision-15 files only after independent durable restoration proof. Make current scope, acceptance limits, pending work, and evidence locations clear before ITM-0006 starts.

## Context

### Customer source

> Issue tasks cleanup where needed suggest what leftovers of the previous SCR SDLC need to be removed
>
> Later user ruling:
> Create a new SDLC chain that transits from old to new SDLC. Add all items to it (except rebuilding the module). The state of the repo after the chain must be "ready for kernel module rebuild" according to the new ceremonies
>
> Later user ruling:
> All these folders belong to the planning, implementation and QA stage and should be managed under .codex/sdlc as in Specz (with claude)

Standing authority, verbatim:

> Approve this and pre-approve all other items in this chain until the migration is complete

1. Chain CHN-0001: ITM-0002 → ITM-0005 → ITM-0004 → ITM-0003 → ITM-0006. Execution requires ITM-0004 DONE.
2. Planning checkout: `/home/fudya/devel/scr`, branch `feature/monit-stability`. Initial audited base: `62b3a9e4bf3d50ad09ea71c17164adcbcf65fe2e`. Final installed planning base: `41bf1462c5ff6f6de5149a24ff331f4ddc91ee18`.
3. Draft stays UNAPPROVED. Coordinator owns approval bookkeeping against checked revision and recorded standing authority. Planner neither approves nor commits.
4. Effective REVIEW decisions: none. Source request/history: `.lets/sdlc/logs/ITM-0003/intake-current.json` and `./bin/lets sdlc items show ITM-0003`.
5. Relevance: CONFIRMED. Existing developer guide permits raw-image writes. root release record stops at revision 6. Ten revision-15 artifacts remain tracked.
6. Readiness: READY for coordinator approval. ITM-0004 DONE, installed source/INPUT/RESULT, and fresh installed guide/interface checks all verified below. No unresolved planning questions.
7. Preparation began before prerequisite completion. Final readiness uses installed evidence, never candidate evidence alone. ITM-0003 remains BACKLOG r0 until coordinator approval.

### Verified inputs and durable locations

| # | Input | Identity and use |
| --- | --- | --- |
| 1 | ITM-0002 final source | `9f6d26bcab95a09ac643eefa96c7817cac9d4aba`. installed commit `62b3a9e4bf3d50ad09ea71c17164adcbcf65fe2e` |
| 2 | ITM-0002 historical import INPUT | `6ebd9151f9187333775141e81b3b17d653074e70865de8213b11c2f54b778881`. original-path map for 96 former root payloads |
| 3 | ITM-0002 final INPUT | `d04ef0f55ec933559f8d6bb8f1c7986175a478ace786bd28dbf167fd7df29094` |
| 4 | ITM-0002 independent RESULT | `3f138507ca7f77937f42c36619b3011c4a6bb71835f6d519c0b3d9be7ebbd3ec`. binds row 1 source and row 3 INPUT |
| 5 | ITM-0005 source | `9f6d26bcab95a09ac643eefa96c7817cac9d4aba` |
| 6 | ITM-0005 final INPUT | `0dafde9ce21b89d7e82ef07378bed48a35016380eff27240fcadb786660002c5` |
| 7 | ITM-0005 independent RESULT | `407902732e2dd731785e465a0d9094aba1c395256fb1a29de733c4db0f35977d`. binds row 5 source and row 6 INPUT |
| 8 | Historical collection | `.codex/sdlc/artifacts/legacy/scr-pre-item/`. former `contracts/`, feasibility, revisions, and hidden retired snapshots |
| 9 | Assessment reports | `.codex/sdlc/artifacts/items/ITM-0005/implementation/{inventory.json,capture-log.md,disposition.md,recovery-proposal.md,consumer-contract.md,publication-proof.md}` plus explicit raw capture entries |
| 10 | Ledger bundle lookup | `artifacts/bundles/DIGEST.json` on `sdlc`. `./bin/lets sdlc artifacts list ID --json` identifies exact retained pairs |
| 11 | Artifact recovery | `./bin/lets sdlc artifacts restore --bundle DIGEST --json`. `./bin/lets sdlc artifacts verify --bundle DIGEST --json` |
| 12 | Immutable local copy | `.codex/sdlc/artifacts/snapshots/DIGEST/`. local presence alone does not prove durable acceptance |

1. ITM-0002 preserved 87 historical and nine current root artifacts. Consume existing bundles and original-path mappings. Do not re-import those payloads.
2. ITM-0005 reports 54 RECOVERY-REQUIRED entries, 21 unreadable texts, and 11 excluded suspected mount subtrees. Active runtime/source boundaries remain KEEP.
3. Failed image and four clones remain excluded from offline build inputs. Image identities, restoration, and reclaimable capacity remain unproved.
4. Two recorded baseline atime drifts remain historical evidence. This item grants no metadata repair, privileged read, recovery, or quarantine clearance.
5. Historical guide hashes identify old capture context only. Current installed guide and interfaces require fresh source checks.
6. Planner baseline guide hashes: `docs/DEVELOPER-GUIDE.md` = `b286b0da115327370ffc3476539ca2b41ad72673dbc52492b54ecfed0888d9a7`. `docs/SDLC-DEVELOPER-GUIDE.md` = `7669ec50ca62f878df77d10d394af0ed7481a4abbe9446ffbae5485251a471a4`.
7. ITM-0004 changed current contract. These initial baseline hashes never stand in for final installed guide identified below.

### ITM-0004 installed verified pair

| # | Evidence | Exact identity or status |
| --- | --- | --- |
| 1 | Integration merge | `28f57def1bf905a51f0e0174cab77400a096ec1c` |
| 2 | Detached snapshot | `40f2a75c6594a0ffdf361ff07f9aa3c73c407ec0` |
| 3 | Source tree | `d3a5a0e1a757a80784ce1810e543912c2a91d8f0` |
| 4 | Bound INPUT, 19 entries | `0670aa05932f3a48d5693f884c8bef8e9adc2c684d56263ffc1e3a8ac6eac804` |
| 5 | Durable INPUT locator | `artifacts/bundles/0670aa05932f3a48d5693f884c8bef8e9adc2c684d56263ffc1e3a8ac6eac804.json` on `sdlc` |
| 6 | Immutable INPUT copy | `.codex/sdlc/artifacts/snapshots/0670aa05932f3a48d5693f884c8bef8e9adc2c684d56263ffc1e3a8ac6eac804/` |
| 7 | Consumer contract | `items/ITM-0004/implementation/consumer-contract.md`, SHA-256 `33c7441f5c30b3e9aca2c816b865b09ecf1cca01c50a1e296dca6267d1032f66` |
| 8 | Installed SDLC guide | `docs/SDLC-DEVELOPER-GUIDE.md`, SHA-256 `99908d49f8aa1986ef41e04222fddd87b8d47ed17b693a372de9d6cf35443555` |
| 9 | Independent validator | Coordinator reports all 20 criteria PASS and exact-pair ACK PASS |
| 10 | Integration gates | Unit 519 PASS. Style zero findings across four changed Python files |
| 11 | Final independent QA | All 20 criteria PASS. Unit 519/system 8/style zero findings across four paths. Fresh restoration: 19 entries, 76 copy comparisons |
| 12 | Installed acceptance | Commit `41bf1462c5ff6f6de5149a24ff331f4ddc91ee18`, exact row 3 tree. Fresh item status DONE at `2026-11-12T07:23:48 UTC`. Both tasks DONE |
| 13 | Independent RESULT | `954af6859a3e436bda98cf341d9b2d08096e39317daae4f4d097eced3ab6c618`, 26 entries. Public verification and QA ACK PASS |
| 14 | Durable RESULT locator | `artifacts/bundles/954af6859a3e436bda98cf341d9b2d08096e39317daae4f4d097eced3ab6c618.json` on `sdlc` |
| 15 | QA assessment SHA-256 | `9c5684b2f49dd8137cc146214ff61779e7bd004bea6dad20692138efddd509b0` |

1. Planner read consumer contract matching row 7 hash and guide from exact snapshot. Public artifact list confirms RESULT binds rows 3–4 exactly.
2. Final installed MAIN audit verifies row 12 commit/tree, clean worktree, row 8 guide hash, retained interface source, and ITM-0004 DONE. Coordinator recorded actual standing approval.
3. Installed wrappers remain `tools/sdlc/{package-init,test-package,verify-package,lock-run,models}.sh` through `sdlc.controllers.safety_cli:SafetyCliHelper.main`.
4. Private `SdlcPackageHelper.cmd_package_init` refuses absent `approved_state` before legacy lookup/output. Public adapter retains approved-plan, running-status, hardware-required, and assigned-output checks.
5. Private safety entry points refuse 27 retired ceremony names before repository access. Active item/chain commands and explicit historical transcript support remain.
6. `lock-run` routes original selected CLI verb and consumes exactly one leading separator. Remaining child argv, shared lock, and quarantine behavior remain intact.
7. Three wrapper usage labels change from `REQ-ID` to `ITM-ID`. Options, dispatch, and help exit `1` remain unchanged.
8. Consumer contract corrects frozen regression matrix's mistaken `Approved plan: revision 4` to actual approved revision 1. Preserve frozen bytes and correction together.
9. Consumer contract retains earlier pending fields and broad revision-15-unapproved wording. Exact-pair handoff and historical correction below supersede those capture limits additively.
10. No automated result proves real image restoration, package acceptance, hardware success, or current recovery authority.
11. Installed engine SHA-256: `bbf6c340affaa235d8308dbda8693a78c9f549c0e4e2d33eaa401ba5d759d243`. Installed adapter SHA-256: `102ed493300dc00745ba4b8af9d735a1bfcabf606fd889fa27518c5b325f13d6`.
12. Installed wrapper hashes match consumer contract: `package-init.sh` = `fe33310c0c325959d96982440c19888e724996580c51e813131735579dbb7db2`, `test-package.sh` = `00940e4c257aa31c1ba0eb85b82abc83fa7685f5ff5064adb9e7894e44848493`, `verify-package.sh` = `6e6e8718ee4b7bf3fc8708d85a342b405a256912a54cfb53edd9b78a8c73679a`.
13. Fresh three wrapper `--help` calls at `2026-11-12T07:23:56 UTC` show `ITM-ID` with original options. Each exits `1`, as documented. No package/image operation occurs.
14. Installed `cmd_package_init` and both CLI boundaries match refusal/separator contracts. `cmd_lock_run` retains before-lock and in-lock quarantine checks and continuous shared-lock child execution.

### Historical facts and correction

1. Root `RELEASE.md` describes revision-6 diagnostic evidence and says no production release/no DEB. Preserve its bytes and label its historical boundary externally.
2. Managed `contracts/module-internal.md` and `record-namespace.json` prescribe SRC/reset-reason behavior. Later observable-boot scope supersedes those prescriptions.
3. Current scope counts one observable event per boot reaching module initialization. Same-boot supported unload/reload adds no event. Empty durable records remain module-owned.
4. Reset causes, SRC/MMIO, physical-reset completeness, pre-module events, retained counters, and reset-loop mitigation remain excluded. Static/offline evidence cannot prove hardware compatibility.
5. Exact legacy checkout: `/home/fudya/devel/scr/.codex/worktrees/REQ-0001-GOAL-COUNT-SYSTEM-RESETS`, branch `sdlc-req/req-0001-goal-count-system-resets`.
6. Legacy implementation root: `sdlc/requirements/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/` inside that checkout. Its release, source, package work, and revisions 7–15 exceed root release scope.
7. Legacy checkout contains staged renames, unstaged changes, deleted package paths, and untracked evidence. Preserve every state. ITM-0006 owns complete archival/disposition.
8. Retained REQ ledger path: `docs/requirements/REQ-0001-GOAL-COUNT-SYSTEM-RESETS.md`. state: `docs/requirements/.state/REQ-0001-GOAL-COUNT-SYSTEM-RESETS.json`.
9. Retained round artifacts: `docs/requirements/artifacts/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/round-1/` on `sdlc`. Current lookup follows `./bin/lets sdlc sync`.
10. Audited mirror commit: `76a65b348290b604dd7bcec15c49b480eff14e25`. REQ document blob: `6aa7e3179305c0240fcfc52a2d923132557d31fc`. State blob: `f5756aa4f7986cceec5b376b9f7d663cc54cafa5`. Document SHA-256: `4d75d8bb130573bea07a01513ebf242ee090e82663003faa716975ba8fc2f1b0`. State SHA-256: `a36eafcfa825d2a8932e8e7d5571e6d9240b8eaab28960f5c278fcf77205f4c1`.
11. STALE handoff corrected: blanket “revision 15 unapproved” conflated different bytes. Local tracked draft SHA-256 is `8a139fe5726d538c58b2fce1e38d95c46fc4c6f39bfaa1830c9bbafbcd871153`.
12. Historical state records `approval.status: auto-approved` for revision 15 SHA-256 `8801ca2266b6f90afd0e1a937926d3d3f88f4965a67c233be1e8ae5862533618` at `2026-09-27T07:14:31+00:00`.
13. Event sequence `200` records that claim. State still has `plan.status: draft`. latest sequence `207` has T02 active. Preserve contradiction and exact identities.
14. `.codex/task-plan-rev15/manifest.json` references hash from paragraph 12. It does not prove equality with local draft from paragraph 11.
15. Historical auto-approval is evidence, not current developer authority. Local draft lacks matched approved-byte proof. No retired workflow resumption follows.
16. Preserve ITM-0005 and ITM-0004 report bytes. Add clarification that their unapproved-draft statements concern named local draft and bounded capture, not complete ledger chronology.
17. ITM-0001 remains BACKLOG, plan r1 unapproved/stale, depends on ITM-0006, and sits outside migration chain. Replacement plan requires separate explicit approval.
18. ITM-0006 owns canonical source import, final workspace archive, native `readelf` prerequisite fix, readiness evidence, and fresh independently checked UNAPPROVED ITM-0001 plan.

## Design

1. **Fit:** Add versioned `docs/RESET-MODULE-INDEX.md` as current reader entry point. Update current developer guidance and broken migration-audit links. Preserve historical payloads.
2. **Patterns:** Reuse `ArtifactSource`, explicit `ArtifactManifest`, `ArtifactUsecases.publish/restore/verify`, source-plus-INPUT snapshots, and independent QA RESULT. No artifact-engine change.
3. **Context:** Current `docs/SDLC-DEVELOPER-GUIDE.md`, final ITM-0004 consumer contract, and ITM-0005 evidence govern safety and current interfaces.
4. One block owns coupled archival, index, and guide work. Three sequential tasks keep archive proof before tracked-file removal. No cross-block dependency exists.
5. Index separates current accepted scope, historical design, observed evidence, failed/unproved acceptance, and pending work. Every claim carries exact source/identity and limits.
6. Index links root release, all former contracts/feasibility/revision collections, hidden migration history, retained REQ, dirty workspace, ITM-0001, and migration items.
7. Existing immutable bundles remain authoritative. New original-path mappings record duplicate or unique classification for each tracked revision-15 file.
8. Unique revision-15 bytes use `.codex/sdlc/artifacts/legacy/scr-revision-15-planning/`. Reports use `items/ITM-0003/planning/`, `implementation/`, or `qa/`.
9. Every live link must resolve at completion, either directly or through explicit tested recovery instructions. Historical embedded links remain unchanged and receive external mapping.
10. Future ITM-0006 source/archive paths remain pending text, never broken hyperlinks. Stable entry points are `items show ITM-0006` and `artifacts list ITM-0006 --json`.
11. Current index provides complete documentation acceptance now. ITM-0006 adds final preservation/readiness evidence later. Neither item inherits hardware authority.
12. No new runtime code, abstraction, or documentation-test framework. Use bounded link/reference, source-interface, byte/mode, and command-help checks.
13. Add one Plan-section sentence to `docs/SDLC-DEVELOPER-GUIDE.md` that locates mandatory final item gates after task validation. Preserve ITM-0004 Migration boundary changes.

## Out of scope

1. Kernel rebuild, module source import, module load, package build/install, device access, flashing, reboot, or physical-output tests.
2. ITM-0001 approval/execution, legacy REQ resumption, retrospective approval repair, or historical state/hash rewriting.
3. Broader legacy-workspace archival/removal, compiler prerequisite correction, and final chain readiness. Those remain ITM-0006 responsibilities.
4. Image reads, image copies, mounts, mutation, recovery, unlock, privilege escalation, and protected-runtime traversal.
5. Product changes to reset semantics, package lifecycle, image tools, Codex/Claude launchers, artifact engine, or SDLC ceremonies.
6. General skill cleanup, unrelated documentation rewrites, and any modification of original `var/` images, kernel archive, or README.

## Safety

1. This is source documentation and historical-artifact work. No delivered Debian package, package version/hash, image lifecycle execution, or hardware-required marker applies.
2. Package and hardware checks remain future obligations, never fictitious PASS results. Preserve all original image/kernel payload and metadata without reading them.
3. Future image changes require reversible Debian ownership, conflict/overlap checks, architecture matching, immutable first backup, and maintainer-script rollback.
4. Future uninstall must restore bytes, type, ownership, modes, links, xattrs, timestamps, and moved/added/deleted paths. Upgrades must preserve first baseline.
5. Future functional/package tests require source hashes and whole-image restoration evidence. One shared image lock spans copy, mount, install, test, uninstall, restoration, unmount, cleanup, and final source proof.
6. Cleanup/restoration failure retains quarantine and blocks reuse until separately approved recovery proves restoration. Ordinary leases and environment flags never establish image-lock authority.
7. Real-hardware procedure remains separate: identify device/image/package version/hash, explicit authority, expected behavior, logs, rollback, observed results, and verbatim developer confirmation.
8. Plan approval, historical authority, automated tests, and SHOW approval grant no flashing, reboot, hardware execution, recovery, or package acceptance.
9. Archive sources are ten explicit regular text files plus bounded new reports. Never enumerate `.codex/sdlc` runtime siblings or follow image/worktree symlinks.
10. Before any retirement, independent restore must prove bytes, SHA-256, size, mode, and original-path mapping. Failure preserves originals and stops retirement.
11. Product rollback reverses reviewed doc/deletion diff. Artifact rollback selects retained immutable bundles and conflict-free LETS restoration. Never overwrite conflicting files.
12. `.lets` control state, drafts, logs, leases, telemetry, and existing dirty legacy workspace remain in place. No force-add, stash, reset-hard, or unrelated edit removal.
13. Coordinator captures exact source tree and INPUT. Independent detached QA publishes separate RESULT for that pair, without self-reference.
14. Artifact-bearing `verified`, `approve`, `settle`, `prepare-promotion`, and `promote` require explicit `--expected-artifacts DIGEST`. Missing index cannot downgrade existing bundles.

## BLK-0001 — Preserve historical planning and complete current documentation

Ownership: `docs/RESET-MODULE-INDEX.md`, `docs/DEVELOPER-GUIDE.md`, narrow locator/current-interface updates in `docs/audits/SDLC-MIGRATION.md`, one Plan-section clarification in `docs/SDLC-DEVELOPER-GUIDE.md`, and retirement of ten listed revision-15 files. Managed deliverables belong under main `.codex/sdlc/artifacts/items/ITM-0003/` and `.codex/sdlc/artifacts/legacy/scr-revision-15-planning/`. `RELEASE.md`, old managed payloads, historical REQ, and legacy workspace are read-only.

### TSK-0001 — PRESERVE REVISION-15 PLANNING BYTES

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. VERIFY ITM-0004 DONE and final installed source/INPUT/RESULT against planner-approved consumer evidence before implementation starts.
2. INVENTORY `.codex/REQ-0001-revision-15-solution-plan.tmp.md` and nine `.codex/task-plan-rev15/` files: `acceptance.json`, `contract.md`, `interfaces.md`, `manifest.json`, and `tasks/T01.md` through `T05.md`.
3. RECORD exact path, bytes hash, size, permission mode, and tracked state in managed `implementation/revision15-inventory.json`.
4. COMPARE explicit candidate counterparts from retained REQ round artifacts, existing managed manifests, and accessible legacy text evidence. Never scan runtime roots.
5. CLASSIFY each original as exact duplicate or unique. Equal-looking prose, embedded plan hashes, or filenames cannot establish byte equality.
6. RECORD counterpart locator, byte/mode comparison, historical status, and hash mismatch in `implementation/revision15-provenance.md`.
7. CAPTURE only explicit owned regular files without following symlinks. COPY unique payloads into managed `legacy/scr-revision-15-planning/` with exact bytes/modes and original relative paths.
8. PUBLISH explicit INPUT manifest with stage `implementation` through `./bin/lets sdlc artifacts publish ITM-0003 --stage implementation --manifest /absolute/manifest.json --json`.
9. RECORD reusable managed bundle locators for duplicates and new bundle locators for unique bytes. Preserve every original-path mapping without re-importing ITM-0002 payloads. A duplicate without existing managed recovery proof needs its own preserved copy and publication. Artifact API accepts only allowed managed staging sources, never arbitrary `.codex` inputs. Do not broaden allowlist.
10. REQUEST independent restoration comparison in disposable source checkout through public artifacts commands. Keep all ten originals until comparison passes.
11. RECORD restoration evidence and bounded read-only historical ledger identities in managed reports. Coordinator retains final publication identities outside self-hashed reports.

**Done when**

1. Inventory maps all ten tracked files exactly once. Every duplicate has byte-equal counterpart evidence. every unique file has durable byte-preserving bundle.
2. Existing and new bundles recover all ten originals, with SHA-256, size, mode, and exact original paths. No unique information exists only locally.
3. Independent restore from ledger passes before any original is removed. Comparison covers restored managed copy and immutable snapshot, not copied source only.
4. Local draft hash `8a139fe5726d538c58b2fce1e38d95c46fc4c6f39bfaa1830c9bbafbcd871153` remains distinct from referenced `8801ca2266b6f90afd0e1a937926d3d3f88f4965a67c233be1e8ae5862533618`.
5. Historical auto-approval, contradictory draft state, event sequence/time, document/state blob IDs, commit, and content SHA-256 appear as facts with limits.
6. No historical payload, ledger state, original image, runtime evidence, or legacy workspace changed. Old ITM-0005 report bytes remain exact.
7. Manifest and proof state INPUT/stage explicitly. Independent validator can reproduce preservation using public artifact restore/verify commands.

### TSK-0002 — INDEX CURRENT SCOPE AND HISTORICAL EVIDENCE

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | high |

**To do**

1. ADD `docs/RESET-MODULE-INDEX.md` with current scope, historical chronology, exact evidence locations, acceptance limits, and pending work.
2. MAP root `RELEASE.md`, all managed former contracts, feasibility/revision collections, hidden retired snapshots, and ITM-0002 provenance bundles.
3. MAP retained REQ document/state/round artifacts using stable ledger identity and tested read-only retrieval after public sync. Keep old local ledger checkout labeled historical.
4. CAPTURE bounded source/docs evidence from exact legacy checkout into `implementation/history-audit.md`. Record dirty-state limits without archival or source import.
5. DISTINGUISH revision-6 diagnostic/no-DEB record from later production/package evidence, failures, rejected packages, and unresolved image/hardware acceptance.
6. ADD explicit supersession mapping for old SRC/reset-reason prescriptions, historical ABI/toolchain assumptions, and current observable-boot limits.
7. EXPLAIN revision-15 local-draft/ledger hash distinction and historical auto-approval claim. Preserve original reports through additive clarification only.
8. LINK ITM-0005 report bundle and unresolved recovery limits. State source/image identities and approved-plan byte gaps only as verified or unknown.
9. LINK current ITM-0001 status and ITM-0006 responsibility through resolving commands and stable ledger paths. Keep future canonical source/archive deliverables explicitly pending.
10. PROVIDE exact managed materialization/recovery instructions for every non-product target. Explain unchanged embedded historical links through original-path mappings.
11. AFTER independent TSK-0001 restoration PASS, REMOVE only ten inventoried active-looking revision-15 files from assigned product worktree.
12. UPDATE narrow live links in `docs/audits/SDLC-MIGRATION.md` to current index/recovery entries. Preserve dated historical claims and test results as historical.
13. RECORD link/reference coverage, deletion preconditions, recovery checks, and source hashes in managed `implementation/link-audit.md`.

**Done when**

1. Reader can identify current observable-boot scope, excluded reset reasons, actual acceptance limits, pending build plan, and authoritative evidence without stale assumptions.
2. Index covers every required collection and ten revision-15 mappings. Hidden historical snapshots have explicit coverage, not only visible files.
3. Root release remains byte-identical. Later package/source evidence is indexed without production-release, hardware-success, or clean-image claims.
4. Every new/current Markdown link resolves after stated materialization or has exact tested recovery instructions. No pending ITM-0006 path is a broken live link.
5. Retained REQ history remains recoverable by pinned identity. Historical `auto-approved` record never becomes current approval or permission to resume.
6. All ten retired files have independent pre-removal restore proof. Product diff removes only those assigned artifacts and changes assigned documentation.
7. ITM-0003 documentation acceptance stands alone. ITM-0006 final archive/source/readiness work remains pending and explicitly owned.
8. No historical contract or evidence bytes/hash changed. Current-source claims cite current evidence, never historical guide hashes.

### TSK-0003 — DOCUMENT SAFE IMAGE PROCEDURES AND VERIFY CONSUMERS

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | default |

**To do**

1. REWRITE `docs/DEVELOPER-GUIDE.md` around current Codex SDLC entry points, current index, image safety, actual image tools, and supported optional Claude tooling.
2. REMOVE instructions that imply original raw-image writes or routine privileged launch. Explain raw `--rw` behavior only with disposable-copy and authority constraints.
3. DOCUMENT full shared-lock window from copy through final cleanup/source proof. Prefer retained `test-package` orchestration for reversible package acceptance.
4. DOCUMENT read-only inspection boundaries, disposable-root `verify-package` limits, mount-state checks, source hashes, architecture, ownership, upgrades, and complete restoration.
5. DOCUMENT separate hardware procedure and explicit exact-package developer acceptance. Keep cleanup failures quarantined and recovery separately approved.
6. RETAIN accurate raw/gzip, partition, mount-state, cleanup, and namespace behavior. Verify flags against installed wrappers and source without executing image commands.
7. DESCRIBE `./bin/lets codex run` and supported `./bin/lets claude run` options from actual help/source. No container, privilege, device, or hardware launch occurs.
8. MATCH command examples to final ITM-0004 retained `SafetyCliHelper.main`, `SdlcPackageHelper`, wrappers, and current SDLC contract. Use item identifiers, not retired ceremonies.
9. VERIFY shell/help examples and links without image execution. Record usage exits accurately where leaf help returns `1` with valid usage text.
10. COMPLETE managed `implementation/documentation-acceptance.md` with requirement map, commands/exits, fresh guide hashes, rollback, and pending ITM-0006 obligations.
11. PUBLISH complete explicit INPUT selection through LETS. Include new reports and new archive evidence or exact prior-bundle references. Exclude QA RESULT and self-hashed final digest.
12. HAND OFF validator-ready source and complete durable INPUT selection. Coordinator records committed source after orchestrator commit. Final snapshot, QA, RESULT, and promotion remain pending.
13. ADD this sentence in `docs/SDLC-DEVELOPER-GUIDE.md` Plan section: “Task validation precedes final item QA/RESULT/SHOW/promotion, whose mandatory obligations belong in post-task item acceptance instead of task Done-when.” Link canonical contract from developer guide. Preserve all gates and ITM-0004 Migration boundary text. Do not change roles, skills, template, or engine.

**Done when**

1. Developer guide cannot reasonably direct mutation of original images or imply routine privileged container/hardware authority.
2. Guide specifies full lock-held disposable lifecycle, reversible Debian ownership/scripts/backups/upgrades/conflicts, functional checks, rollback, whole-image restoration, and quarantine.
3. Guide separates image/package acceptance from identified-device hardware procedure and explicit developer confirmation. This item claims neither occurred.
4. Current Codex entry points and supported Claude tooling match installed source/help. No retired REQ ceremony, absent flag, or automatic telemetry claim appears.
5. Revised live docs and index resolve every link/reference through existing files or tested recovery. Historical evidence retains its original bytes and internal references.
6. Requirement map and actual preservation/reference evidence let independent validator judge every task criterion. Producer does not claim future detached QA or RESULT.
7. Gate handoff names required unit/system commands, stack-lease rules, and style applicability. Post-task acceptance retains independent validation and detached QA obligations below.
8. Python style is inapplicable to docs-only diff. Any newly justified Python change requires renewed scope review and changed-existing/new-file style coverage, excluding deletions.
9. Whitespace, numbered-list/table structure, fresh command/source checks, bounded link checks, and durable restoration all pass. No implementation-mirroring test framework is added.
10. Producer handoff names exact checkout/base/diff, complete selected INPUT digest/ledger path, actual restore proof, doc hashes, rollback, and ITM-0006 obligations. Coordinator records committed source identity after commit.
11. Complete selected INPUT restores through LETS with bytes, modes, sizes, hashes, and original-path mappings intact. Final source/INPUT binding, RESULT, and promotion stay explicitly pending.
12. No item/chain-complete claim precedes corresponding gates. No ITM-0001 approval, image recovery, package acceptance, or hardware success is inferred.
13. Canonical Plan section states task/final-gate ordering through one added sentence. All existing gates and ITM-0004 Migration boundary changes remain intact. Developer guide links canonical contract without duplicating ceremony procedure.

## Item acceptance after task validation

1. Independent task/block validator judges every task criterion before integration assembly. TSK-0001 independent restoration PASS remains mandatory before TSK-0002 removes ten originals.
2. Coordinator records orchestrator-committed task source, assembles validated block, and captures final detached source snapshot plus complete selected INPUT.
3. Independent QA repeats every acceptance criterion against exact `(source_tree, input_digest)` pair. Source and artifact evidence remain immutable during verification.
4. Required unit and system gates pass once per independent role on final applicable source. System gate uses owned stack lease. No duplicate identical gate commands.
5. Python style is inapplicable to docs-only diff. Any approved Python change requires changed-existing/new-file style coverage, excluding deletions.
6. Independent detached QA verifies current guides/interfaces, all links/recovery instructions, ten-file preservation, and actual durable INPUT restoration.
7. Independent QA publishes separate RESULT bound to exact source/INPUT pair. RESULT never enters its own INPUT. Producer reports never contain future self-referential identities.
8. Coordinator final handoff names source tree, INPUT digest/ledger path, independent RESULT digest/ledger path, restore proof, doc hashes, rollback, and ITM-0006 obligations.
9. Artifact-bearing `verified`, `approve`, `settle`, `prepare-promotion`, and `promote` use explicit `--expected-artifacts DIGEST`. Missing index cannot downgrade existing bundles to source-only.
10. Exact-pair SHOW approval and promotion follow current contract and recorded authority. Coordinator verifies installed source before completion bookkeeping.
11. No task implementation criterion requires future QA RESULT, final detached binding, or installed promotion. These remain mandatory item acceptance gates.
12. ITM-0003 completion proves its documentation acceptance only. ITM-0006 readiness, ITM-0001 approval/build, image recovery, package acceptance, and hardware success remain separate.
