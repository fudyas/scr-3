---
name: sdlc-validate
description: Audit SDLC implementation against the complete requirement, approved plan, package reversibility, and image restoration. Use for `$sdlc-validate` or textual `/sdlc-validate` requests.
---

# Validate an implementation

Run `./bin/lets sdlc validate <REQ>` and audit every requirement and approved plan item against concrete package, test, and commit evidence. Validation must include Debian package install behavior and proof that uninstalling all requirement packages restores the original image state.

Any image test must hold the SDLC lock continuously across mount, install, tests, uninstall, restoration verification, and unlock. Cleanup failure quarantines the image and is a validation failure; do not bypass or clear quarantine manually.

Persist precise findings with `./bin/lets sdlc validation-result <REQ> --result pass|fail --report-file FILE`. If validation passes, merge the exact validated commit and resume automatically to the hardware follow-up gate. A failure returns the current round to implementation.
