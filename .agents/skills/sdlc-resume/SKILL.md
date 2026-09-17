---
name: sdlc-resume
description: Resume an existing SCR requirement from its durable ledger state and auto-progress to the next human gate. Use for `$sdlc-resume` or textual `/sdlc-resume` requests.
---

# Resume an SDLC requirement

Run `./bin/lets sdlc resume <REQ>` and treat its durable `sdlc`-branch state as authoritative. Continue every ready stage automatically; do not ask the developer to issue the next stage command.

For each reported action, read `./bin/lets sdlc models`, spawn the named custom agent with that role's configured model and effort, and persist its result through `./bin/lets sdlc section` before advancing:

Write every spawned-agent instruction in `$caveman full`. Require every agent-authored `REQ-*` section to use `$caveman full` while preserving full technical content, exact evidence, and traceability.

1. `requirements-analysis`: run `sdlc_requirements`, write `requirements-analysis`, then stage `image-analysis`.
2. `image-analysis`: run `sdlc_image_analysis`, write `image-analysis`, then stage `planner-questions`.
3. `planner-questions`: run `sdlc_planner` only to enumerate all load-bearing questions. Ask them together, write questions and answers to `planner-questions`, then stage `drafting-plan`. If there are no questions, record that fact and advance immediately.
4. `drafting-plan`: run `sdlc_planner` with the recorded answers, write `solution-plan`, and stage `draft-ready`. Run `trivial-policy` with facts from the plan. Display the committed DRAFT. Stop only if the resulting state is `awaiting-approval`.
5. `approved` or `auto-approved`: run `sdlc implement`, then continue.
6. `implementing`: run `sdlc_implementation` in the requirement worktree. Write implementation evidence, then run `implementation-commit --deb FILE`; it records the artifact hash and advances only after the DEB exists.
7. `implementation-ready`: run `sdlc validate`, then continue.
8. `validating` without PASS evidence: run `sdlc_validation`. Persist report with `validation-result`. FAIL returns pipeline to `implementing`.
9. `validating` with PASS evidence: run `sdlc_integration`. Agent verifies exact validated commit/branch/DEB hash, target cleanliness, merge-base overlap, and unit tests. Agent then invokes `sdlc merge`; command holds shared cross-process main-tree lock from registry/target inspection through completion or safe abort. Conflict or semantic overlap needing precedence is human gate. Successful merge advances to `awaiting-hardware`.
10. `awaiting-hardware`: show exact package artifact/checksum and manual test procedure, then stop for `$sdlc-follow-up`.

Use a temporary file for each authored section; never manipulate the ledger worktree directly. Every stage transition needs a concise evidence-bearing `--message`.

Stop only for planner intake questions, required plan approval/amendment, hardware testing, an explicit safety decision, or a tooling-reported blocker. Ensure a planner's DRAFT is committed before displaying it. Skip approval only when the tooling reports that the deterministic trivial-policy passed.

Never bypass the reversible-package rule, image lock, restoration verification, or quarantine. On cleanup failure, preserve quarantine and stop.
