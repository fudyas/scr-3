# Revision 5 managed-toolchain gate

Status: blocked before publish/use. Target, image, and ledger unchanged.

`./bin/lets devenv init` downloaded pinned `gcc-linaro-arm-linux-gnueabihf-4.8-2014.04_linux.tar.xz` through configured HTTPS fallback. Cache size `51126392`; SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`. Archive boundary/type/link checks passed after recognizing release's internal hard links. Complete bundled notices remain in cache/staging.

Compiler sentinel failed before atomic publish:

```text
arm-linux-gnueabihf-gcc: cannot execute: required file not found
unexpected toolchain compiler banner
```

Host inspection established archive compiler is `ELF 32-bit LSB executable, Intel 80386`, dynamically linked with interpreter `/lib/ld-linux.so.2`. Host is `x86_64`; `/lib/ld-linux.so.2` and i386 runtime absent. Approved contract requires managed verified self-check before publish/use. Installing host APT packages or adding an unpinned runtime was not authorized. No bypass, direct compiler/binutils execution, probe rebuild, target copy, `insmod`, `rmmod`, reboot, target APT, image mount, package, DEB, or production work occurred.

Unblock: coordinator approves a pinned, licensed i386 runtime managed under `${LETS_STATE_DIR}`, or explicitly approves host i386 runtime provisioning with exact package provenance. Then rerun `./bin/lets devenv init`; lock-held partial-stage recovery removes abandoned tool-owned staging and reuses verified cache offline.
