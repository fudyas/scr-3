# ITM-0005 — Plan

## Goal

Deliver bounded, read-only assessment of legacy REQ-0001 image residue. Record exact paths, evidence limits, retention decisions, and later recovery needs. Publish durable inventory/disposition evidence for ITM-0004 safety audit and ITM-0006 offline readiness. Completion proves assessment coverage, never image recovery, reclaimable bytes, or permission to delete.

## Context

1. Customer source, verbatim:

   > Issue tasks cleanup where needed suggest what leftovers of the previous SCR SDLC need to be removed

   > Create a new SDLC chain that transits from old to new SDLC. Add all items to it (except rebuilding the module). The state of the repo after the chain must be "ready for kernel module rebuild" according to the new ceremonies

   > All these folders belong to the planning, implementation and QA stage and should be managed under .codex/sdlc as in Specz (with claude)

   > Approve this and pre-approve all other items in this chain until the migration is complete

2. Current record: ITM-0005-SDLC-IMAGE-RESIDUE-ASSESSMENT. Chain CHN-0001 order: ITM-0002, ITM-0005, ITM-0004, ITM-0003, ITM-0006. Target: `feature/monit-stability`. ITM-0002 must reach DONE before execution. Standing authorization replaces repeated interactive plan/SHOW waits within recorded scope only. Coordinator records actual revision and exact source/INPUT/RESULT identities. Independent planning, validation, QA, exact guards, and safety remain required.
3. Candidate root A: `/home/fudya/devel/scr/.codex/sdlc/recovery/REQ-0001-GOAL-COUNT-SYSTEM-RESETS/`. Candidate root B: `/home/fudya/devel/scr/.codex/sdlc/req-0001-offset-test/`. Source record estimates about 7.3 GiB and 1.9 GiB allocated. Estimates are historical, not verified reclaimable space.
4. Planner metadata observation, 2026-11-12: four `baseline-clone.img` files and failed `image_8.26.0` each report logical size `3850371072`. Thirteen root-owned `journal.json` files have mode `0600` and fail current user's readability check. No journal contents or image bytes read. Existing `authentic-baseline.json`, `legacy-inspection.json`, mountpoint directories, `group.baseline`, and `statoverride.baseline` need individual coverage.
5. Exact markers: `/home/fudya/devel/scr/.codex/sdlc/quarantine/image-dirty.json` and `/home/fudya/devel/scr/.codex/sdlc/quarantine/image-2fb37ce67d396e77fa86.json`. Both metadata entries report root ownership, mode `0600`, and size `10958`. Contents remain UNKNOWN. Marker names alone do not prove image identity or recovery state.
6. `etc/sdlc.conf` selects `.codex/sdlc` for `SDLC_RUNTIME_ROOT` and `SDLC_SHARED_LOCK_ROOT`. Active locks, quarantine, recovery evidence, and new `artifacts/` sibling remain protected. Entire `.codex/sdlc` never becomes cleanup scope.
7. Historical source: `/home/fudya/devel/scr/.codex/REQ-0001-revision-15-solution-plan.tmp.md`. It is explicitly unapproved revision 15. Its approved-revision-14 reference is SHA-256 `70415f436cfc2bbe4b4df38af2e02e6a56fd69950c718021143ea66662a74a58`. Approved plan bytes and hash match remain unverified. Missing historical plan locator becomes explicit missing evidence, never inherited authority.
8. Historical draft records source SHA-256 `cce7577ce20aa4263a08dab9891bbf17e8471a385fbc4d0d050605b5a6de56f6`, failed-copy SHA-256 `27ceb7e1b57c9f46e15c9cb1fe976ab5fef318339a419fdca9614e68417909b2`, and marker-pair SHA-256 `3f76d69432243decfda0e57eaad03c93886bfa9572954839113c00c9338915ae`. These are historical claims, not fresh byte verification. Draft also records replay/baseline identities and failed sequencing history. Preserve those references without executing old procedures.
9. Closest safety code: `tools/sdlc/src/sdlc.py`, symbols `Context.assert_image_available` and `Context.lock`. Global quarantine blocks image operations before lock acquisition. Metadata assessment requires neither lock bypass nor recovery mode. No current image-analysis contents exist within authorized scope.
10. ITM-0002 supplies `ArtifactManifest`, `ArtifactBinding`, `ArtifactUsecases.publish`, `capture_review`, `verify_review`, and `result_for`. `ArtifactSource` confines explicit regular files to managed paths. Durable bundle: `artifacts/bundles/DIGEST.json` on `sdlc` branch. Item index: `artifacts/items/ITM-0005/index.json`.
11. Facts derive from current item/history, standing chain description, guide, code, bounded host metadata, and labeled historical draft. Assumption: protected paths can change externally. Assessment records capture times and drift limits. Unknown facts remain unknown. No load-bearing question blocks honest inventory.

## Design

1. **Fit:** Evidence-only item, one block, three tasks. No product source, architecture, safety implementation, or package changes. Managed reports supply exact consumer contract for ITM-0004 and ITM-0006.
2. **Patterns:** Reuse ITM-0002 explicit manifests, immutable ledger bundles, restoration comparison, and source/INPUT/RESULT review binding. Reuse existing safety rules as constraints. Do not add inventory framework or resurrect legacy commands.
3. **Context:** Assigned checkout `/home/fudya/devel/scr`. Future block/integration paths come from coordinator. Host inventory always names absolute candidate roots. Worker checkout must not link or copy images. Existing `docs/SDLC-DEVELOPER-GUIDE.md` owns architecture contract. Reports reference this contract and explain capture limits. No architecture/documentation consumer change outside managed assessment is needed.
4. **Evidence shape:** `inventory.json` records `schema_version`, `captured_at`, `host`, `uid`, `roots`, `entries`, `commands`, and `coverage`. Each entry records exact path, type, owner/group, mode, logical/allocated bytes, timestamps, device/inode, links, evidence source, and confidence. Unavailable fields include reason, never guessed values.
5. **Disposition shape:** Each path gets exactly one of KEEP, ARCHIVE, SAFE-CANDIDATE, or RECOVERY-REQUIRED. Separate evidence status uses OBSERVED, HISTORICAL, or UNKNOWN. ARCHIVE and SAFE-CANDIDATE are proposals only. Unknown identity, unreadable protected evidence, or unresolved reference requires RECOVERY-REQUIRED. Active runtime/source paths remain KEEP.
6. **Capture boundary:** Metadata traversal never follows symlinks or enters mounted image roots. Mountpoint directories receive metadata and explicit coverage exclusions. Accessible regular journals/baselines can supply references without touching their image targets. Quarantined image content and fresh image hashes remain excluded even when Unix permissions allow access.
7. **Delivery boundary:** New reports live under `/home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0005/implementation/`. Independent reports live under sibling `qa/`. Publication selects explicit report files only. Protected originals never become artifact-manifest sources.

## Out of scope

1. Deletion, moves, archival of protected originals, cleanup, chmod/chown, marker modification, image hashing/content inspection, image copy, mount, loop setup, restoration, quarantine release, or process termination.
2. Privilege escalation, `SDLC_RECOVERY` bypass, legacy-workflow resumption, package build/install/remove, kernel rebuild/load, hardware access, flashing, reboot, or physical output.
3. General scan of `.codex/sdlc`, other recovery roots, credentials, unrelated worktrees, or main-checkout edits.
4. ITM-0004 safety-code removal, ITM-0003 historical index, ITM-0006 archive/readiness execution, and ITM-0001 replacement implementation plan.
5. Fresh complete image-hash inventory, proven image preservation by byte comparison, successful hardware result, or proven reclaimed-space claim.

## Safety

1. This is host metadata/evidence assessment, not image-change item. Debian package ownership, maintainer scripts, backups, upgrades, architecture/conflict checks, package functional tests, and uninstall restoration tests are inapplicable because no package/image change occurs. Do not mark hardware-required for this item.
2. Preserve `var/` images, kernel archive, README, failed copy, all clones, journals, baselines, markers, and active locks. Never open image bytes to improve confidence. Readable historical hashes remain historical.
3. Metadata capture permits bounded directory listing, no-follow file metadata, mount/loop/process metadata, and accessible textual evidence. Record denied access and visibility limits. Never escalate permissions or interpret inaccessible process/mount evidence as absence.
4. Before traversal, record visible mount table. Do not descend into known or suspected image mountpoints, cross filesystem boundaries, or follow links. Record changes between pre/post metadata captures as drift. Drift blocks unsupported conclusions, not honest UNKNOWN coverage.
5. Later recovery proposal remains non-executable scope. It must identify exact paths, authority/access needs, trusted baseline, backup, verification, rollback, and acceptance evidence. It must require continuous shared image lock through copy/mount/install/test/uninstall/restoration/unmount/cleanup. Ordinary leases cannot replace image lock. Any cleanup/restoration failure retains quarantine and blocks reuse until separately approved recovery succeeds.
6. Any later image modification requires reversible Debian delivery. Uninstall all delivered packages must restore bytes, types, ownership, permissions, symlinks, hardlinks, timestamps, xattrs, and added/moved/deleted paths. Proposal must retain upgrades, architecture, ownership-overlap, conflicts, source hashes, and whole-image restoration evidence. This item executes none of those actions.
7. Hardware procedure and acceptance are separately inapplicable. Later device work requires explicit developer authority and identified device/image/package, logs, expected/observed behavior, rollback, exact package version/hash, and developer confirmation. Historical draft hardware language grants no current authority.
8. Report rollback preserves immutable prior bundles and restores report bytes/modes through artifact tooling to conflict-free managed destinations. No image rollback occurs because no image action occurs. Publication never removes originals or rewrites historical hashes.
9. QA uses detached source snapshot plus immutable INPUT. QA publishes separate RESULT for exact pair. `verified`, `approve`, `settle`, `prepare-promotion`, and `promote` require `--expected-artifacts DIGEST`. Missing index cannot downgrade artifact-bearing review to source-only. RESULT never appears inside its own INPUT.

## Item acceptance

1. Independent block validation covers implementation criteria before assembly. Later detached QA owns final source/INPUT binding checks and RESULT publication.
2. Independent QA restores final bound INPUT in disposable checkout and compares every report's bytes, SHA-256, mode, size, and path provenance.
3. Independent QA records all task criteria, safe capture review, final restoration evidence, and applicable gate results in `qa/assessment-result.md`.
4. QA publishes this report as RESULT, stage `qa`, bound to exact `source_tree` and `input_digest`. QA never changes implementation INPUT.
5. Applicable workflow checks use LETS. No new implementation tests needed for report-only change. Required unit/system gates use disposable fixtures without actual image operations.
6. Coordinator records exact final INPUT digest, ledger locator, entry paths, source tree, and separate RESULT locator for ITM-0004 and ITM-0006.
7. Exact source/INPUT/RESULT identities survive SHOW and promotion with artifact guards. Unknown protected evidence remains visible in final handoff.

## BLK-0001 — Assess residue and publish durable disposition

Block owns ITM-0005 managed implementation reports only. No cross-block dependencies. Validator and QA retain independent ownership of their reports.

### TSK-0001 — CAPTURE BOUNDED RESIDUE INVENTORY

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | — |
| 2 | model | high |

**To do**

1. READ promoted ITM-0002 guide and actual artifact CLI help after dependency reaches DONE.
2. RECORD allowed roots, explicit marker paths, source-document locators, current user, capture time, and command boundaries in `implementation/capture-log.md`.
3. CAPTURE visible mount, loop backing-file, relevant process, and lock metadata before directory traversal. Record exact scope and permission limits.
4. INVENTORY candidate roots without following links, opening image bytes, or entering image mountpoints. Write `implementation/inventory.json` using Design fields.
5. RECORD exact path/type/uid/gid/mode/logical size/allocated size/device/inode/link/timestamp metadata where available. Separate allocated totals from logical totals and historical estimates.
6. READ only accessible regular textual journals/baselines and named historical source. Preserve exact reference/hash/error text with source locator.
7. ***if*** evidence is inaccessible, image content, mounted content, missing, or ambiguous ***then***
   7.1. RECORD UNKNOWN, exclusion reason, required evidence, and access needs.
   7.2. PRESERVE affected original path without retries that broaden authority.
8. RECORD source/copy/replay/marker/baseline reference edges without asserting unverified identity matches.
9. CAPTURE same bounded post-inventory metadata. Record drift and visibility limitations in `implementation/capture-log.md`.

**Done when**

1. `inventory.json` covers both candidate roots, every safely discoverable entry, and explicit exclusions for inaccessible or mounted subtrees.
2. Four baseline clones, failed image, all discovered journals/baselines/mountpoint directories, and both markers have exact-path records.
3. Every hash states source, capture context, and HISTORICAL or fresh textual-report provenance. No fresh image/content hash exists.
4. Metadata includes owners, logical/allocated sizes, references, visible mount/loop/process findings, and actual errors or access limitations.
5. Pre/post evidence records preservation limits honestly. No zero-mount/process claim exceeds current namespace and user visibility.
6. Capture log contains exact commands, exit codes, timestamps, source locators, and no image/mutation/escalation command.

### TSK-0002 — RECORD DISPOSITION AND RECOVERY BOUNDARIES

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0001 |
| 2 | model | high |

**To do**

1. WRITE `implementation/disposition.md` with explicit numbered per-path rows linked to `inventory.json` entries.
2. ASSIGN KEEP, ARCHIVE, SAFE-CANDIDATE, or RECOVERY-REQUIRED with evidence status, retention reason, reference dependencies, and missing evidence.
3. RECORD existing archive locator only when observed. Label proposed archive destination as proposed. Preserve referenced clones, journals, baselines, failed copy, and markers.
4. WRITE `implementation/recovery-proposal.md` with exact path groups, required authority/access, verification, rollback, acceptance evidence, and stop conditions.
5. SEPARATE later privileged evidence access from later image recovery and reclamation. State concrete prerequisite evidence before any disposition can change.
6. RECORD approved-revision-14 locator/hash-match gap and unapproved revision-15 status. Preserve source/copy/replay/marker historical identities verbatim.
7. WRITE `implementation/consumer-contract.md` naming ITM-0004 safety dependencies and ITM-0006 retention/offline-build exclusions.
8. STATE that failed image and protected clones cannot supply final offline build. Treat managed artifacts, active locks, and quarantine as protected siblings.

**Done when**

1. Every inventory entry maps to exactly one disposition or explicit excluded-subtree record. Rows have `#` first column and exact paths.
2. UNKNOWN protected entries are RECOVERY-REQUIRED. No unreadable journal, unverified clone, or active path becomes SAFE-CANDIDATE by assumption.
3. Report distinguishes observed facts, historical claims, unknowns, and later proposals. Actual reclaimable bytes remain unproven.
4. Proposal states verification and rollback for each proposed action. Protected recovery requires separate approval and full Safety section invariants.
5. ITM-0004 receives exact retained safety/runtime dependency boundaries. ITM-0006 receives path retention and forbidden offline-input boundaries.
6. No deletion, migration, package, device, lock bypass, or recovery step was executed. Historical approval never becomes current authority.

### TSK-0003 — PUBLISH AND VERIFY ASSESSMENT INPUT

| # | Field | Value |
| --- | --- | --- |
| 1 | depends_on | TSK-0002 |
| 2 | model | default |

**To do**

1. WRITE `implementation/input-manifest.json` with explicit `purpose: INPUT`, `stage: implementation`, and selected report entries only.
2. USE absolute `source_path`, exact `original_path`, and `items/ITM-0005/implementation/...` `managed_path` per entry. Exclude manifest self-reference and protected originals.
3. PUBLISH selected reports through `./bin/lets sdlc artifacts publish ITM-0005 --stage implementation --manifest /home/fudya/devel/scr/.codex/sdlc/artifacts/items/ITM-0005/implementation/input-manifest.json --json`.
4. VERIFY bundle through `artifacts verify --bundle DIGEST --json`. Retain digest and ledger locator in planner/implementation logs.
5. RESTORE bundle through `artifacts restore --bundle DIGEST --json` in coordinator-assigned disposable checkout with no image links.
6. COMPARE every restored report's bytes, SHA-256, mode, size, original path, and managed path against selected originals.
7. RECORD restoration commands, exits, comparisons, consumer locators, and rollback in `implementation/publication-proof.md`.
8. PUBLISH complete final INPUT including publication proof. Keep proof's earlier bundle reference explicitly labeled as restoration evidence.
9. HAND OFF final artifact index, bundle locator, entry paths, coverage map, and known gaps to independent validator and QA.

**Done when**

1. Durable `artifacts/items/ITM-0005/index.json` selects complete INPUT. `artifacts/bundles/DIGEST.json` contains exact bytes/modes/path provenance.
2. Final INPUT includes inventory, capture log, disposition, recovery proposal, consumer contract, and publication proof. No source report is force-added to Git.
3. Every final INPUT entry passes `artifacts verify`. Publication proof records successful disposable restoration of selected reports before final source binding.
4. Consumer locator is exact final INPUT digest plus ledger path and managed entry path. Coordinator records final binding after source snapshot recapture.
5. Independent validator receives complete immutable evidence and criterion map. Later QA and promotion obligations remain explicit under Item acceptance.
