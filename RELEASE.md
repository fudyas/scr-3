# SCR reset monitor release boundary

Status: no production release. Revision 6 installs verified Ubuntu Trusty i386 runtime and pinned Linaro toolchain only below `.lets`; managed GCC/binutils smoke tests pass through `./bin/lets toolchain`. Rebuilt diagnostic probe SHA-256 `1377d6cae2339aedf00647a8e78b7aefed54c206a40927fb241cae0e12245334` loaded/unloaded cleanly once on exact target: ordinary `insmod`/`rmmod` returned `0`, expected init/exit logs only, taint stayed `4096`, module/transient removed, module-table/config/uImage baselines restored. This proves diagnostic callbacks only, not production ABI/integration. No host/target APT, dpkg, sudo, global runtime install, image mutation, boot, or reboot occurred. No DEB exists.

Toolchain provenance: ID `linaro-arm-linux-gnueabihf-4.8-2014.04`; archive `gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz`; size `51126392`; SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`; bundled licenses/notices preserved in verified cache. Expected compiler is Linaro GCC 4.8.3 prerelease, not live kernel compiler 4.8.4; compatibility remains approximate even after runtime unblock.

Runtime provenance: ID `ubuntu-trusty-i386-2019`; authoritative origin `https://archive.ubuntu.com/ubuntu/`; exact seven-package versions, sizes, SHA-256 hashes, control metadata, and license evidence are pinned in `lets/etc/toolchain/toolchain.conf` and verified before publish. Managed loader is runtime-local `lib/ld-linux.so.2`; library resolution is runtime-local. Runtime remains development infrastructure, never package/image payload.

Intended production scope: one observable event for each boot reaching production `scr_reset_monitor` module initialization. Same-boot supported unload/reload adds no event. Empty durable records only; module owns guard, record, retry, count, filter, reset, and serialization. Bash frontend transports requests and displays results only.

Excluded: physical-reset completeness, pre-module boots/resets, reset cause/reason, i.MX6 register/MMIO access, retained counters, reset-loop detection/mitigation, kernel/U-Boot patch/replacement, forced module load/removal, target APT mutation, reboot for install/remove, userspace monitoring authority.

Approximate probe limit: clean revision-6 init/exit proves only that exact diagnostic artifact loaded/unloaded once on exact running kernel without observed anomaly. It cannot prove exact ABI, VFS, guard, worker, control, persistence, package, boot, upgrade, count/reset/filter, or production safety. Production remains blocked pending stronger production-specific ABI/integration evidence.

Durability boundary: intended production event counts only after empty inode and parent-directory synchronization. Storage/device flush guarantees remain limited; pre-initialization events and crashes before durable synchronization may be lost. Wall-clock timestamps can be invalid/backward; unique suffix prevents overwrite.

Lifecycle boundary: intended package must preserve first baseline, never auto-load during install, use first normal boot activation, never force unload/reboot, retain pending removal on busy/failure, and restore every managed path on remove/purge. No lifecycle claim exists until exact production gates, package tests, and locked image restoration pass.

Testing/recovery: production live load requires probe success plus stronger production ABI/integration evidence. Image testing must hold SDLC lock through copy, mount, install, test, uninstall, restoration verification, unmount, source-hash verification, and unlock. Cleanup/restoration failure quarantines image. Target anomaly quarantines device testing; never reboot as probe cleanup.
