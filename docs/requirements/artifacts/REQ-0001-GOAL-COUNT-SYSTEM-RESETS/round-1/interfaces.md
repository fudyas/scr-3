# Revision-14 interfaces

- Runtime: reuse exact revision-13 manifest SHA-256 `f92dd6c2525d57b2b50b92007fa4f3619e9c6b8abc412e6371a1d739a39da710`, generation suffix `f92dd6c2525d57b2`, QEMU SHA-256 `47a63bcbdf3030cf42230a0521dae38ff9d62ba1268d5cafc7d8ccf7da7c761c`; verified offline shared-lock lifetime.
- Broker: real-root bounded child enters new mount+network namespace; marks `/` recursively private; exact QEMU and DEB self-bind onto canonical paths; remount QEMU `ro,nosuid,nodev`, DEB `ro,nosuid,nodev,noexec`; verify mountinfo, mutation denial, identities, FDs, namespace/process cleanup. No target/global/shared/broad bind.
- Target runner: pinned loader/PRoot/external QEMU; target root `/`; exact private-read-only QEMU/DEB PRoot mappings; clean environment/fds; authentic target dpkg, shell, NSS, database, update-rc.d, insserv. No host dpkg, force, binfmt, network, target helper/copy/placeholder.
- Recovery: existing `recover-package` lock/journal/quarantine contract; exact runtime, source, copy, marker, replay baseline, inspection report, artifact identities; ordinary target dpkg install/query/remove/purge; package test; exact restoration/cleanup/tooling-only clearance.
- Evidence: task result plus independent validation JSON bind plan hash, commands, full hashes, exact errors, namespace/mountinfo/process/FD proof, safety state, acceptance IDs. No retrospective PASS.
