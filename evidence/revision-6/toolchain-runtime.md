# Revision 6 managed runtime and toolchain

Status: runtime/toolchain gate passed. Later exact config retrieval and bounded probe result recorded in `probe-live.md`.

- Approved DRAFT revision 6 SHA-256: `eaa5b1ea6f36bf64e3c18d9301ffbb90f6581fdbea3c0198907ae814315e4242`.
- Toolchain archive: size `51126392`; SHA-256 `2b4b29bcfed26948b654088aabbd7e5357691f66f0ba4864df63b2c00f054152`.
- Runtime: `ubuntu-trusty-i386-2019`; seven Ubuntu Trusty i386 packages, exact metadata in `lets/etc/toolchain/toolchain.conf`.
- `./bin/lets devenv init` downloaded and verified all pinned cache artifacts, rejected no metadata, extracted without APT/dpkg/maintainer scripts, published runtime/toolchain under `.lets`, then passed managed GCC banner check.
- Managed compiler banner: `arm-linux-gnueabihf-gcc (crosstool-NG linaro-1.13.1-4.8-2014.04 - Linaro GCC 4.8-2014.04) 4.8.3 20140401 (prerelease)`.
- Managed binutils banner: `GNU ld (crosstool-NG linaro-1.13.1-4.8-2014.04 - Linaro GCC 4.8-2014.04) 2.24.0.20140311 Linaro 2014.03`.
- Compiler-subprogram wrapper invokes `cc1`, assembler, and linker through managed loader/library path. Smoke compile produced ELF32 ARM relocatable output; managed `readelf`, `nm`, and `objdump` succeeded.
- Second `./bin/lets devenv init` reported verified skip; `.lets-manifest` mtime stayed `1789733939`. Cache/network not needed for toolchain/runtime path.
- Source checkout: NXP `linux-imx` commit `e35e57f24ef5851787812a18a38feeb9deb6ea46`, stored below `.lets`.
- Initial target config retrieval failed at old endpoint `192.168.68.56`: one `scp` connection close, then SSH `ConnectTimeout=10`, three `ConnectTimeout=5` attempts, and later `ConnectTimeout=10` timed out. Empty partial never accepted. Developer supplied new endpoint `192.168.68.55`; identity and exact config hash then passed.
- Production work, DEB, image lock/test, boot/reboot did not occur.

Safety: no force, MMIO, VFS probe behavior, persistence, boot activation, reboot, target APT, host APT, `sudo`, global install, image mount, or package action.
