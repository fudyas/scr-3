---
name: sdlc-chain-run
description: Run or resume an SCR SDLC chain in ledger order while retaining per-item plan, SHOW, and hardware approvals.
---

# SDLC chain-run

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

1. READ requested chain with `./bin/lets sdlc chains show CHN --json`, fresh item records, and dependencies after sync.
2. VERIFY complete remaining chain before starting. External prerequisites must be DONE. Internal prerequisites must be DONE or earlier members. OBSOLETE never satisfies DONE dependency.
3. RETAIN chain ID, ordered members, current item, and target branch through questions and compaction.
4. SELECT first member neither DONE nor OBSOLETE. Empty chain reports no work.
5. ***if*** active review context ***then*** APPLY `$sdlc-review ID` before other dispatch rules.
6. ***else if*** BACKLOG ***then*** APPLY `$sdlc-plan ID`. Explicit plan approval immediately starts `$sdlc-run ID`.
7. ***else if*** PLANNED ***then*** VERIFY current plan approval and APPLY `$sdlc-run ID`.
8. ***else if*** SCHEDULED, IN_PROGRESS, or TESTING ***then*** APPLY `$sdlc-run ID` with same ownership.
9. ***else if*** REVIEW ***then*** APPLY `$sdlc-review ID` or pending hardware follow-up.
10. WAIT at each plan, exact-revision SHOW, or hardware gate. Never approve on user's behalf.
11. ***if*** member completes ***then*** SYNC, verify unchanged membership/order, recheck prerequisites, and continue automatically.
12. ***if*** stop, failed command, ownership conflict, safety failure, or changed order ***then*** REPORT `STAGE CHAIN HALT`, current member, reason, and `$sdlc-chain-run CHN`.
13. ***if*** all members complete/obsolete ***then*** REPORT `STAGE CHAIN DONE` and ready unfinished chains. Start no unrelated chain.
