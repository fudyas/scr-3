---
name: sdlc-status
description: Show the durable state, current round, next gate, and safety status of an SCR SDLC requirement. Use for `$sdlc-status` or textual `/sdlc-status` requests.
---

# Show SDLC status

Run `./bin/lets sdlc status` with the supplied requirement when present. Report the requirement and round, current stage, plan revision/approval state, implementation branch and commit when available, hardware-follow-up state, next automatic action or human gate, and any held lock or quarantined image.

This command is observational. Do not edit bookkeeping or advance stages.
