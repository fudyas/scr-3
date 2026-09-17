---
name: sdlc-implement
description: Implement an approved SCR SDLC plan as a fully reversible Debian package and continue through automated validation. Use for `$sdlc-implement` or textual `/sdlc-implement` requests.
---

# Implement an approved plan

Run `./bin/lets sdlc implement <REQ>` only when the ledger says the plan is approved or the deterministic trivial-policy explicitly waived approval. Follow the approved revision exactly; record deviations through the pipeline instead of improvising.

The deliverable must be one or more Debian packages. Package uninstall must restore replaced, patched, moved, and added image files so uninstalling every package produced for the requirement returns the image to its original state.

Use only `./bin/lets sdlc ...` operations for image access and testing. The image lock must cover mount, install, test, uninstall, restoration verification, and unlock. Never release it before verified restoration. If uninstall or verification fails, preserve quarantine, stop, and report the failure.

When implementation succeeds, resume automatically into validation and continue to the next human gate.
