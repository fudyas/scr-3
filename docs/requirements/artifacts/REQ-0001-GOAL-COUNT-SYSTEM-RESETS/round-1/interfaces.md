# Revision 11 interfaces

- Package: exact `scr-req-0001-goal-count-system-resets` version `1.0.3`, `Architecture: armhf`, DEB SHA-256 `8139e08b81216daf6ff9697ee8f9e60989cd830c8d3aad1a2b77bfe042b616f5`; package bytes unchanged.
- Module: exact SHA-256 `f8243c125555df192c5441efdc167574d1865fb690d493f3e59cea4d110ed3cc`; validated observable-init behavior unchanged.
- Recovery: `./bin/lets sdlc recover-package`; exact source/copy/root/DEB/fixture/hash/geometry/state-root inputs.
- Baseline: tooling-owned `baseline-clone.img`; pre-mount hash equals approved source; rw replay then clean unmount/loop release; ro fingerprint; authentic source never mounted.
- Recovery mutation: ordinary offline dpkg upgrade to corrected hooks, package test, remove, purge on preserved failed copy only.
- Clearance: outer recovery transaction only, after exact replayed-clone restoration, every unmount/loop release, source hash PASS.
- Fresh image: `./bin/lets sdlc test-package`; continuous lock covers copy/mount/install/test/remove/purge/restoration/unmount/source proof.
- Hardware: exact target `192.168.68.55`; one ordinary reboot only after recovery + fresh lifecycle + prerequisite task validation PASS.
