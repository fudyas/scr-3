---
name: sdlc-plan
description: Plan or revise one SCR SDLC item through independent planning and explicit developer approval.
---

# SDLC plan

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

1. RUN `./bin/lets sdlc sync` and `./bin/lets sdlc items show ID`.
2. ***if*** item is neither BACKLOG nor PLANNED ***then*** STOP. Unschedule before replanning. Retain active review ownership.
3. RUN `./bin/lets sdlc mark ID plan` and `./bin/lets sdlc items plan edit ID`.
4. LAUNCH `sdlc_planner` with item, draft path, existing code, design, and image-analysis evidence. Planner edits only draft.
   4.1. REQUIRE [Scope and verification](../../../docs/SDLC-DEVELOPER-GUIDE.md#scope-and-verification) audit of deliverables, dependency ownership, design necessity, tests, and acceptance stages.
5. ***while*** planner reports STALE, UNSURE, contradictions, or load-bearing questions:
   5.1. ASK developer focused questions before drafting. Reuse same planner for answers and feedback.
6. RUN `./bin/lets sdlc items plan check ID`.
   6.1. REVIEW planner's coverage and necessity findings. Structural success alone does not prove focused scope or relevant tests.
   6.2. RESOLVE unsupported tasks, dependency qualification, and tests before approval. Preserve required safety and repository gates separately.
7. SHOW Goal, Context, Design, and Out of scope verbatim. Summarize blocks and tasks with IDs, dependencies, and model hints. Name draft path.
   7.1. SHOW deliverables, dependency assumptions, test-to-criterion mapping, mandatory gates, and acceptance stages within same approval request.
8. WAIT for explicit plan approval, changes, or stop. Never infer approval from silence or chain agreement.
9. ***if*** approved ***then*** RUN `./bin/lets sdlc items plan approve ID`.
10. RUN `./bin/lets sdlc mark ID end`.
11. ***if*** active chain authorizes execution ***then*** APPLY `$sdlc-run ID` immediately. Otherwise report approved plan and next command.
