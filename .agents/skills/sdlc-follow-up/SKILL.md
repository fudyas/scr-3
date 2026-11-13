---
name: sdlc-follow-up
description: Record developer real-hardware results for an SCR item; preserve failed evidence and require exact-package confirmation before completion.
---

# SDLC follow-up

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

1. READ item, review context, delivered package hash, image identity, installation/rollback procedure, and restoration evidence.
2. CAPTURE developer wording verbatim. Record hardware and image identity, package/version/hash, procedure, expected/observed behavior, and logs.
3. ***if*** explicit success is absent ***then*** KEEP hardware gate pending. Never infer hardware success from automated tests.
4. ***if*** developer confirms success ***then*** RUN `./bin/lets sdlc hardware pass ID --deb FILE --image-identity TEXT --notes-file FILE --confirmed-by-developer`.
5. ***if*** failure reported ***then*** RUN `./bin/lets sdlc hardware fail ID --deb FILE --image-identity TEXT --notes-file FILE`.
   5.1. RETAIN exact symptoms and failed artifact identity. Return same item to integration rework, or plan complete follow-on fix item when approved immutable scope cannot cover correction.
   5.2. REQUIRE new verification, exact-revision approval, and hardware confirmation for changed package. Never mark failed item DONE.
6. APPLY `$sdlc-review ID` completion only after successful hardware gate. Retain active chain and continue next member only after DONE.
