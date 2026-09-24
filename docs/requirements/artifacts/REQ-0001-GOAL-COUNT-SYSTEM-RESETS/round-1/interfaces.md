# Revision-13 interfaces

- Runtime acquisition/verification: only `./bin/lets sdlc ...`; pinned HTTPS artifacts, size/SHA-256/license/member/ELF/dependency manifest; atomic generation under LETS state; dedicated lock; verified offline reuse.
- Target runner: pinned PRoot plus external `qemu-arm-static`; target root `/`; exact DEB read-only virtual mapping; clean environment/fds; target `/usr/bin/dpkg`, shell, NSS, database, update-rc.d, insserv. No host dpkg/bind/global/target helper.
- Recovery: existing `recover-package` lock/journal/quarantine contract; exact runtime, source, copy, marker, baseline, report, artifact identities; ordinary target dpkg install/query/remove/purge; package test; restoration/cleanup/clearance.
- Evidence: task result plus independent validation JSON bind plan hash, commands, hashes, exact errors, safety state, acceptance IDs. No retrospective PASS.
