---
name: sdlc-approve
description: Record developer approval or requested amendments for a persisted SDLC plan and then continue automatically. Use for `$sdlc-approve` or textual `/sdlc-approve` requests.
---

# Approve or amend a plan

First show the committed DRAFT and its revision if the current conversation has not already shown it. Pass explicit approval through `./bin/lets sdlc approve`; never infer approval from silence. For amendments, record them in the plan section, checkpoint the document, and use `./bin/lets sdlc stage <REQ> drafting-plan --message <summary>` so the planner produces a new committed DRAFT.

Amendments return the plan to planning; the planner must resolve all new questions before committing and displaying a revised DRAFT. Approval records the exact approved revision. Then run `./bin/lets sdlc resume <REQ>` and auto-progress until the next human gate or blocker.
