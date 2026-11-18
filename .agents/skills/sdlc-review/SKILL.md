---
name: sdlc-review
description: Own interactive SCR SHOW, apply fixes in integration, verify immutable snapshots, and promote only approved exact revision.
---

# SDLC review

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

1. RUN `sync`, read item, verify host ownership, and read `worktree context ID --json`.
2. ***if*** context absent for REVIEW ***then*** RUN `worktree present ID`. For another status, route to `$sdlc-run ID`.
3. RETAIN integration path, branch, target, diff base, snapshot, verified tree, approval, and promotion commit. Interrupted promotion resumes from persisted context.
4. SHOW `STAGE SHOW`, integration path, `status --short`, and full diff against recorded base. Offer `./bin/lets sdlc ide ID`.
5. ***for each*** user fix or manual IDE edit:
   5.1. RECORD actual user decisions through `items review edit|check|commit ID`. Each decision names Overrides and Decision. REVIEW.md outranks immutable approved PLAN.md.
   5.2. RECORD affected task reworks and set IN_PROGRESS. Autonomous QA findings belong in reworks and logs, never invented user decisions.
   5.3. LAUNCH `sdlc_implementation` for requested fixes in integration only. Preserve existing edits. Leave review fixes unstaged and uncommitted.
6. RUN `worktree snapshot ID --json`. Pass detached source path, source tree, INPUT digest, and immutable artifact path to validator and QA.
   6.1. APPLY [Scope and verification](../../../docs/SDLC-DEVELOPER-GUIDE.md#scope-and-verification) to effective approved scope and current acceptance stage.
   6.2. CLASSIFY findings before rework. Dependency failures do not authorize dependency repairs. Unrelated improvements do not become acceptance criteria.
7. ***if*** any gate or criterion fails ***then*** RECORD evidence and continue authorized fixes in integration. Never record verification for failed or unchecked criteria.
8. RECORD `worktree verified ID --expected-tree TREE --expected-artifacts DIGEST`, then set REVIEW. Concurrent edits require fresh snapshot and verification.
9. SHOW source tree, INPUT digest/path, RESULT digest/path, target, full diff, package hashes, tests, rollback, and hardware obligations. WAIT for explicit approval of that exact tree.
10. ***if*** approved ***then*** RUN `worktree approve ID --expected-tree TREE --expected-artifacts DIGEST` and `worktree settle ID --expected-tree TREE --expected-artifacts DIGEST --message TEXT`.
11. ACQUIRE maintree lease. LAUNCH `sdlc_integration` in promote mode. Prepare clean promotion merge, run required gates, and install only tested expected commit.
12. RELEASE ordinary leases on every exit. Conflicts, target movement, overlapping user edits, or changed artifacts return to review. Never force promotion.
13. VERIFY persisted promotion commit exists in target before completion bookkeeping. Interrupted bookkeeping never repeats installed merge.
14. ***if*** hardware required ***then*** KEEP item REVIEW and worktrees until developer reports hardware result through `$sdlc-follow-up ID`. No automatic deployment, reboot, flashing, or physical I/O.
15. ***if*** hardware not required ***or*** confirmed successful for exact delivered package ***then*** SET tasks DONE and item DONE.
16. REMOVE only clean worktrees. Retain pending IDE edits and report paths. Report promotion commit, decisions, tests, package identity, hardware result, and resume command.
17. ***if*** active chain ***then*** RETURN completed member to chain runner. Continue only after required hardware confirmation.

Short commands carry prefix `./bin/lets sdlc`. User pushes code separately. Do not request scheduling approval again.
Merging moved target into review requires explicit user intent and new snapshot verification and approval.
