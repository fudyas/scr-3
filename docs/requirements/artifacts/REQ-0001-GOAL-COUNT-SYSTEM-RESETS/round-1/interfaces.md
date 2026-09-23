# Revision 10 interfaces

- Package: `scr-req-0001-goal-count-system-resets` version `1.0.3`, `Architecture: armhf`; one canonical reproducible DEB.
- Init: `/etc/init.d/scr-resets-monitor`; exact approved LSB header; `$local_fs` only.
- Register: `/usr/sbin/update-rc.d scr-resets-monitor defaults`; verify rc, exact all-runlevel links, `.depend.start` exact token/order, expected `.depend.stop`, no `.depend.boot` activation.
- Unregister: `/usr/sbin/update-rc.d -f scr-resets-monitor remove`; verify rc, zero links, exact three-graph original content/type/metadata. Never write graph content.
- Diagnostic: `/sbin/insserv -s`; capture only; never pass/fail membership.
- Recovery: explicit `./bin/lets sdlc ... --recover` path binds existing copy/root, source, original baseline, artifact, backup, quarantine, lock. Outer transaction alone clears matched quarantine after remove/purge, restoration, unmount/loop release, source-hash PASS.
- Fresh image: `./bin/lets sdlc test-package ...`; lock spans copy/mount/install/test/remove/purge/restoration/unmount/source proof.
- Hardware: exact target `192.168.68.55`; one bounded reboot only after T03 PASS; ordinary cleanup restores baseline.
