#### Revision 6 implementation checkpoint

Approved DRAFT revision 6 SHA-256 `eaa5b1ea6f36bf64e3c18d9301ffbb90f6581fdbea3c0198907ae814315e4242` implemented through bounded diagnostic probe in designated worktree. No production release, DEB, image mutation, boot, or reboot.

LETS environment:

- `./bin/lets devenv init` owns pinned Linaro archive plus seven pinned Ubuntu Trusty i386 packages under `.lets/toolchains`.
- Exact URLs/versions/architectures/sizes/SHA-256 values match revision 6. Safe ar/tar inspection rejects unexpected members, traversal, special files, escaped links, wrong metadata, missing license evidence. No APT/dpkg/scripts/triggers/`ldconfig`/`sudo`/global install.
- Managed loader/library path runs allowlisted ELF32 i386 tools and GCC subprograms. Environment strips overrides; locale `C`. All compiler/binutils calls use `./bin/lets toolchain`.
- Functional suite passes all 13 allowlisted tools plus ELF32 ARM smoke compile. Idempotent second init skips verified generation; sentinel mtime `1789733939` unchanged.
- Toolchain archive size `51126392`; SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`.
- GCC `4.8.3 20140401 (prerelease)`; binutils `2.24.0.20140311 Linaro 2014.03`.

Old endpoint `192.168.68.56` failed config reacquisition: one `scp` close; SSH `ConnectTimeout=10`, three `ConnectTimeout=5`, later `ConnectTimeout=10` timed out. Empty partial SHA `e3b0c44298fc1c149afbf4e8996fb92427ae41e4649b934ca495991b7852b855` rejected. Developer changed endpoint to `192.168.68.55`; ignored credential host updated, secret preserved, mode `0600`.

New endpoint gates:

- Identity `SCR-7CCC91`; kernel `3.10.105-imx6 #5 SMP PREEMPT Wed May 16 11:21:53 IDT 2018 armv7l`; root.
- Config SHA-256 `956615a914d7759eabaf653d53e19ee1f4e85c8852f526b44c312dfac1017f26`; uImage MD5 `9ab15ca7cf8f336c519d5b51f14c4c3c`.
- NXP source commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`; reconstructed release `3.10.105-imx6`.
- Two builds matched SHA-256 `1377d6cae2339aedf00647a8e78b7aefed54c206a40927fb241cae0e12245334`.
- ELF/attributes/vermagic/symbol/disassembly gate passed. Relocation `3` absent; emitted `R_ARM_NONE`, `R_ARM_ABS32`, `R_ARM_CALL`, `R_ARM_JUMP24`, `R_ARM_PREL31` supported by reconstructed loader.

Sole live retry consumed:

- Baseline taint `4096`; probe/path absent; `/proc/modules` SHA-256 `4ad4f5e875ed244ec909d71af3857132e1b663aef98c6c0a11bfcaaf350e9b2c`.
- Transient root-owned mode `0600`; remote SHA exact.
- Ordinary `insmod` rc `0`; exact init log only; live refcount `0`; taint `4096`.
- Ordinary `rmmod` rc `0`; exact exit log only; module absent; taint `4096`.
- Transient removed. Final module-table/config/uImage hashes exactly baseline; connectivity healthy. No anomaly or quarantine condition.

Current blocker: diagnostic success proves callbacks only. Approximate source, Linaro GCC 4.8.3 prerelease versus live GCC 4.8.4, missing exact vendor tree/build recipe/generated headers/`Module.symvers` prevent stronger production-specific ABI/integration proof. Stop before production source/package/DEB/image test. Live retry exhausted.

Safety preserved: no host/target APT, direct compatibility tools, force, VFS/MMIO probe behavior, persistence, activation, boot/reboot, kernel/U-Boot patch, image mount/install, package action. Evidence: `evidence/revision-6/toolchain-runtime.md`, `evidence/revision-6/probe-live.md`; boundary: `RELEASE.md`.
