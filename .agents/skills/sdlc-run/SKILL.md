---
name: sdlc-run
description: Schedule, implement, or resume an approved SCR SDLC item through independent validation and exact-revision SHOW.
---

# SDLC run

READ [SDLC contract](../../../docs/SDLC-DEVELOPER-GUIDE.md) and [image and hardware safety](../../../docs/SDLC-DEVELOPER-GUIDE.md#image-and-hardware-safety).
Use only `./bin/lets sdlc ...` for ledger operations. Preserve exact user wording, IDs, evidence, commands, paths, hashes, and errors.
Use `$caveman full` for every handoff and authored SDLC section. Apply `simple-english` where compatible.
SDLC roles require independent workers. READ matching `.codex/agents/sdlc-*.toml`. Role `sdlc_planner` uses `sdlc-planner.toml`. PASS complete instructions, full handoff, explicit ownership, and absolute worktree path.
When custom role is unavailable, use default worker with complete role body. Workers share repo. Preserve other workers' edits. Follow available concurrency limits. Use configured Codex models, with no Claude runtime dependency.

READ [Codex role dispatch](../../../docs/SDLC-DEVELOPER-GUIDE.md#codex-role-dispatch) before each worker launch.
This skill explicitly authorizes configured model and mapped effort overrides for fresh independent SDLC workers.
Use `fork_turns="none"` with overrides and a complete reconstructed handoff containing every contract field.
Full-history inheritance uses `fork_turns="all"` with neither `model` nor `reasoning_effort`.
Check current tool-supported models, efforts, custom roles, and concurrency before dispatch. Missing or unsupported mapping blocks dispatch with exact evidence.
Use available custom SDLC role, or `default` worker with complete role body. Count coordinator and all existing workers.
Configuration changes affect future launches. They do not switch an already-running coordinator.

READ [Managed stage artifacts](../../../docs/SDLC-DEVELOPER-GUIDE.md#managed-stage-artifacts).
Store planning, implementation, and QA deliverables under `.codex/sdlc/artifacts/`; keep product source and documentation on working branch.
Publish explicit INPUT or RESULT manifests through `./bin/lets sdlc artifacts publish`; retain immutable ledger bundles and original path/hash provenance.
Do not force-add ignored artifacts. Preserve original bytes until independent durable restore comparison passes.
Image runtime siblings remain protected. Never enumerate or clean them through artifact tooling. `.lets` state, drafts, leases, and telemetry retain current locations.
Review binds source tree and immutable INPUT digest. QA publishes separate RESULT for exact pair, without self-reference. Historical QA evidence can be INPUT.
Artifact-bearing review requires `--expected-artifacts DIGEST` on verified, approve, settle, prepare-promotion, and promote. Never downgrade missing artifact index to source-only.

1. RUN `./bin/lets sdlc sync`. Select explicit ID, next ready scheduled item, or sole PLANNED item. Ask only for ambiguous selection.
2. READ item and available `worktree context ID --json`.
3. ***if*** active review context exists ***then*** APPLY `$sdlc-review ID`, regardless of item status.
4. ***if*** PLANNED ***then*** RUN `items schedule ID`. Run request authorizes scheduling.
5. ***if*** SCHEDULED ***then*** RUN `items status set ID IN_PROGRESS`. Never force another host's claim or bypass dependencies.
6. ***for each*** independent block, within available worker slots:
   6.1. RUN `worktree add ID BLK`.
   6.2. ***for each*** unfinished task in dependency order:
      6.2.1. MARK task IN_PROGRESS.
      6.2.2. LAUNCH `sdlc_implementation` with complete `items task show ID TSK` handoff, block path, ownership, and findings.
      6.2.3. COMMIT only assigned block changes under authorized SDLC execution. Preserve unrelated main edits.
   6.3. LAUNCH `sdlc_validation` against block and diff base. PASS marks tasks VALIDATED. FAIL records `items task rework ID TSK --stage validate --reason TEXT` and returns findings to engineer.
7. CREATE integration with `worktree add ID integration`. LAUNCH `sdlc_integration` in assemble mode for validated blocks, sequentially.
8. RUN `worktree present ID`, then `worktree snapshot ID --json`.
9. SET TESTING. LAUNCH `sdlc_qa` against detached snapshot, all criteria, package hashes, and restoration evidence.
10. ***if*** QA passes and matching RESULT is published ***then*** RECORD `worktree verified ID --expected-tree TREE --expected-artifacts DIGEST`, set REVIEW, and SHOW tree, full diff, integration path, branch, and `./bin/lets sdlc ide ID`.
11. RETAIN same-session review context. WAIT for fixes or explicit approval through `$sdlc-review ID`. Never auto-promote.
12. ***if*** QA fails ***then*** RECORD rework and continue fixes in integration. Preserve IDE edits. Never return to block worktrees after presentation.

Short commands above carry prefix `./bin/lets sdlc`. Log every stage with `log write ID --role run`.
Bounded engineering fixes within approved scope continue automatically. Halt on three failures at one stage, unresolved design choices, changed scope/risk/hardware authority, or safety failure.
Never release an image from quarantine as routine halt cleanup. Ordinary worktree leases release on exit.
