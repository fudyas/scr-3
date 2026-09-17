---
name: sdlc-resume
description: Resume an existing SCR requirement from its durable ledger state and auto-progress to the next human gate. Use for `$sdlc-resume` or textual `/sdlc-resume` requests.
---

# Resume an SDLC requirement

Run `./bin/lets sdlc resume <REQ>` and treat its durable `sdlc`-branch state as authoritative. Continue every ready stage automatically; do not ask the developer to issue the next stage command.

For each reported action, read `./bin/lets sdlc models`, spawn the named custom agent with that role's configured model and effort, and persist its result through `./bin/lets sdlc section` before advancing:

1. `requirements-analysis`: run `sdlc_requirements`, write `requirements-analysis`, then stage `image-analysis`.
2. `image-analysis`: run `sdlc_image_analysis`, write `image-analysis`, then stage `planner-questions`.
3. `planner-questions`: run `sdlc_planner` only to enumerate all load-bearing questions. Ask them together, write questions and answers to `planner-questions`, then stage `drafting-plan`. If there are no questions, record that fact and advance immediately.
4. `drafting-plan`: run `sdlc_planner` with the recorded answers, write `solution-plan`, and stage `draft-ready`. Run `trivial-policy` with facts from the plan. Display the committed DRAFT. Stop only if the resulting state is `awaiting-approval`.
5. `approved` or `auto-approved`: run `sdlc implement`, then continue.
6. `implementing`: run `sdlc_implementation` in the requirement worktree. Write implementation evidence, then run `implementation-commit --deb FILE`; it records the artifact hash and advances only after the DEB exists.
7. `implementation-ready`: run `sdlc validate`, then continue.
8. `validating`: run `sdlc_validation`. Persist its report with `validation-result`. On PASS, `sdlc merge` verifies and merges the exact validated commit and advances to `awaiting-hardware`; on FAIL, the result returns the pipeline to `implementing`. A merge conflict is a human gate.
9. `awaiting-hardware`: show the exact package artifact/checksum and manual test procedure, then stop for `$sdlc-follow-up`.

Use a temporary file for each authored section; never manipulate the ledger worktree directly. Every stage transition needs a concise evidence-bearing `--message`.

Stop only for planner intake questions, required plan approval/amendment, hardware testing, an explicit safety decision, or a tooling-reported blocker. Ensure a planner's DRAFT is committed before displaying it. Skip approval only when the tooling reports that the deterministic trivial-policy passed.

Never bypass the reversible-package rule, image lock, restoration verification, or quarantine. On cleanup failure, preserve quarantine and stop.
