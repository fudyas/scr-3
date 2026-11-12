# ITM-0004-SDLC-RETIRED-CEREMONY-CODE-CLEANUP — Plan

## Goal

Remove retired REQ ceremony implementation and obsolete-only tests after caller proof. Preserve active item/chain commands, historical evidence, transcript import, and package/image safety. Deliver tested retained interfaces and immutable audit evidence for ITM-0003 and ITM-0006.

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

1. Chain CHN-0001: ITM-0002 → ITM-0005 → ITM-0004 → ITM-0003 → ITM-0006. Execution requires ITM-0005 DONE.
2. Planning checkout: `/home/fudya/devel/scr`, branch `feature/monit-stability`, supplied base `62b3a9e4bf3d50ad09ea71c17164adcbcf65fe2e`.
3. Draft stays unapproved until coordinator checks actual revision and records standing authority. Independent validation, QA, and exact artifact guards remain required.
4. Effective REVIEW decisions: none. Current intake and amendment history: `.lets/sdlc/logs/ITM-0004/intake-current.json` and `./bin/lets sdlc items show ITM-0004`.
5. Product contract: `docs/SDLC-DEVELOPER-GUIDE.md`, especially Migration boundary, Managed stage artifacts, Image and hardware safety, and Exact-revision SHOW and promotion.
6. Planner relevance verdict: RELEVANT. Retired workflow remains in `tools/sdlc/src/sdlc.py`; active safety adapter imports same module.

### Evidence and limits

1. ITM-0005 detached snapshot: commit `783b84dc867d52f9bea5cdf1c0956d620e53ad65`, source tree `9f6d26bcab95a09ac643eefa96c7817cac9d4aba`. Bound INPUT: `0dafde9ce21b89d7e82ef07378bed48a35016380eff27240fcadb786660002c5`. Ledger locator: `artifacts/bundles/0dafde9ce21b89d7e82ef07378bed48a35016380eff27240fcadb786660002c5.json`. Independent exact-pair validator reports PASS for all eleven unchanged payloads and provenance. Independent QA RESULT: `407902732e2dd731785e465a0d9094aba1c395256fb1a29de733c4db0f35977d`. RESULT locator: `artifacts/bundles/407902732e2dd731785e465a0d9094aba1c395256fb1a29de733c4db0f35977d.json`.
2. Stable restoration-reference INPUT: `db0b46a6789d3907caa459770ac01a1e2e735d4ade22c9469623b9c3fced50c5`. Ledger locator: `artifacts/bundles/db0b46a6789d3907caa459770ac01a1e2e735d4ade22c9469623b9c3fced50c5.json`.
3. Complete unbound INPUT: `c4ab990bfbf0d5296e54c8b7b57879afad5ef54758944a422068ebac3893503c`. Ledger locator: `artifacts/bundles/c4ab990bfbf0d5296e54c8b7b57879afad5ef54758944a422068ebac3893503c.json`.
4. Reports live under `.codex/sdlc/artifacts/items/ITM-0005/implementation/`; immutable copies live under `.codex/sdlc/artifacts/snapshots/DIGEST/`.
5. Required reports: `inventory.json`, `capture-log.md`, `disposition.md`, `recovery-proposal.md`, `consumer-contract.md`, and `publication-proof.md`. Retain accompanying raw capture entries.
6. Observed report hashes: `disposition.md` = `0dd8edb296ec9a2e82670ed4bb7520413a0593673a87b5afdc67752defa8363a`; `recovery-proposal.md` = `bc1488fbca945086adf64ae7881ae6de077733b8bec5046b2de233f098f2e917`; `consumer-contract.md` = `0f8938721bd0d7e9b0db59a25aa2cc10b8c8773f8841b6f96658ccd50f21fb45`.
7. All 54 residue entries remain RECOVERY-REQUIRED. Active source/runtime boundaries remain KEEP. No removal, archive, recovery, or offline image-input candidate exists.
8. Twenty-one texts remain unreadable; eleven suspected mount subtrees remain excluded. Two quarantine markers remain held. Metadata observations cannot establish image identity or restoration.
9. Historical revision 14 hash lacks verified approved-plan bytes/locator. Revision 15 remains unapproved. Baseline reads caused recorded atime-only drift; no timestamp restoration occurred.
10. Image bytes and current image hashes remain unverified. Failed image and four clones cannot supply final offline build. Historical guide hashes never prove current contract.
11. Planner source hashes: `sdlc.py` = `d5fe60ef8c60ac6a545fe207322ec97a1d5ba250a63f4fb8850cef5147db1f1d`; safety adapter = `96b35f556429a2378d6d6f50881aca67f1ea7f0bab0fe1c41347d8c60bb02099`.
12. Planner test/contract hashes: `tests/sdlc/test_sdlc.py` = `2e39948195d9aad72e1ce2804e86b1e9fed3ea50930bcdf23dcd23fdaf78ee23`; guide = `7669ec50ca62f878df77d10d394af0ed7481a4abbe9446ffbae5485251a471a4`.
13. ITM-0005 QA report: `.codex/sdlc/artifacts/items/ITM-0005/qa/assessment-result.md`, SHA-256 `9c1cb7aadb0031ea966a8cba22946cbbf4bc63a0414ab2f13219766e19543a7e`. All 17 criteria PASS. Unit 496 and system 6 pass, exits 0. Eleven entries restore exactly across 44 copy comparisons. RESULT publication/verification ACK PASS supplied by coordinator.
14. Fresh prerequisite status at final planning check: REVIEW. Standing exact-pair approval recorded by coordinator; promotion/bookkeeping remains its responsibility. Execution still requires ITM-0005 DONE.

### Source audit findings

1. Active path: LETS safety wrappers → `sdlc.controllers.safety_cli:SafetyCliHelper.main` → file-loaded `sdlc.py` parser, `Context`, runtime helpers, package helpers, and model output.
2. Retired candidates: `SdlcWorkflowHelper`, `ContinuationPolicyHelper`, `STATES`, `ALLOWED_TRANSITIONS`, `SECTION_HEADINGS`, REQ-only ledger helpers and parser callbacks.
3. `SdlcLedgerHelper` is not wholly unreachable yet. `SdlcPackageHelper.cmd_package_init` loads REQ state when `approved_state` is absent.
4. Active adapter supplies approved item state after plan/status, hardware-required, and assigned-output checks. Removing legacy fallback must retain these checks and generated payload bytes.
5. `tests/sdlc/test_sdlc.py` mixes obsolete ceremony tests with active model routing, package scaffold, fingerprints, architecture, quarantine, and locked lifecycle tests.
6. `test_models_and_resume_dispatch_validated_work_to_integration` contains live model assertions and retired resume assertions. Keep live assertions when removing retired portion.
7. `test_package_scaffold_contains_reversible_maintainer_scripts` currently uses REQ creation. Adapt fixture to approved item state; retain script syntax and safety assertions.
8. Existing deterministic scaffold test pins bytes and modes. Existing full-window test uses real temporary fingerprints with simulated image/process effects. Preserve both oracles.
9. Historical transcript parsing and explicit import live in item engine. `tests/sdlc/items/test_transcript_usage.py` and `test_telemetry.py` remain retained coverage.
10. `SDLC_RECOVERY` and `SDLC_IMAGE_LOCK_HELD` are existing trust boundaries. Environment values alone prove neither recovery authority nor actual lock ownership.
11. No source change or passing test can resolve ITM-0005 unreadable evidence. Unknown recovery dependencies stay retained unless independent source/reference proof permits removal.

## Design

1. **Fit:** Keep private safety module at current path. Remove proven retired ceremony implementation in place. No safety-engine extraction or framework rewrite.
2. **Patterns:** Reuse `SafetyCliHelper.main`, existing parser/helper classes, active item approval checks, temporary repositories, deterministic scaffold hashes, and actual fingerprint comparisons.
3. **Context:** Current guide and ITM-0005 consumer contract govern retention. Source audit maps every removed symbol and mixed test before removal.
4. Active commands remain `package-init`, `test-package`, `verify-package`, `lock-run`, and `models`. Preserve options, callbacks, repeated operations, remainder arguments, and model row semantics.
5. Remove retired parser callbacks. Preserve explicit retired-command refusal before repository access, using inert command-name recognition where needed for existing diagnostics.
6. `cmd_package_init` must refuse absent approved item state before legacy lookup or output creation. Public adapter remains only supported scaffold entry.
7. Preserve generated package paths and historical `round` labels where they form package compatibility. Removing ceremony orchestration does not rename package artifacts.
8. One block owns coupled module, adapter, tests, and immediate documentation. Tasks run sequentially. No cross-block dependency exists.
9. Product source/docs stay versioned. Stage audit reports use explicit managed INPUT manifests. Independent QA publishes separate RESULT for exact source/INPUT pair.

## Out of scope

1. Image content reads, hashes, copy, mount, mutation, package installation, recovery, quarantine release, or metadata repair.
2. Hardware access, flash, reboot, physical outputs, module compile/load, module source import, compiler prerequisite repair, global dependency installation, or actual reset-module rebuild.
3. Removal or relocation of REQ ledger/history, retired snapshots, package artifacts, hardware evidence, protected runtime, immutable bundle payloads, or `.lets` control state.
4. ITM-0002 historical contracts/evidence relocation and path mapping. ITM-0003 historical/current index. ITM-0006 final offline-build readiness.
5. Broader safety redesign, recovery protocol changes, model configuration changes, new automatic transcript capture, or unrelated style churn.

## Safety

1. This item changes repository tooling only. No image change, delivered Debian package, package install, or hardware test occurs. Package/hardware acceptance is inapplicable for this item.
2. Retained scaffold must preserve private Debian payload ownership, `preinst` overlap claims, original backup retention, `postinst` operations, and `postrm` restoration.
3. Preserve upgrade behavior: original backup survives repeated installation, ownership by another package refuses, and remove/purge restores baseline. Deterministic payload hashes cannot be silently replaced.
4. Preserve source-hash checks, target architecture proof, explicit cross-architecture intent, root-scoped dpkg, existing exclusions, and ownership/conflict checks.
5. Preserve whole-tree bytes, file types, owner/group, modes, symlinks, hardlinks, timestamps, root/parent metadata, xattrs, and added/moved/deleted paths.
6. Retain full shared image-lock window: copy, mount, install, functional test, uninstall, restoration proof, unmount, source verification, scratch cleanup, unlock.
7. Preserve global/image quarantine, pre-acquisition and in-lock checks, journals, failure propagation, and blocked reuse. Ordinary leases cannot replace image lock.
8. Tests use synthetic temporary files and simulated external effects only. No test can reference shared images, actual mount state, protected runtime siblings, or real devices.
9. Preserve all original `var/` image/kernel/README bytes and metadata. No runtime-wide scans, lock acquisition against real images, marker removal, privilege escalation, or safety waiver.
10. Source rollback uses retained pre-change revision through normal review. Artifact rollback restores prior immutable bundles to conflict-free destinations through artifact commands.
11. Any later actual image change needs separately approved reversible Debian package and hardware-required marker before plan approval. All delivered packages must uninstall to original image state.
12. Later image procedure requires exact image/package identity, maintainer scripts, backups, upgrade/conflict tests, full locked lifecycle, and independent whole-image restoration evidence.
13. Later hardware procedure requires explicit developer/device/image/package authority, exact version/hash, expected/observed behavior, logs, source hashes, and rollback path.
14. Hardware acceptance separately requires verbatim developer confirmation for exact delivered package. Plan/SHOW authority and automated tests cannot establish hardware success.
15. Cleanup/restoration failure keeps quarantine until separately approved recovery proves restoration. Missing hardware policy blocks device work.

## Item acceptance after task validation

1. Coordinator captures integration source and selected INPUT through `./bin/lets sdlc worktree snapshot ITM-0004 --json`.
2. Independent QA verifies detached source and immutable INPUT. Required unit/system/style/safety gates and every plan criterion must pass.
3. QA publishes separate managed RESULT for exact `(source_tree, input_digest)`. RESULT never enters its own INPUT.
4. Coordinator records exact source/INPUT/RESULT under standing authority. Use explicit `--expected-artifacts DIGEST` for verified, approve, settle, prepare-promotion, and promote.
5. Changed source or INPUT requires fresh exact-pair verification. Missing index cannot downgrade existing durable bundles to source-only.
6. Final handoff records installed source, INPUT/RESULT locators, rollback, and remaining ITM-0005 limits. No image or hardware success claim exists.

## BLK-0001 — Remove retired ceremony code and retain verified safety interfaces

Ownership: `tools/sdlc/src/sdlc.py`, `tools/sdlc/src/item_engine/sdlc/controllers/safety_cli.py`, `tests/sdlc/test_sdlc.py`, `tests/system/test_sdlc_cli.py`, `tools/sdlc/package-init.sh`, `tools/sdlc/test-package.sh`, `tools/sdlc/verify-package.sh`, and narrow guide updates. Managed reports belong under `/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0004/implementation/`. No other worker edits these files for this item.

### TSK-0001 — REMOVE PROVEN RETIRED CEREMONY IMPLEMENTATION

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. READ final ITM-0005 bound reports and verify ITM-0005 DONE before implementation. Recheck source assumptions against assigned worktree.
2. RECORD `retirement-audit.md` with source hashes, exact search scope, imports, wrappers, callbacks, shared helpers, and removed/retained symbol decisions.
3. MAP every removal to actual caller proof. Include `SdlcLedgerHelper`, `SdlcWorkflowHelper`, `ContinuationPolicyHelper`, workflow constants, runtime helpers, and `Context` fields.
4. KEEP uncertain recovery dependencies. Record uncertainty explicitly. Stop material scope changes before edits.
5. REMOVE REQ fallback from `SdlcPackageHelper.cmd_package_init`. Refuse absent approved state before ledger access or scaffold writes.
6. REMOVE retired ceremony classes/constants/helpers only after caller closure. Preserve safety functions in current module and retained CLI interfaces.
7. REMOVE retired parser callbacks in `SdlcCliHelper.parser`. Preserve existing retired refusal diagnostics in both entry points before repository access.
8. ADAPT `SafetyCliHelper.main` only where parser/refusal compatibility requires. Preserve item approval/status, hardware-required, output-boundary, and loaded-error identity checks.
9. REMOVE obsolete-only tests/helpers from `tests/sdlc/test_sdlc.py`. Adapt mixed model/scaffold tests without dropping live assertions.
10. ADD regression cases for all retired command names, absent approved state, and no legacy ledger/output effects. Exercise actual retained entry points.
11. RETAIN deterministic scaffold bytes/modes, metadata fingerprints, architecture failures, quarantine races, cleanup failures, and full locked-window success/failure tests.
12. EXTEND `tests/system/test_sdlc_cli.py` only where public retired-command refusal or retained safety help/model dispatch lacks coverage.
13. RECORD test-to-behavior matrix in `retirement-audit.md`. Distinguish actual temporary-file checks, simulated external effects, and untested image/hardware behavior.

**Done when**

1. Audit lists every deleted symbol/test/helper, caller evidence, reason, and retained replacement where needed. No live consumer imports deleted symbols.
2. Retired workflow states, orchestration, ledger mutation, and callbacks are absent. Retired commands cannot create repository context, write ledger, or emit scaffold files.
3. Absent approved state fails closed. Active adapter still accepts approved running hardware-required items only within assigned output boundary.
4. Retained command arguments and diagnostics stay compatible. `models` preserves nine configured role rows, main-checkout resolution, and visible missing values.
5. Deterministic scaffold golden hashes and modes pass unchanged. Shell syntax, original backup/upgrade guards, ownership overlap, and uninstall operations retain meaningful assertions.
6. Fingerprint tests detect bytes, mode, timestamps, hardlinks, symlinks, root metadata, and xattr changes. Architecture mismatch still refuses before install.
7. Actual temporary-tree lifecycle test proves lock through source hashes, simulated copy/mount/install/test/remove, restoration, unmount, and cleanup. Mismatch retains quarantine.
8. Quarantine race, fingerprint failure, mount/unmount cleanup failure, and scratch cleanup failure tests retain real error assertions. No weaker replacement oracle or broadened exclusion exists.
9. `./bin/lets sdlc gate unit` passes with full item, safety, and toolchain collection evidence. Historical transcript/telemetry tests remain collected and pass. No duplicate `sdlc test` run required without new changes, failures, or unresolved concerns. Independent QA still runs its own required gates.
10. `./bin/lets sdlc gate style PATH...` passes for every changed/new existing Python path. Deleted files are excluded from style arguments.
11. `./bin/lets sdlc gate system --holder ITM-0004` passes under owned stack lease. Public item/chain behavior and synthetic historical REQ preservation remain verified.
12. Independent validator confirms every criterion, safety code retention, obsolete-only deletions, unchanged scaffold hashes, and absence of protected filesystem effects.

### TSK-0002 — DOCUMENT AND BIND RETAINED INTERFACES

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | default |

**To do**

1. UPDATE `docs/SDLC-DEVELOPER-GUIDE.md` Migration boundary narrowly for final private safety ownership, retired refusal, and item-only scaffold authority.
2. UPDATE usage text in `package-init.sh`, `test-package.sh`, and `verify-package.sh` from retired `REQ-ID` to active item identifier where appropriate.
3. RECORD `consumer-contract.md` with final symbols/wrappers, retained recovery constraints, ITM-0005 locator, audit/test evidence, source hashes, and ITM-0003/ITM-0006 obligations.
4. RECORD exact commands, exits, test counts, known limits, removal list, and rollback in managed implementation evidence. Keep reports outside product source.
5. PUBLISH explicit implementation INPUT manifest through `./bin/lets sdlc artifacts publish ITM-0004 --stage implementation --manifest /absolute/manifest.json --json`.
6. RESTORE published bundle through artifact commands in disposable checkout. Compare bytes, SHA-256, size, mode, and original paths against originals.
7. HAND OFF selected INPUT and source revision to coordinator for detached capture and independent QA after task validation.
8. IDENTIFY required exact-pair gates and final source/INPUT/RESULT locator fields. Coordinator records final identities after QA without rewriting published payloads.

**Done when**

1. Product documentation and wrapper usage match tested implementation. No active instruction invokes retired REQ ceremonies or claims automatic transcript capture.
2. Consumer report names exact retained safety interfaces and final ITM-0005 evidence. Every UNKNOWN/RECOVERY-REQUIRED boundary remains explicit.
3. Managed INPUT bundle restores byte-for-byte with original paths, hashes, sizes, and modes. Failed restore/comparison blocks acceptance and preserves originals.
4. Task handoff includes exact INPUT locator, restore proof, source revision, test matrix, and every acceptance obligation for independent QA.
5. Independent validator confirms narrow documentation changes, tested interface mapping, preserved historical import support, and unchanged ITM-0003 index ownership.
6. Current guide/code prove current contract. Historical hashes remain immutable capture claims. Missing artifact index cannot downgrade durable bundles to source-only.
7. Item acceptance remains pending coordinator source capture, QA RESULT, exact-pair approval, and promotion. No worker fabricates approval or commits source independently.
8. Consumer handoff supplies ITM-0003 interface/audit inputs and ITM-0006 cleanup inputs, protected-input exclusions, and pending recovery/hardware limits.
