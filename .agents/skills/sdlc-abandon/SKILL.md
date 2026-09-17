---
name: sdlc-abandon
description: Explicitly abandon an SCR SDLC requirement while preserving its complete audit history. Use for `$sdlc-abandon` or textual `/sdlc-abandon` requests.
---

# Abandon an SDLC requirement

Require an explicit requirement ID and developer-provided reason. Show the current state and consequences, then run `./bin/lets sdlc abandon`; do not delete branches, worktrees, packages, or ledger history manually.

If image mutation or testing is active, abandonment must first use the tooling's cleanup path: uninstall packages, verify restoration, and release the lock. A cleanup failure leaves the image quarantined and prevents final abandonment until recovery. Report the durable terminal state and retained artifacts.
