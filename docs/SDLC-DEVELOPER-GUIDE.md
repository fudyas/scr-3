# SCR SDLC

Codex owns one item workflow. Skills, roles, and LETS share this contract. All commands start with `./bin/lets sdlc`.

## Ceremonies

| # | Ceremony | Skill | Result and gate |
| --- | --- | --- | --- |
| 1 | Intake | `$sdlc-new` | Normalize request, retain source wording, mint authorized BACKLOG item. |
| 2 | Plan | `$sdlc-plan` | Independent planner audits intent/code and drafts plan. Developer approves current revision. |
| 3 | Run | `$sdlc-run` | Schedule approved item, claim host, build independent blocks, validate tasks, assemble, verify snapshot. |
| 4 | SHOW | `$sdlc-review` | Retain editable integration workspace. Developer approves exact verified tree before promotion. |
| 5 | Hardware | `$sdlc-follow-up` | Developer reports exact package on identified hardware/image. Required image items remain REVIEW until success. |
| 6 | Chain planning | `$sdlc-chain-plan` | Define complete outcomes, reconcile existing scope, and write authorized membership. No implementation approval. |
| 7 | Chain run | `$sdlc-chain-run` | Run members in ledger order. Retain every plan, SHOW, and hardware gate. |

Textual `/sdlc-*` aliases select matching Codex skills. Canonical skills live in `.agents/skills/`. Roles live in `.codex/agents/`.
Old round commands and Claude SDLC prompts no longer define active workflow. Managed artifact manifests preserve their original paths and bytes.

## Ledger and identity

1. Item identity: `ITM-NNNN-DESC`. Stable key: `ITM-NNNN`. DESC uses 2–8 uppercase hyphenated words, at most 64 characters.
2. Kinds: task, improve, refactor, fix. Records retain raw idea, normalized description, tags, dependencies, host, plan revision/approval, tasks, hardware evidence, and history.
3. Statuses: BACKLOG, PLANNED, SCHEDULED, IN PROGRESS, TESTING, REVIEW, DONE, OBSOLETE.
4. Only approved current plan reaches PLANNED. Scheduling does not approve plans. Run request authorizes scheduling and execution.
5. Dependencies must be DONE before claim. Cycles fail. Another host's claim blocks work. Never use force to bypass ownership.
6. All records live on `sdlc` branch: `items/ITM-NNNN/item.json`, PLAN.md, REVIEW.md, `chains/CHN-NNNN/chain.json`, and `ids.json`.
7. LETS uses local mirror and compare-and-swap remote writes with bounded retries. Sync before decisions and inspect state after uncertain writes.
8. Existing `docs/requirements/REQ-*` ledger history remains intact. Item paths do not replace it. No automatic ID conversion or old-requirement resumption.
9. `SDLC_LEDGER_REMOTE` overrides default remote. Existing image configuration remains in `etc/sdlc.conf`. Item configuration lives in `tools/sdlc/src/item_engine/etc/sdlc.json`.
10. Ledger commands can commit and push their bookkeeping as part of requested workflow. Implementation promotion stays local. User pushes implementation separately.

## Architecture context

1. READ project instructions, relevant developer guide, design records, customer source, prior requirement/package history, and relevant code.
2. FIND closest existing module and reusable helpers. Record constraints, ownership, interfaces, and evidence before design.
3. ***if*** topic has an architecture map ***then*** USE map to select exact records and dependencies.
4. ***else*** SEARCH relevant project files directly. No absent architecture tree is required.
5. PRESERVE stable IDs and canonical links. Update affected design references and consumers with implementation.
6. DISTINGUISH implementation evidence from intended design. Missing product or hardware policy remains explicit question.

## Scope and verification

These rules govern new plans and explicit plan revisions. Existing approved plans keep their criteria and effective review decisions.
Skill updates alone never add or remove obligations, trigger replanning, or reopen completed work.

1. DEFINE deliverables before tasks or tests. Each names source requirement, observable result, owned changes, and supported conditions.
2. DISTINGUISH owned changes from existing dependencies. Record each consumed interface, required assumption, and evidence needed to use it.
3. LIMIT each item to a bounded outcome that can be reviewed and accepted independently after prerequisites complete.
4. SELECT simplest design that satisfies declared behavior. Justify added mechanisms through concrete failures of a deliverable.
5. KEEP dependency internals outside scope unless changed or explicitly requested. Using a dependency does not assign ownership of its correctness.
6. MAP each item-specific test to a deliverable criterion, expected result, defect detected, and acceptance stage.
7. COVER relevant failure behavior and regressions. Name changed code and affected behavior for each regression beyond direct deliverables.
8. VERIFY consumed interfaces through delivered behavior. Broader dependency qualification requires explicit scope. Missing prerequisite evidence blocks affected acceptance without expanding ownership.
9. LIST mandatory repository gates and applicable safety checks separately, with their source and stage. Scope limits never waive them.
10. USE focused fixtures or interface tests that prove required behavior. Require actual dependency execution for integration claims that fixtures cannot establish.
11. KEEP task criteria achievable at task validation. Place assembled-item QA, RESULT, SHOW, promotion, and hardware confirmation in later acceptance stages.
12. AUDIT both missing coverage and unnecessary work before approval. Every task and proposed test needs a stated delivery or mandatory-gate purpose.
13. SHOW deliverables, dependency boundaries, test mapping, mandatory gates, and pending acceptance stages during existing plan approval.
14. REUSE this mapping in implementation and review. Additional focused diagnostics for the same criteria need no new approval.
15. CLASSIFY findings as deliverable defects, concrete regressions, unmet prerequisites, mandatory-gate failures, or unrelated observations.
16. CITE criterion, affected behavior, or mandatory rule for blocking findings. Unrelated improvements remain observations, not automatic rework.
17. REPORT dependency failures that prevent promised behavior or safe delivery. Such failures do not authorize dependency repair or broader qualification.
18. ROUTE material changes through existing scope-decision process. Never disguise new product behavior, compatibility changes, or dependency ownership as test hardening.

Test mapping describes acceptance, not a fixed command list. Engineers retain bounded diagnostic freedom within approved behavior and authority.
Task validation uses relevant unit/style checks. Final QA retains required repository gates and applicable package/image checks.
An unrun required check stays pending or failed at its assigned stage. Earlier stages cannot claim its success or require later-stage completion.

| # | Requested change | Relevant evidence | Outside scope without additional requirement |
| --- | --- | --- | --- |
| 1 | Utility integrates its logs with existing rotation | Shipped configuration, post-rotation writes, retained-history decisions, and required integration behavior | General scheduler, compression engine, or unrelated-log qualification |
| 2 | Item changes rotation policy | Changed policy and affected logs, including scheduling or retention behavior that item changes | Unaffected platform behavior |
| 3 | CLI adds one output field | Field value/schema and affected output compatibility | Requalification of unchanged network, database, or logging implementations |
| 4 | Reversible image package | Owned payload plus all required source-preservation, ownership, restoration, cleanup, and hardware evidence | Unrequested platform features |

## Plan

Template: `tools/sdlc/src/item_engine/etc/PLAN.template.md`. `items plan check ID` validates structure and task dependencies.

Task validation precedes final item QA/RESULT/SHOW/promotion, whose mandatory obligations belong in post-task item acceptance instead of task Done-when.

1. Header contains Goal, Context, Deliverables, Dependencies, Design with Fit/Patterns/Context, Out of scope, Safety, and Verification.
2. BLK-NNNN blocks own disjoint work. Blocks have no cross-block dependencies.
3. TSK-NNNN tasks carry depends_on, model hint, To do, and verifiable Done when. Dependencies reference earlier tasks within same block.
4. Model hints are low, default, high. They select available Codex effort through coordinator. They are not foreign model identifiers.
5. Each handoff contains full header and one task. Effective review decisions travel with every later handoff.
6. Image plans include package ownership, backups, scripts, upgrades, conflicts, whole-tree restoration, rollback, locked tests, and hardware procedure.
7. Planner asks load-bearing questions before drafting and audits scope under [Scope and verification](#scope-and-verification). Developer approves concrete checked draft. Approved PLAN.md stays immutable.
8. REVIEW.md holds actual later developer decisions. Each decision names Overrides and Decision. Autonomous findings belong in reworks and logs.
9. Bounded engineering fixes within approved invariants continue. Changed customer behavior, scope, risk, safety, or hardware authority requires renewed developer decision.
10. Replanning requires unscheduling unstarted work. Active review changes retain integration ownership. Preserve prior plans and evidence through ledger history.

## Run and independent roles

| # | Role | Responsibility |
| --- | --- | --- |
| 1 | sdlc_requirements | Normalize intent, source constraints, and failed hardware evidence. |
| 2 | sdlc_image_analysis | Read-only image facts, file ownership, and prior package conflicts. |
| 3 | sdlc_planner | Audit relevance, requirements, existing code, and draft only. |
| 4 | sdlc_implementation | One task in assigned worktree. No commit, push, or hardware authority. |
| 5 | sdlc_validation | Read-only independent criteria, code, style, package, and restoration audit. |
| 6 | sdlc_integration | Assemble validated blocks; prepare and install exact tested promotion. |
| 7 | sdlc_qa | Detached-snapshot gates and every acceptance criterion. |
| 8 | sdlc_follow_up | Verbatim developer hardware evidence, success/failure, and next action. |
| 9 | sdlc_coordinator | Durable stage progression, independent handoffs, human gates, and safety. |

1. SYNC and select explicit item, next ready queued item, or sole PLANNED item. Ask for ambiguous selection only.
2. ***if*** persisted review context exists ***then*** RESUME integration before status dispatch.
3. SCHEDULE approved item and claim IN_PROGRESS. Failed dependency/host checks stop before worktree creation.
4. CREATE block worktrees. Build tasks in dependency order, within available concurrency. Orchestrator commits authorized block work only.
5. VALIDATE each block independently. Record failures with `items task rework ID TSK --stage STAGE --reason TEXT`.
6. ASSEMBLE validated blocks sequentially into integration.
7. PRESENT integration and create detached snapshot. QA judges every criterion against that snapshot.
8. ***if*** gates pass ***then*** RECORD verified tree and enter REVIEW/SHOW.
9. ***if*** gates fail ***then*** RECORD findings and continue bounded fixes. After presentation, fixes stay in integration.
10. HALT on three failures at same stage, unresolved design decision, material authority change, tooling blocker, or safety failure.

Unchecked criteria cannot pass. Ordinary halt releases owned worktree leases and records reason/resume command. Image quarantine stays logically locked.

## Codex role dispatch

Main-checkout `etc/sdlc.conf` owns live role models and efforts. `./bin/lets sdlc models` prints nine tab-separated role, model, and effort rows.
The safety CLI resolves main checkout even from a linked worktree. Candidate configuration needs isolated regression evidence before promotion.
Installed main-checkout output needs a fresh check after promotion. Unpromoted worktree configuration does not change live dispatch configuration.
Configuration changes affect future dispatches. They do not switch an already-running coordinator or worker.
These identifiers require fresh support checks against the current collaboration tool declaration before each dispatch.

| # | Role | Model | Role effort |
| --- | --- | --- | --- |
| 1 | `sdlc_coordinator` | `gpt-6.1-sol` | `high` |
| 2 | `sdlc_requirements` | `gpt-6-astra` | `xhigh` |
| 3 | `sdlc_image_analysis` | `gpt-6.1-terra` | `high` |
| 4 | `sdlc_planner` | `gpt-6-astra` | `high` |
| 5 | `sdlc_implementation` | `gpt-6.1-sol` | `high` |
| 6 | `sdlc_validation` | `gpt-6-astra` | `high` |
| 7 | `sdlc_integration` | `gpt-6-astra` | `high` |
| 8 | `sdlc_qa` | `gpt-6-astra` | `high` |
| 9 | `sdlc_follow_up` | `gpt-6.1-sol` | `high` |

Task `model` values are effort hints, never model identifiers. Roles without a task hint use `default`.
Effort order is `low`, `medium`, `high`, `xhigh`, `max`, `ultra`, subject to current model support.

| # | Task hint | Selected effort |
| --- | --- | --- |
| 1 | `default` | Configured role effort. |
| 2 | `low` | `low`. |
| 3 | `high` | At least `high`. Preserve configured `xhigh`, `max`, or `ultra`. |

Canonical `.agents/skills/sdlc-*` instructions authorize configured model and mapped effort overrides for fresh independent workers.
Overrides require `fork_turns="none"` and a complete reconstructed handoff in `message`.
Full-history inheritance uses `fork_turns="all"` with both `model` and `reasoning_effort` omitted.
Inheritance cannot prove explicit configured routing. Configuration-specific launch evidence requires explicit overrides.
Fixed `swe` and `Verifier` role model contracts remain unchanged. They do not replace the custom SDLC roles.

Dispatch procedure:

1. READ current `./bin/lets sdlc models` output into `roleMapping`.
2. READ current collaboration tool declaration into `toolSupport`.
3. SELECT required SDLC role and task hint into `selectedRole` and `taskHint`.
4. CALCULATE `selectedModel` and `selectedEffort` from `roleMapping` and hint table.
5. ***if*** configuration is missing, hint is invalid, ***or*** selected model/effort is unsupported ***then***
   5.1. STOP before dispatch.
   5.2. RECORD exact missing values, tool declaration, and any tool error.
   5.3. REPORT routing blocker without silently substituting another model or effort.
6. READ complete matching `.codex/agents/sdlc-*.toml` role instructions into `roleBody`.
7. ***if*** custom role is available ***then***
   7.1. SET `agent_type` to `selectedRole`.
8. ***else***
   8.1. SET `agent_type` to `default`.
   8.2. INCLUDE complete `roleBody` in reconstructed handoff.
9. COUNT coordinator and all existing workers against current live concurrency limit.
10. ***if*** no worker slot is available ***then***
    10.1. WAIT for a slot before dispatch.
11. RECONSTRUCT complete handoff with fields listed below.
12. ***if*** configured routing is selected ***then***
    12.1. LAUNCH `collaboration.spawn_agent` with selected `agent_type`, `model`, `reasoning_effort`, `fork_turns="none"`, and handoff in `message`.
13. ***else if*** full-history inheritance is deliberately selected ***then***
    13.1. LAUNCH `collaboration.spawn_agent` with selected `agent_type`, `fork_turns="all"`, and neither `model` nor `reasoning_effort`.
14. RECORD requested role/model/effort, returned worker identity, exact errors, and worker acknowledgement.
15. ***if*** launch fails ***then***
    15.1. STOP dependent work with exact failure evidence.

Required handoff fields:

1. Complete role instructions, including safety rules and role-specific duties.
2. Item ID, chain/order when active, target branch, plan revision and explicit approval evidence.
3. Complete approved header and assigned task with every Done-when criterion. Include available deliverable/test mapping, dependency boundaries, and acceptance stages.
4. Effective `REVIEW.md` decisions with Overrides and Decision, or explicit statement that none exist.
5. Absolute assigned worktree path, branch, base revision, file ownership, and allowed edits.
6. Shared-worker warning, preservation of others' edits, current stage, and main-checkout bookkeeping path.
7. Relevant findings, dependencies, prior evidence, gate commands, artifacts/hashes, rollback, and pending obligations.
8. Selected role/model/effort, task hint, current tool support source/date, fallback choice, and concurrency limit.
9. Explicit image/hardware authority or prohibition, required log role/task, and expected return evidence.

Role selection, configuration inspection, and worker acknowledgements establish separate facts.
Successful launch needs returned worker identity and acknowledgement. Work acceptance still needs independent validation, QA, SHOW approval, and required hardware evidence.
Missing or failed launch evidence blocks routing acceptance. Simulated dispatch and planned results never count as live launch proof.

## Managed stage artifacts

1. Planning, implementation, and QA deliverables belong under main checkout `.codex/sdlc/artifacts/`. Product documentation and source code remain on working branch.
2. Managed item paths start with `items/ID/`. Historical collection paths start with `legacy/COLLECTION/`. Manifests retain each original path.
3. Immutable ledger bundles contain exact file bytes, SHA-256, size, and permission mode. Durable locator: `artifacts/bundles/DIGEST.json` on `sdlc` branch.
4. Item index `artifacts/items/ID/index.json` retains selected INPUT digest, RESULT digests, and prior bundle history. Local storage alone is not durable acceptance evidence.
5. Local immutable copies live under `.codex/sdlc/artifacts/snapshots/DIGEST/`. Another host restores them through ledger. Conflicting destination files block restoration.
6. `purpose` is explicit `INPUT` or `RESULT`. Stage is independently `planning`, `implementation`, or `qa`. Historical QA evidence can be INPUT.
7. INPUT captures selected evidence for review. RESULT records independent QA against exact `(source_tree, input_digest)` pair. RESULT never includes itself as INPUT.
8. Manifests select explicit regular files. Binary and hidden files retain bytes. Traversal, symlink ancestors, duplicate paths, and protected paths fail closed.
9. Import sources belong beneath integration `contracts/` or `evidence/`, managed `items/ID/`, or managed `legacy/`. New deliverables use managed paths.
10. `.lets` control state, drafts, leases, telemetry, and logs retain current locations. `.codex/sdlc` image runtime paths remain protected siblings of `artifacts/`.
11. Artifact commands never enumerate, clean, or migrate protected image runtime siblings. Image locks, quarantine, and recovery policy remain unchanged.
12. Never force-add ignored artifacts into product tree. Publish explicit manifest through LETS. Preserve originals until durable restoration and byte/mode comparison pass.
13. Historical hashes prove original capture context. Preserve hashed payloads unchanged. An older guide hash does not identify current guide after contract changes.
14. Provenance index retains original path, hash, bundle locator, and capture limits. Fresh QA verifies current contract independently.
15. ITM-0002 migrates all 87 historical and nine current root artifacts. ITM-0003 consumes locators for indexing. ITM-0006 verifies final preservation and readiness.

Public commands:

```bash
./bin/lets sdlc artifacts publish ID --stage planning --manifest /absolute/manifest.json --json
./bin/lets sdlc artifacts list ID --json
./bin/lets sdlc artifacts restore --bundle DIGEST --json
./bin/lets sdlc artifacts verify --bundle DIGEST --json
```

Manifest fields are `schema_version`, `purpose`, optional `stage`, optional `source_tree`, optional `source_commit`, optional `input_digest`, and `entries`.
Each entry has absolute local `source_path`, historical `original_path`, and relative `managed_path`. Durable bundle excludes local source path.
RESULT requires `source_tree` and same-item `input_digest`. Stage argument must match manifest stage when present.

Artifact procedure:

1. WRITE explicit manifest for selected files and purpose.
2. PUBLISH manifest with stage through `artifacts publish`.
3. RESTORE bundle in fresh disposable checkout through `artifacts restore`.
4. COMPARE restored bytes and modes against originals.
5. ***if*** publication, restoration, ***or*** comparison fails ***then***
   5.1. KEEP originals.
   5.2. STOP source removal.
6. ***if*** comparison passes ***then*** REMOVE only preserved root artifacts and update live consumers to bundle locators.
7. SNAPSHOT source and INPUT together through `worktree snapshot ID --json`.
8. VERIFY detached source snapshot and immutable INPUT copy through independent validator and QA.
9. PUBLISH independent QA report as RESULT bound to exact source tree and INPUT digest.
10. RECORD verification and approval with exact source tree and INPUT digest.

Publication and restore retain prior bundles. Rollback selects retained prior bundle, without overwriting conflicts or rewriting ledger history.

## Exact-revision SHOW and promotion

Context: `worktree context ID --json`. Durable file: `.lets/sdlc/logs/ID/review-context.json`.
Integration: `.codex/worktrees/ID/integration`, branch `work/ID/integration`. Main-checkout edits belong to user.

1. PRESENT complete staged item diff. Retain built task commits. Show integration path, branch, diff, and `ide ID` command.
2. RECORD user decisions in REVIEW.md. Send fixes to same integration path. Preserve manual edits and staging groups.
3. SNAPSHOT every tracked edit, deletion, staged edit, and new unignored file with `worktree snapshot ID --json`. Capture selected INPUT separately.
4. VERIFY detached snapshot through independent validator and QA. Changed/new files count. Deleted files do not enter style gate.
5. RECORD `worktree verified ID --expected-tree TREE --expected-artifacts DIGEST` after successful independent QA and matching RESULT publication.
6. SHOW source tree, INPUT digest/path, RESULT digest/path, target, full diff, tests, rollback, and pending hardware obligations separately.
7. WAIT for explicit approval of exact source/INPUT pair and pinned RESULT. Silence, earlier plan approval, and chain invocation are not approval.
8. RECORD `worktree approve ID --expected-tree TREE --expected-artifacts DIGEST`, then `worktree settle ID --expected-tree TREE --expected-artifacts DIGEST --message TEXT`.
9. ACQUIRE maintree. Prepare isolated promotion merge with `worktree prepare-promotion ID --expected-artifacts DIGEST --json`.
10. VERIFY prepared commit. Changed merge tree requires system verification. Changed package requires fresh restoration evidence and SHOW approval.
11. INSTALL `worktree promote ID --expected-commit COMMIT --expected-artifacts DIGEST`. Target movement, overlaps, changed reviewed files, or active merge blocks installation.
12. RELEASE ordinary leases on every exit. Preserve unrelated main edits. Never force, stash, reset hard, or silently choose semantic precedence.
13. VERIFY installed commit before completion bookkeeping. Interrupted bookkeeping resumes installed promotion without merging again.
14. ***if*** hardware required ***then*** WAIT in REVIEW for developer result. Do not deploy automatically.
15. ***if*** all required evidence passes ***then*** MARK tasks/item DONE. Remove clean worktrees only. Retain pending IDE edits.

Optional `--codex-session URL` adds session attribution to promotion. No Claude hooks or platform adapters are required.
Artifact-bearing contexts require explicit `--expected-artifacts` on verified, approve, settle, prepare-promotion, and promote.
Source-only legacy contexts remain compatible only when no artifact selection exists. Missing index with durable bundles fails closed.
Changed live INPUT bytes, immutable snapshot, selected digest, or pinned RESULT invalidates acceptance even when Git source tree stays unchanged.

## Image and hardware safety

1. PRESERVE `var/image_8.26.0`, kernel archive, kernel README, and all original image/kernel data. Never remove or rewrite them for testing.
2. USE reversible Debian packages for every image change. Retain backups for replaced, patched, moved, added, and deleted files.
3. RESTORE payload, file type, owner/group, permissions, symlink targets, hardlinks, timestamps, and xattrs within existing fingerprint contract.
4. RETAIN package ownership overlap checks, architecture matching, upgrade checks, rollback, and proof that uninstalling all delivered packages restores original image.
5. TEST disposable image copies only. `test-package` hashes source before/after, copies, mounts, installs, tests, removes, verifies restoration, unmounts, and cleans scratch.
6. HOLD shared image lock across entire operation. `stack` and `maintree` leases do not replace image lock.
7. RETAIN source hash, active-mount, partition, root-scoped dpkg, package architecture, cross-architecture intent, fingerprint, xattr, unmount, and cleanup checks.
8. QUARANTINE on cleanup or restoration failure. Shared quarantine blocks image reuse even after process exits. Never manually erase markers to pass gates.
9. USE shared filesystem lock root across hosts that share images. Advisory flock semantics must work there. Preserve existing `SDLC_SHARED_LOCK_ROOT` setting.
10. MARK image item with `hardware require ID` before approval. Image package scaffold requires approved running item and this marker.
11. IDENTIFY hardware/image, exact package version/hash, installation procedure, expected behavior, logs, and rollback before any hardware test.
12. REQUIRE explicit authority before flashing, reboot, physical outputs, or broader real-device access. Missing policy is a blocker.
13. RECORD developer report verbatim through `hardware pass|fail`. Automated tests, plan approval, SHOW approval, and agent reports never establish hardware success.
14. KEEP image item out of DONE until developer confirms success. Failure preserves report and package identity, then returns to bounded rework or separately approved follow-on item.
15. REVERIFY and obtain new SHOW/hardware approval after artifact changes. A successful earlier package does not approve later bytes.

Retained commands:

```bash
./bin/lets sdlc package-init ID --operation replace:/absolute/path
./bin/lets sdlc test-package ID --image /absolute/source/image --deb /absolute/package.deb
./bin/lets sdlc verify-package ID --root /disposable/mounted/root --deb /absolute/package.deb
./bin/lets sdlc lock-run --image /absolute/image -- COMMAND...
./bin/lets sdlc hardware require ID
./bin/lets sdlc hardware pass ID --deb /retained/integration/package.deb --image-identity TEXT --notes-file FILE --confirmed-by-developer
./bin/lets sdlc hardware fail ID --deb /retained/integration/package.deb --image-identity TEXT --notes-file FILE
```

`verify-package` is internal to locked disposable testing or an explicitly approved controlled disposable root. Never target original mounted image.
Recovery requires separately approved procedure and successful restoration proof. Routine continuation cannot waive quarantine.

## Leases, gates, and logs

1. Item worktrees share `.lets` for managed tools and host state. They do not link `var/` or `image/` into workers.
2. Host-local `stack` lease serializes system QA. `maintree` serializes promotion. When both needed, acquire maintree before stack.
3. Never steal or force another holder's lease. Check ownership before shared operations. Release ordinary leases on every exit.
4. `gate unit` runs project automated unit tests. `gate style PATH...` checks changed Python paths. `gate system --holder ID` runs disposable automated system tests.
   4.1. `gate unit` always includes `tests/sdlc` and `tests/toolchain`. Additional path arguments extend collection, not narrow it.
   4.2. USE a pytest `-k` or marker selector for scoped task checks. Verify selected tests cover task criteria and relevant regressions.
   4.3. RETAIN full required gates at final QA. A scoped task pass cannot substitute for their results.
5. `gate all --holder ID` runs unit then system. Failed unit prevents system. Missing/failed system coverage cannot become a green result.
6. Automated CLI system tests prove tooling behavior. Image acceptance additionally requires locked package restoration evidence and developer hardware result.
7. `sdlc test` runs item-engine and retained SCR safety regressions. Tests use temporary repositories and simulated image operations.
8. Every stage and role writes `log write ID --role ROLE [--task TSK] [--block BLK] [--level LEVEL] TEXT`.
9. Logs live in `.lets/sdlc/logs/ID/`. Use `log tail ID --follow` for live evidence.
10. `mark ID STAGE` attributes CLI events. `stats ID`, aggregated reports, and read-only SQL remain available.
11. Automatic transcript usage capture is not claimed for Codex. Historical transcript parser supports explicit local imports only. Missing usage is not zero-cost evidence.

## Chain execution

1. Chain identity is CHN-NNNN-DESC. Ledger member list supplies order. Each item belongs to at most one chain.
2. Derived status ignores OBSOLETE members: all remaining DONE means DONE, all unstarted means BACKLOG, otherwise IN PROGRESS.
3. VERIFY complete remaining chain before execution. External prerequisites must be DONE. Internal prerequisites precede dependents.
4. SELECT first unfinished non-obsolete member. Existing review context takes precedence over item status.
5. APPLY plan, run, review, or pending hardware follow-up. Plan approval immediately starts execution within requested chain.
6. KEEP exact-revision SHOW and hardware approvals per item. Chain agreement never approves either.
7. ***if*** member completes ***then*** SYNC, verify unchanged membership/order, recheck prerequisites, and continue automatically.
8. ***if*** halt, safety failure, ownership conflict, failed command, or changed order ***then*** STOP chain and report current member/resume command.
9. ***if*** chain completes ***then*** REPORT ready unfinished chains. Start no unrelated chain.
10. Chain planning defines bounded complete outcomes, assigns unique artifact ownership, reconciles existing records, and preserves every acceptance obligation.
11. Authorized membership changes use LETS only. A partially applied batch requires fresh reads before dependent writes.

## Migration boundary

1. Existing REQ ledgers, package artifacts, kernel files, image files, image-tool implementations, and real-hardware evidence remain preserved.
2. Source ceremony engine supplies items, plans, chains, leases, exact-tree review, promotion, listings, logs, and telemetry reports.
3. SCR retains private image/package safety engine in `tools/sdlc/src/sdlc.py`. Adapter `tools/sdlc/src/item_engine/sdlc/controllers/safety_cli.py` exposes `package-init`, `test-package`, `verify-package`, `lock-run`, and `models`.
4. Retired workflow snapshots preserve prior local edits. They are inert historical evidence, never active skills or executable instructions.
5. Historical adoption/import grants no hardware, image-mount, implementation-promotion, staging, or commit authority.
6. Tested, authorized artifact publication writes bundles and indexes through LETS ledger transactions. It grants no implementation promotion or hardware authority.
7. Private safety entry points refuse retired REQ ceremony names before repository access. Active item/chain commands and explicit historical transcript imports remain supported.
8. Public `package-init` requires an approved item in IN PROGRESS or TESTING, hardware-required status, and output within its assigned block or integration worktree.
9. Private scaffold helper refuses absent approved item state before ledger reads or output writes. No REQ ledger fallback remains.
10. `lock-run --image IMAGE -- COMMAND...` consumes one separator before `COMMAND`. Remaining child arguments, spaces, flags, and literal separators stay unchanged.
