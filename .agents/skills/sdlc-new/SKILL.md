---
name: sdlc-new
description: Start a traceable SCR image requirement and automatically drive its first round to the next human gate. Use for `$sdlc-new` or textual `/sdlc-new` requests.
---

# Start an SDLC requirement

Pass the user's requirement and additional instructions to `./bin/lets sdlc new`; do not mint an ID or write the ledger manually. If essential intake facts are absent, ask focused questions before invoking it.

After creation, run `./bin/lets sdlc resume <REQ>` and coordinate the agents/stages it reports until the workflow reaches a human gate or blocker. Present planner questions before a draft is authored. A plan draft must be persisted and committed as **DRAFT** before it is displayed. Approval may be skipped only when the tooling's deterministic trivial-policy result explicitly permits it.

Do not implement direct image edits: every change must be a reversible Debian package whose uninstall restores all replaced, patched, added, or moved files. All image testing must use the SDLC lock for the complete mount/install/test/uninstall/restoration-verification window. If cleanup fails, leave the image quarantined and report recovery instructions from the tool.
