---
name: sdlc-new
description: Create one SCR SDLC item from a raw idea. Preserve intent, normalize scope, and mint through LETS when authorized.
---

# SDLC new

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

1. READ project instructions, relevant design, similar code, and related items. Separate facts, assumptions, constraints, acceptance, exclusions, and questions.
   1.1. APPLY [Scope and verification](../../../docs/SDLC-DEVELOPER-GUIDE.md#scope-and-verification). Identify bounded deliverables and existing dependency interfaces before proposing acceptance.
   1.2. KEEP inferred improvements separate from customer requirements. Dependency use alone never adds implementation or qualification scope.
2. RUN `./bin/lets sdlc mark - new`.
3. NORMALIZE kind (`task`, `improve`, `refactor`, `fix`), uppercase domain-first DESC, description, tags, and explicit dependencies.
4. SHOW concrete proposed record. Reuse existing mint authorization. Ask only when authorization or essential intent is missing.
5. WRITE raw idea and normalized description into separate scratch files.
6. RUN `./bin/lets sdlc items new --kind KIND --desc DESC --idea-file FILE --description-file FILE` with applicable tags and dependencies.
7. ***if*** item changes an image ***then*** RUN `./bin/lets sdlc hardware require ID` before planning.
8. RUN `./bin/lets sdlc mark ID end`.
9. REPORT minted ID and `$sdlc-plan ID`. Intake does not approve implementation.
